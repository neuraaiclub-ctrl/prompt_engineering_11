from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.challenge import Challenge, Constraint, TestCase
from app.models.hackathon import Round
from app.models.user import User
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event
from app.schemas.challenge import ParticipantConstraintChallengeSchema, ParticipantConstraintSchema, AdminTestCaseSchema

router = APIRouter(tags=["Round 2 Challenges & Hidden Tests"])

class CreateConstraintChallengeSchema(BaseModel):
    title: str
    constraint_type: str # max_tokens_n, zero_shot, one_shot, no_system_prompt, generalize_unseen_inputs, valid_json_always
    max_tokens: Optional[int] = 50
    task_description: str
    format_rule: Optional[str] = None

class CreateTestCaseSchema(BaseModel):
    input: str
    expected_output: str
    eval_rule: Optional[Any] = {"type": "exact"}

@router.post("/rounds/{round_id}/constraint-challenges", status_code=status.HTTP_201_CREATED)
def create_constraint_challenge(
    round_id: str,
    payload: CreateConstraintChallengeSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    challenge = Challenge(round_id=round_id, type="constraint_challenge", title=payload.title, status="published")
    db.add(challenge)
    db.flush()

    constraint_obj = Constraint(
        challenge_id=challenge.id,
        type=payload.constraint_type,
        max_tokens=payload.max_tokens or 50,
        task_description=payload.task_description,
        format_rule=payload.format_rule
    )
    db.add(constraint_obj)
    db.commit()

    log_audit_event(db, action="challenge.create", target_type="ConstraintChallenge", target_id=challenge.id, actor_user_id=admin_user.id)
    return {
        "id": challenge.id,
        "title": challenge.title,
        "constraint_type": constraint_obj.type,
        "max_tokens": constraint_obj.max_tokens
    }

@router.get("/constraint-challenges/{challenge_id}")
def get_constraint_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge or challenge.type != "constraint_challenge":
        raise HTTPException(status_code=404, detail="Challenge not found")

    test_count = db.query(TestCase).filter(TestCase.challenge_id == challenge_id).count()

    c = challenge.constraint
    # Return participant-safe schema omitting all hidden test inputs and expected outputs
    return {
        "id": challenge.id,
        "round_id": challenge.round_id,
        "type": challenge.type,
        "title": challenge.title,
        "status": challenge.status,
        "constraint": {
            "type": c.type if c else "max_tokens_n",
            "max_tokens": c.max_tokens if c else 50,
            "task_description": c.task_description if c else "",
            "format_rule": c.format_rule if c else None
        },
        "hidden_test_count": test_count
    }

@router.post("/constraint-challenges/{challenge_id}/test-cases", status_code=status.HTTP_201_CREATED)
def add_test_case(
    challenge_id: str,
    payload: CreateTestCaseSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    tc = TestCase(
        challenge_id=challenge_id,
        input=payload.input,
        expected_output=payload.expected_output,
        eval_rule=payload.eval_rule or {"type": "exact"},
        visibility="hidden"
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)

    log_audit_event(db, action="testcase.create", target_type="TestCase", target_id=tc.id, actor_user_id=admin_user.id)
    return {"message": "Hidden test case created successfully", "id": tc.id}

@router.get("/test-cases/{test_case_id}")
def get_test_case_by_id(
    test_case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    CRITICAL SECURITY ENDPOINT (SRS Section 11.1 Threat Model / Edge Case #7):
    A Participant token can NEVER access TestCase details by ID.
    Access attempts by non-admin roles return 404 indistinguishably from non-existent IDs,
    and every denied attempt is recorded in the immutable AuditLog.
    """
    is_admin = any(r.name == "admin" for r in current_user.roles)

    if not is_admin:
        # Log unauthorized security probe
        log_audit_event(
            db,
            action="testcase.access_denied",
            target_type="TestCase",
            target_id=test_case_id,
            actor_user_id=current_user.id,
            metadata={"reason": "Participant probed hidden test case"}
        )
        # Indistinguishable 404 response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found"
        )

    tc = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    return {
        "id": tc.id,
        "challenge_id": tc.challenge_id,
        "input": tc.input,
        "expected_output": tc.expected_output,
        "eval_rule": tc.eval_rule,
        "visibility": tc.visibility
    }
