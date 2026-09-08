from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hackathon import Hackathon, Round
from app.models.team import Team
from app.models.user import User
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event

hackathon_router = APIRouter(prefix="/hackathons", tags=["Hackathons"])
round_router = APIRouter(prefix="/rounds", tags=["Rounds"])

class HackathonCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None

class RoundCreateSchema(BaseModel):
    type: str # round1_fix_the_prompt or round2_constraint_challenge
    duration_seconds: Optional[int] = 180

@hackathon_router.post("", status_code=status.HTTP_201_CREATED)
def create_hackathon(
    payload: HackathonCreateSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    hackathon = Hackathon(
        title=payload.title,
        description=payload.description,
        status="active",
        registration_open=True
    )
    db.add(hackathon)
    db.commit()
    db.refresh(hackathon)

    log_audit_event(db, action="hackathon.create", target_type="Hackathon", target_id=hackathon.id, actor_user_id=admin_user.id)
    return {
        "id": hackathon.id,
        "title": hackathon.title,
        "description": hackathon.description,
        "status": hackathon.status
    }

@hackathon_router.get("/{hackathon_id}")
def get_hackathon(hackathon_id: str, db: Session = Depends(get_db)):
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return hackathon

@hackathon_router.post("/{hackathon_id}/rounds", status_code=status.HTTP_201_CREATED)
def create_round(
    hackathon_id: str,
    payload: RoundCreateSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    round_obj = Round(
        hackathon_id=hackathon_id,
        type=payload.type,
        duration_seconds=payload.duration_seconds or 180,
        status="published"
    )
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)

    log_audit_event(db, action="round.create", target_type="Round", target_id=round_obj.id, actor_user_id=admin_user.id)
    return {
        "id": round_obj.id,
        "hackathon_id": round_obj.hackathon_id,
        "type": round_obj.type,
        "duration_seconds": round_obj.duration_seconds,
        "status": round_obj.status
    }

@round_router.post("/{round_id}/start")
def start_round(
    round_id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    now = datetime.utcnow()
    round_obj.status = "active"
    round_obj.start_at = now

    # FR-018: Lock all teams in the hackathon when round starts
    teams = db.query(Team).filter(Team.hackathon_id == round_obj.hackathon_id).all()
    for t in teams:
        t.status = "locked"

    db.commit()

    log_audit_event(db, action="round.start", target_type="Round", target_id=round_id, actor_user_id=admin_user.id, metadata={"teams_locked_count": len(teams)})

    return {"message": "Round started successfully. All teams locked.", "status": "active", "start_at": now.isoformat()}

@round_router.post("/{round_id}/pause")
def pause_round(
    round_id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    round_obj.status = "paused"
    db.commit()

    log_audit_event(db, action="round.pause", target_type="Round", target_id=round_id, actor_user_id=admin_user.id)
    return {"message": "Round paused", "status": "paused"}

@round_router.post("/{round_id}/end")
def end_round(
    round_id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    round_obj.status = "ended"
    db.commit()

    log_audit_event(db, action="round.end", target_type="Round", target_id=round_id, actor_user_id=admin_user.id)
    return {"message": "Round ended", "status": "ended"}

@round_router.get("/{round_id}/timer")
def get_server_timer(round_id: str, db: Session = Depends(get_db)):
    """Server-authoritative timer endpoint."""
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    now = datetime.utcnow()
    
    if round_obj.status != "active" or not round_obj.start_at:
        return {
            "round_id": round_obj.id,
            "status": round_obj.status,
            "server_time": now.isoformat(),
            "remaining_seconds": round_obj.duration_seconds,
            "is_expired": False
        }

    elapsed = (now - round_obj.start_at).total_seconds()
    remaining = max(0, int(round_obj.duration_seconds - elapsed))
    is_expired = remaining <= 0

    return {
        "round_id": round_obj.id,
        "status": "ended" if is_expired else round_obj.status,
        "server_time": now.isoformat(),
        "start_at": round_obj.start_at.isoformat(),
        "duration_seconds": round_obj.duration_seconds,
        "remaining_seconds": remaining,
        "is_expired": is_expired
    }
