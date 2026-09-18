import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session


from app.database import get_db
from app.models.user import User
from app.models.registration import Registration
from app.core.rbac import require_roles
from app.core.audit import log_audit_event
from app.services.registration_sync import RegistrationSyncService
from app.schemas.registration import RegistrationOut, RegistrationImportReport, RegistrationActionPayload

router = APIRouter(prefix="/admin/registrations", tags=["Registration Management"])

@router.get("", response_model=List[RegistrationOut])
def get_all_registrations(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Retrieves all imported participant registrations for administrative review.
    """
    query = db.query(Registration)
    if status_filter:
        query = query.filter(Registration.registration_status == status_filter.upper())
    if search:
        search_fmt = f"%{search.strip().lower()}%"
        query = query.filter(
            (Registration.team_name.ilike(search_fmt)) |
            (Registration.participant_name.ilike(search_fmt)) |
            (Registration.email.ilike(search_fmt)) |
            (Registration.external_registration_id.ilike(search_fmt))
        )
    return query.order_by(Registration.imported_at.desc()).all()

@router.get("/summary")
def get_registrations_summary(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Returns summary statistics for the Admin Registration Control Panel.
    """
    total = db.query(Registration).count()
    pending = db.query(Registration).filter(Registration.registration_status == "PENDING").count()
    verified = db.query(Registration).filter(Registration.registration_status == "VERIFIED").count()
    rejected = db.query(Registration).filter(Registration.registration_status == "REJECTED").count()
    disabled = db.query(Registration).filter(Registration.registration_status == "DISABLED").count()
    active_accounts = db.query(Registration).filter(Registration.account_status == "ACTIVE").count()

    last_reg = db.query(Registration).order_by(Registration.last_synced_at.desc()).first()
    last_sync = last_reg.last_synced_at.isoformat() if last_reg and last_reg.last_synced_at else None

    return {
        "total": total,
        "pending": pending,
        "verified": verified,
        "rejected": rejected,
        "disabled": disabled,
        "active_accounts": active_accounts,
        "last_synced_at": last_sync
    }

@router.get("/export")
def export_registrations_csv(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Exports all imported registration records as a downloadable CSV.
    """
    from fastapi.responses import Response
    import io
    import csv

    registrations = db.query(Registration).order_by(Registration.imported_at.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Registration ID", "Team Name", "Participant Name", "Email", "Phone",
        "College", "Course", "Year", "Registration Status", "Account Status", "Last Synced At"
    ])
    for r in registrations:
        writer.writerow([
            r.external_registration_id or r.id,
            r.team_name,
            r.participant_name,
            r.email,
            r.phone or "",
            r.college or "",
            r.course or "",
            r.year or "",
            r.registration_status,
            r.account_status,
            r.last_synced_at.isoformat() if r.last_synced_at else ""
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=neura_registrations_export.csv"}
    )

@router.get("/{id}", response_model=RegistrationOut)
def get_registration_detail(
    id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    reg = db.query(Registration).filter(Registration.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found")
    return reg


@router.post("/sync", response_model=RegistrationImportReport)
def sync_google_sheets(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Triggers live synchronization with the configured Google Sheet response spreadsheet.
    """
    return RegistrationSyncService.sync_google_sheets(db)

@router.post("/import", response_model=RegistrationImportReport)
async def import_file(
    file: UploadFile = File(...),
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Uploads and imports a CSV or XLSX file containing registration records.
    """
    content = await file.read()
    try:
        report = RegistrationSyncService.import_csv_or_xlsx(db, content, file.filename)
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process import file: {str(e)}")

@router.post("/{id}/verify", response_model=RegistrationOut)
def verify_registration(
    id: str,
    payload: Optional[RegistrationActionPayload] = None,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Verifies registration and provisions runtime Team and User credentials.
    """
    reg = db.query(Registration).filter(Registration.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    if payload and payload.notes:
        reg.review_notes = payload.notes

    updated_reg = RegistrationSyncService.verify_and_provision_registration(db, reg, admin_user)
    log_audit_event(db, action="registration.verify", target_type="Registration", target_id=reg.id, actor_user_id=admin_user.id)
    return updated_reg

@router.post("/{id}/reject", response_model=RegistrationOut)
def reject_registration(
    id: str,
    payload: Optional[RegistrationActionPayload] = None,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    reg = db.query(Registration).filter(Registration.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    reg.registration_status = "REJECTED"
    reg.verification_status = "REJECTED"
    reg.account_status = "LOCKED"
    reg.is_active = False
    if payload and payload.notes:
        reg.review_notes = payload.notes

    if reg.user:
        reg.user.status = "suspended"

    db.commit()
    db.refresh(reg)

    log_audit_event(db, action="registration.reject", target_type="Registration", target_id=reg.id, actor_user_id=admin_user.id)
    return reg

@router.post("/{id}/disable", response_model=RegistrationOut)
def disable_registration(
    id: str,
    payload: Optional[RegistrationActionPayload] = None,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    reg = db.query(Registration).filter(Registration.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    reg.registration_status = "DISABLED"
    reg.account_status = "DISABLED"
    reg.is_active = False
    if payload and payload.notes:
        reg.review_notes = payload.notes

    if reg.user:
        reg.user.status = "suspended"

    db.commit()
    db.refresh(reg)

    log_audit_event(db, action="registration.disable", target_type="Registration", target_id=reg.id, actor_user_id=admin_user.id)
    return reg

@router.post("/{id}/activate", response_model=RegistrationOut)
def activate_registration(
    id: str,
    payload: Optional[RegistrationActionPayload] = None,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    reg = db.query(Registration).filter(Registration.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    reg.registration_status = "VERIFIED"
    reg.account_status = "ACTIVE"
    reg.is_active = True
    if reg.user:
        reg.user.status = "active"

    db.commit()
    db.refresh(reg)

    log_audit_event(db, action="registration.activate", target_type="Registration", target_id=reg.id, actor_user_id=admin_user.id)
    return reg

@router.get("/export")
def export_registrations_csv(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Exports all imported registration records as a downloadable CSV.
    """
    from fastapi.responses import Response
    import io
    import csv

    registrations = db.query(Registration).order_by(Registration.imported_at.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Registration ID", "Team Name", "Participant Name", "Email", "Phone",
        "College", "Course", "Year", "Registration Status", "Account Status", "Last Synced At"
    ])
    for r in registrations:
        writer.writerow([
            r.external_registration_id or r.id,
            r.team_name,
            r.participant_name,
            r.email,
            r.phone or "",
            r.college or "",
            r.course or "",
            r.year or "",
            r.registration_status,
            r.account_status,
            r.last_synced_at.isoformat() if r.last_synced_at else ""
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=neura_registrations_export.csv"}
    )

@router.post("/{id}/provision")
def provision_credentials(
    id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Provisions credentials or generates temporary password for a verified registration.
    """
    reg = db.query(Registration).filter(Registration.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    temp_password = f"NeuraPass!{uuid.uuid4().hex[:6]}"
    updated_reg = RegistrationSyncService.verify_and_provision_registration(
        db, reg, admin_user, default_password=temp_password
    )

    return {
        "message": "Credentials provisioned successfully",
        "email": updated_reg.email,
        "temporary_password": temp_password,
        "credentials": {
            "email": updated_reg.email,
            "password": temp_password
        },
        "team_id": updated_reg.team_id,
        "user_id": updated_reg.user_id
    }

