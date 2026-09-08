from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.challenge import Challenge, Constraint, TestCase
from app.models.execution import PromptVersion, Submission
from app.models.evaluation import Evaluation
from app.models.team import TeamMember
from app.models.user import User
from app.core.rbac import get_current_user
from app.core.token_counter import count_tokens
from app.core.validators import (
    validate_max_tokens, validate_zero_shot, validate_one_shot,
    validate_no_system_prompt, validate_valid_json_always
)
from app.core.ai_adapter import AIProviderAdapter
from app.core.audit import log_audit_event

router = APIRouter(tags=["Submissions & Automated Evaluation"])

class SubmitPromptSchema(BaseModel):
    prompt_text: str
    system_prompt_text: Optional[str] = None
    explanation: Optional[str] = None
    final_version_id: Optional[str] = None

@router.post("/challenges/{challenge_id}/submissions", status_code=status.HTTP_201_CREATED)
def submit_final_prompt(
    challenge_id: str,
    payload: SubmitPromptSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    membership = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not on any team")

    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Check for existing submission (DB unique constraint belt & suspenders)
    existing_sub = db.query(Submission).filter(
        Submission.challenge_id == challenge_id,
        Submission.team_id == membership.team_id
    ).first()
    if existing_sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your team has already submitted a final prompt for this challenge"
        )

    # Validate constraint compliance (Round 2)
    constraint_violated = False
    if challenge.type == "constraint_challenge" and challenge.constraint:
        c = challenge.constraint
        if c.type == "max_tokens_n":
            tokens = count_tokens(payload.prompt_text)
            if tokens > c.max_tokens:
                # FR-065 & SRS prompt directive:
                # Over-limit prompt is ACCEPTED, flagged constraint_violated=True, and penalized
                constraint_violated = True
        elif c.type == "zero_shot":
            valid, _ = validate_zero_shot(payload.prompt_text)
            if not valid: constraint_violated = True
        elif c.type == "one_shot":
            valid, _ = validate_one_shot(payload.prompt_text)
            if not valid: constraint_violated = True
        elif c.type == "no_system_prompt":
            valid, _ = validate_no_system_prompt(payload.system_prompt_text)
            if not valid: constraint_violated = True
        elif c.type == "valid_json_always":
            # Verified against model execution output in the test case loop
            pass

    submission = Submission(
        challenge_id=challenge_id,
        team_id=membership.team_id,
        final_prompt_version_id=payload.final_version_id,
        prompt_text=payload.prompt_text,
        explanation=payload.explanation,
        status="locked",
        constraint_violated=constraint_violated
    )
    
    try:
        db.add(submission)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your team has already submitted a final prompt for this challenge"
        )

    # Automated Evaluation: Hidden Test Suite Execution (Round 2)
    test_cases = db.query(TestCase).filter(TestCase.challenge_id == challenge_id).all()
    pass_count = 0
    total_count = len(test_cases)

    for tc in test_cases:
        # Run test server-side against abstracted provider
        res = AIProviderAdapter.execute(
            user_prompt=f"{payload.prompt_text}\n\nInput: {tc.input}",
            system_prompt=payload.system_prompt_text
        )
        raw_out = (res.get("output_text") or "").strip()
        out = raw_out.lower()
        exp = (tc.expected_output or "").strip().lower()

        tc_passed = (exp in out or out == exp)

        if challenge.type == "constraint_challenge" and challenge.constraint and challenge.constraint.type == "valid_json_always":
            json_valid, _ = validate_valid_json_always(raw_out)
            if not json_valid:
                tc_passed = False
                constraint_violated = True

        if tc_passed:
            pass_count += 1

    # Update submission if constraint violation was detected during test execution
    submission.constraint_violated = constraint_violated

    # Calculate automated score (penalizing violated constraints)
    pass_ratio = (pass_count / total_count) if total_count > 0 else 1.0
    calculated_auto_score = round(pass_ratio * (5.0 if not constraint_violated else 2.5), 2)

    evaluation = Evaluation(
        submission_id=submission.id,
        type="automated",
        auto_score=calculated_auto_score, # Stored separately from human judge_score
        pass_count=pass_count,
        total_count=total_count,
        format_compliant="false" if constraint_violated else "true"
    )
    db.add(evaluation)
    db.commit()
    db.refresh(submission)

    log_audit_event(
        db,
        action="submission.create",
        target_type="Submission",
        target_id=submission.id,
        actor_user_id=current_user.id,
        metadata={"challenge_id": challenge_id, "pass_count": pass_count, "constraint_violated": constraint_violated}
    )

    # Disclosure-Limited response payload (FR-061: only aggregate pass count, never inputs or outputs)
    return {
        "id": submission.id,
        "challenge_id": submission.challenge_id,
        "team_id": submission.team_id,
        "status": submission.status,
        "pass_count": pass_count,
        "total_count": total_count,
        "pass_rate_display": f"{pass_count}/{total_count}",
        "constraint_violated": submission.constraint_violated,
        "auto_score": calculated_auto_score,
        "submitted_at": submission.submitted_at.isoformat()
    }
