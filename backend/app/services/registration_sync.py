import csv
import io
import uuid
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models.registration import Registration
from app.models.user import User, Role
from app.models.team import Team, TeamMember
from app.models.hackathon import Hackathon
from app.core.security import hash_password, generate_random_token
from app.core.audit import log_audit_event

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class RegistrationSyncService:

    @staticmethod
    def normalize_row_keys(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps source spreadsheet/CSV column headers to canonical internal model field names.
        """
        column_map = settings.REGISTRATION_COLUMN_MAP
        normalized = {}
        for raw_key, val in row.items():
            if raw_key is None:
                continue
            clean_key = str(raw_key).strip()
            target_key = column_map.get(clean_key, clean_key.lower().replace(" ", "_"))
            normalized[target_key] = str(val).strip() if val is not None else ""
        return normalized

    @classmethod
    def process_registration_row(
        cls, db: Session, row_data: Dict[str, Any], source: str, row_number: int
    ) -> Dict[str, Any]:
        """
        Validates and idempotently upserts a single registration record into the database.
        Returns status: 'created', 'updated', 'unchanged', or 'invalid' with error details.
        """
        row = cls.normalize_row_keys(row_data)

        # Handle multi-member flat rows (e.g. Member 1 Email, Member 2 Email) or single member rows
        team_name = row.get("team_name") or row.get("team")
        participant_name = row.get("participant_name") or row.get("member_1_name") or row.get("name")
        email = (row.get("email") or row.get("member_1_email") or "").lower()
        college = row.get("college")
        course = row.get("course")
        year = row.get("year")
        phone = row.get("phone")
        external_id = row.get("external_registration_id") or row.get("registration_id")

        errors = []
        if not team_name:
            errors.append("Missing required field: Team Name")
        if not participant_name:
            errors.append("Missing required field: Participant Name")
        if not email:
            errors.append("Missing required field: Email")
        elif not EMAIL_REGEX.match(email):
            errors.append(f"Invalid email format: '{email}'")

        if errors:
            return {"status": "invalid", "errors": errors, "row_number": row_number, "email": email}

        # Check existing registration by external_id or email
        reg = None
        if external_id:
            reg = db.query(Registration).filter(Registration.external_registration_id == external_id).first()
        if not reg:
            reg = db.query(Registration).filter(Registration.email == email).first()

        now = datetime.utcnow()
        if reg:
            # Check for changes
            changed = False
            if reg.team_name != team_name:
                reg.team_name = team_name
                changed = True
            if reg.participant_name != participant_name:
                reg.participant_name = participant_name
                changed = True
            if college and reg.college != college:
                reg.college = college
                changed = True
            if course and reg.course != course:
                reg.course = course
                changed = True
            if year and reg.year != year:
                reg.year = year
                changed = True
            if phone and reg.phone != phone:
                reg.phone = phone
                changed = True

            reg.last_synced_at = now
            reg.source_row = row_number
            db.flush()

            return {"status": "updated" if changed else "unchanged", "registration_id": reg.id, "email": email}
        else:
            # Create new registration record
            reg = Registration(
                external_registration_id=external_id or f"REG-{uuid.uuid4().hex[:8].upper()}",
                team_name=team_name,
                participant_name=participant_name,
                email=email,
                phone=phone,
                college=college,
                course=course,
                year=year,
                registration_status="PENDING",
                verification_status="PENDING",
                account_status="NOT_PROVISIONED",
                is_active=True,
                source=source,
                source_row=row_number,
                imported_at=now,
                last_synced_at=now
            )
            db.add(reg)
            db.flush()
            return {"status": "created", "registration_id": reg.id, "email": email}

    @classmethod
    def import_csv_or_xlsx(cls, db: Session, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Parses uploaded CSV or XLSX file and performs idempotent synchronization.
        """
        start_time = time.time()
        rows_data = []

        filename_lower = filename.lower()
        if filename_lower.endswith(".csv"):
            content_str = file_bytes.decode("utf-8-sig", errors="ignore")
            reader = csv.DictReader(io.StringIO(content_str))
            for r in reader:
                rows_data.append(r)
        elif filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if any(row):
                    row_dict = {headers[i]: row[i] for i in range(len(headers)) if i < len(row)}
                    rows_data.append(row_dict)
        else:
            raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")

        created_cnt = 0
        updated_cnt = 0
        unchanged_cnt = 0
        invalid_cnt = 0
        error_details = []

        # Identify records missing from this batch and flag for review (never auto-delete)
        processed_emails = set()
        for idx, row_dict in enumerate(rows_data, start=2):
            res = cls.process_registration_row(db, row_dict, source="csv_import", row_number=idx)
            st = res["status"]
            if st == "created":
                created_cnt += 1
            elif st == "updated":
                updated_cnt += 1
            elif st == "unchanged":
                unchanged_cnt += 1
            elif st == "invalid":
                invalid_cnt += 1
                error_details.append({"row": idx, "errors": res["errors"], "email": res.get("email")})
            if res.get("email"):
                processed_emails.add(res["email"].lower())

        flagged_cnt = 0
        existing_regs = db.query(Registration).filter(Registration.source == "csv_import").all()
        for reg in existing_regs:
            if reg.email.lower() not in processed_emails:
                reg.flagged_for_review = True
                reg.review_notes = "Missing from latest CSV import batch"
                flagged_cnt += 1

        db.commit()

        duration = int((time.time() - start_time) * 1000)
        log_audit_event(
            db,
            action="registration.import",
            target_type="RegistrationImport",
            target_id=filename,
            metadata={
                "total_rows": len(rows_data),
                "created": created_cnt,
                "updated": updated_cnt,
                "invalid": invalid_cnt,
                "flagged": flagged_cnt
            }
        )

        return {
            "success": True,
            "source": "csv_import",
            "total_rows": len(rows_data),
            "created": created_cnt,
            "updated": updated_cnt,
            "unchanged": unchanged_cnt,
            "invalid": invalid_cnt,
            "duplicates": 0,
            "flagged": flagged_cnt,
            "duration_ms": duration,
            "errors": error_details
        }


    @classmethod
    def sync_google_sheets(cls, db: Session) -> Dict[str, Any]:
        """
        Synchronizes live registration responses from Google Sheets API.
        If credentials/sheet ID are not configured, returns clear simulation/status report.
        """
        start_time = time.time()
        if not settings.GOOGLE_SHEET_ID:
            return {
                "success": False,
                "source": "google_sheets",
                "total_rows": 0,
                "created": 0,
                "updated": 0,
                "unchanged": 0,
                "invalid": 0,
                "duplicates": 0,
                "flagged": 0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "errors": [{"row": 0, "errors": ["GOOGLE_SHEET_ID is not configured in environment variables."]}]
            }

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = None
            if settings.GOOGLE_SERVICE_ACCOUNT_FILE:
                creds = service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            elif settings.GOOGLE_SERVICE_ACCOUNT_JSON:
                import json
                info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
                creds = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )

            if not creds:
                return {
                    "success": False,
                    "source": "google_sheets",
                    "total_rows": 0,
                    "created": 0,
                    "updated": 0,
                    "unchanged": 0,
                    "invalid": 0,
                    "duplicates": 0,
                    "flagged": 0,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "errors": [{"row": 0, "errors": ["Google Service Account credentials not provided."]}]
                }

            service = build('sheets', 'v4', credentials=creds)
            sheet_range = f"{settings.GOOGLE_SHEET_NAME}!{settings.GOOGLE_SHEET_RANGE}"
            result = service.spreadsheets().values().get(
                spreadsheetId=settings.GOOGLE_SHEET_ID, range=sheet_range
            ).execute()
            rows = result.get('values', [])

            if not rows or len(rows) < 2:
                return {
                    "success": True,
                    "source": "google_sheets",
                    "total_rows": 0,
                    "created": 0,
                    "updated": 0,
                    "unchanged": 0,
                    "invalid": 0,
                    "duplicates": 0,
                    "flagged": 0,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "errors": []
                }

            headers = rows[0]
            created_cnt = 0
            updated_cnt = 0
            unchanged_cnt = 0
            invalid_cnt = 0
            error_details = []

            for idx, r in enumerate(rows[1:], start=2):
                row_dict = {headers[i]: r[i] for i in range(len(headers)) if i < len(r)}
                res = cls.process_registration_row(db, row_dict, source="google_sheets", row_number=idx)
                st = res["status"]
                if st == "created":
                    created_cnt += 1
                elif st == "updated":
                    updated_cnt += 1
                elif st == "unchanged":
                    unchanged_cnt += 1
                elif st == "invalid":
                    invalid_cnt += 1
                    error_details.append({"row": idx, "errors": res["errors"], "email": res.get("email")})

            db.commit()

            log_audit_event(
                db,
                action="registration.sync",
                target_type="GoogleSheetsSync",
                target_id=settings.GOOGLE_SHEET_ID,
                metadata={"total_rows": len(rows) - 1, "created": created_cnt, "updated": updated_cnt}
            )

            return {
                "success": True,
                "source": "google_sheets",
                "total_rows": len(rows) - 1,
                "created": created_cnt,
                "updated": updated_cnt,
                "unchanged": unchanged_cnt,
                "invalid": invalid_cnt,
                "duplicates": 0,
                "flagged": 0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "errors": error_details
            }
        except Exception as e:
            return {
                "success": False,
                "source": "google_sheets",
                "total_rows": 0,
                "created": 0,
                "updated": 0,
                "unchanged": 0,
                "invalid": 0,
                "duplicates": 0,
                "flagged": 0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "errors": [{"row": 0, "errors": [str(e)]}]
            }

    @classmethod
    def verify_and_provision_registration(
        cls, db: Session, reg: Registration, admin_user: User, default_password: Optional[str] = None
    ) -> Registration:
        """
        Verifies registration and provisions the runtime Team, User, TeamMember, and Role entities.
        """
        reg.registration_status = "VERIFIED"
        reg.verification_status = "VERIFIED"
        reg.account_status = "ACTIVE"
        reg.is_active = True

        # Check or create Team
        team = db.query(Team).filter(Team.name == reg.team_name).first()
        if not team:
            invite_code = f"NR-{uuid.uuid4().hex[:4].upper()}"
            hk = db.query(Hackathon).first()
            hk_id = hk.id if hk else "hk-2026"
            team = Team(
                id=f"team-{uuid.uuid4().hex[:8]}",
                hackathon_id=hk_id,
                name=reg.team_name,
                college=reg.college or "NEURA Registered Institute",
                invite_code=invite_code,
                status="forming"
            )
            db.add(team)
            db.flush()

        reg.team_id = team.id

        # Check or create User
        user = db.query(User).filter(User.email == reg.email.lower()).first()
        raw_pwd = default_password or f"NeuraPass2026!{uuid.uuid4().hex[:4]}"
        pwd_hash = hash_password(raw_pwd)

        if not user:
            user = User(
                id=f"usr-{uuid.uuid4().hex[:8]}",
                name=reg.participant_name,
                email=reg.email.lower(),
                password_hash=pwd_hash,
                affiliation=reg.college or "Participant",
                status="active"
            )
            db.add(user)
            db.flush()
            db.add(Role(user_id=user.id, name="participant"))

        reg.user_id = user.id
        reg.password_hash = user.password_hash
        reg.password_set = True

        # Ensure TeamMember linkage
        existing_member = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
        if not existing_member:
            # First member becomes leader
            team_members_count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
            role_in_team = "leader" if team_members_count == 0 else "member"
            tm = TeamMember(
                team_id=team.id,
                user_id=user.id,
                role=role_in_team
            )
            db.add(tm)

        db.commit()
        db.refresh(reg)

        log_audit_event(
            db,
            action="account.provision",
            target_type="Registration",
            target_id=reg.id,
            actor_user_id=admin_user.id,
            metadata={"email": reg.email, "team_id": team.id, "user_id": user.id}
        )

        return reg
