from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.challenge import Challenge, PromptCase
from app.models.execution import PromptVersion, Submission
from app.models.hackathon import Round
from app.models.team import TeamMember
from app.models.user import User
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event

router = APIRouter(tags=["Round 1 Cases & Versions"])

class CreatePromptCaseSchema(BaseModel):
    title: str
    original_prompt: str
    bad_output: str
    bad_output_screenshot_url: Optional[str] = None
    broken_reason: str # vague, no_format_specified, contradictory, no_role_context, missing_edge_cases, other
    difficulty: Optional[str] = "medium"
    description: Optional[str] = None

class CreateVersionSchema(BaseModel):
    prompt_text: str
    system_prompt_text: Optional[str] = None
    explanation: str # Mandatory non-empty 1-line explanation

@router.post("/rounds/{round_id}/prompt-cases", status_code=status.HTTP_201_CREATED)
def create_prompt_case(
    round_id: str,
    payload: CreatePromptCaseSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    challenge = Challenge(round_id=round_id, type="prompt_case", title=payload.title, status="published")
    db.add(challenge)
    db.flush()

    case_obj = PromptCase(
        challenge_id=challenge.id,
        original_prompt=payload.original_prompt,
        bad_output=payload.bad_output,
        bad_output_screenshot_url=payload.bad_output_screenshot_url,
        broken_reason=payload.broken_reason,
        difficulty=payload.difficulty or "medium",
        description=payload.description
    )
    db.add(case_obj)
    db.commit()

    log_audit_event(db, action="case.create", target_type="PromptCase", target_id=case_obj.id, actor_user_id=admin_user.id)
    return {
        "id": case_obj.id,
        "challenge_id": challenge.id,
        "title": challenge.title,
        "difficulty": case_obj.difficulty
    }

@router.get("/prompt-cases/{case_id}")
def get_prompt_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    case_obj = db.query(PromptCase).filter((PromptCase.id == case_id) | (PromptCase.challenge_id == case_id)).first()
    if not case_obj:
        raise HTTPException(status_code=404, detail="Case not found")

    is_admin = any(r.name in ["admin", "judge"] for r in current_user.roles)
    
    # FR-040: Serializer isolation - Participants NEVER receive internal broken_reason
    res = {
        "id": case_obj.id,
        "challenge_id": case_obj.challenge_id,
        "title": case_obj.challenge.title,
        "original_prompt": case_obj.original_prompt,
        "bad_output": case_obj.bad_output,
        "bad_output_screenshot_url": case_obj.bad_output_screenshot_url,
        "difficulty": case_obj.difficulty,
        "description": case_obj.description
    }

    if is_admin:
        res["broken_reason"] = case_obj.broken_reason

    return res

@router.post("/challenges/{challenge_id}/prompt-versions", status_code=status.HTTP_201_CREATED)
def create_prompt_version(
    challenge_id: str,
    payload: CreateVersionSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Enforce team membership
    membership = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not on any team")

    # FR-041: Mandatory explanation requirement (reject blank with 422)
    if not payload.explanation or not payload.explanation.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An explanation is required for each prompt iteration (what changed & why)"
        )

    # FR-044: Check if case already submitted and locked
    existing_sub = db.query(Submission).filter(
        Submission.challenge_id == challenge_id,
        Submission.team_id == membership.team_id
    ).first()
    if existing_sub and existing_sub.status == "locked":
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="This challenge case has already been submitted and locked. No further versions can be added."
        )

    # Monotonically increasing version number per team
    last_ver = db.query(PromptVersion).filter(
        PromptVersion.challenge_id == challenge_id,
        PromptVersion.team_id == membership.team_id
    ).order_by(PromptVersion.version_number.desc()).first()

    next_num = (last_ver.version_number + 1) if last_ver else 1

    version_obj = PromptVersion(
        challenge_id=challenge_id,
        team_id=membership.team_id,
        version_number=next_num,
        prompt_text=payload.prompt_text,
        system_prompt_text=payload.system_prompt_text,
        explanation=payload.explanation.strip(),
        is_final=False,
        created_by_user_id=current_user.id
    )
    db.add(version_obj)
    db.commit()
    db.refresh(version_obj)

    log_audit_event(
        db,
        action="version.create",
        target_type="PromptVersion",
        target_id=version_obj.id,
        actor_user_id=current_user.id,
        metadata={"version_number": next_num, "team_id": membership.team_id}
    )

    return {
        "id": version_obj.id,
        "challenge_id": version_obj.challenge_id,
        "team_id": version_obj.team_id,
        "version_number": version_obj.version_number,
        "prompt_text": version_obj.prompt_text,
        "explanation": version_obj.explanation,
        "is_final": version_obj.is_final
    }

@router.get("/challenges/{challenge_id}/prompt-versions")
def get_version_history(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    membership = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).first()
    is_admin = any(r.name in ["admin", "judge"] for r in current_user.roles)

    query = db.query(PromptVersion).filter(PromptVersion.challenge_id == challenge_id)
    if not is_admin:
        if not membership:
            return []
        query = query.filter(PromptVersion.team_id == membership.team_id)

    versions = query.order_by(PromptVersion.version_number.asc()).all()
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "prompt_text": v.prompt_text,
            "explanation": v.explanation,
            "is_final": v.is_final,
            "created_at": v.created_at.isoformat()
        }
        for v in versions
    ]

@router.patch("/prompt-versions/{version_id}/mark-final")
def mark_final_version(
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    version_obj = db.query(PromptVersion).filter(PromptVersion.id == version_id).first()
    if not version_obj:
        raise HTTPException(status_code=404, detail="Version not found")

    # Clear prior is_final flags for this team on this challenge
    db.query(PromptVersion).filter(
        PromptVersion.challenge_id == version_obj.challenge_id,
        PromptVersion.team_id == version_obj.team_id
    ).update({"is_final": False})

    version_obj.is_final = True
    db.commit()

    return {"message": f"Version {version_obj.version_number} marked as final"}
