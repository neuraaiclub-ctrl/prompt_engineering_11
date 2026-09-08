from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.execution import Submission, PromptVersion
from app.models.challenge import Challenge, TestCase
from app.models.hackathon import Round
from app.models.evaluation import Evaluation
from app.models.score import Score
from app.models.user import User
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event
from app.core.scoring import validate_rubric_scores, check_disagreement, recompute_leaderboard

from app.schemas.judging import SubmitScoresSchema, AssignJudgeSchema

router = APIRouter(tags=["Human Judging & Rubrics"])

@router.get("/judges/me/assignments")
def get_my_assignments(
    current_user: User = Depends(require_roles(["judge", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Returns submissions assigned to the current judge (FR-102).
    """
    submissions = db.query(Submission).all()
    assignments = []

    for sub in submissions:
        # Check if judge has already evaluated this submission
        existing_eval = db.query(Evaluation).filter(
            Evaluation.submission_id == sub.id,
            Evaluation.judge_user_id == current_user.id
        ).first()

        round_obj = sub.challenge.round
        assignments.append({
            "submission_id": sub.id,
            "team_id": sub.team_id,
            "team_name": sub.team.name,
            "challenge_id": sub.challenge_id,
            "challenge_title": sub.challenge.title,
            "round_type": round_obj.type,
            "round_number": round_obj.order_index,
            "submitted_at": sub.submitted_at.isoformat(),
            "status": "completed" if (existing_eval and existing_eval.status == "submitted") else "pending",
            "my_evaluation_id": existing_eval.id if existing_eval else None
        })

    return assignments

@router.get("/submissions/{submission_id}")
def get_submission_viewer(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Role-scoped Submission Viewer (FR-103 & SRS Section 9.3).
    CRITICAL SECURITY CHECK:
    Judges and participants can NEVER see unrevealed hidden test inputs/outputs (SRS Section 9.3).
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    is_admin = any(r.name == "admin" for r in current_user.roles)
    is_judge = any(r.name == "judge" for r in current_user.roles)

    # Participants can only view their own team's submission
    if not is_admin and not is_judge:
        user_team_id = current_user.team_membership.team_id if current_user.team_membership else None
        if sub.team_id != user_team_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    # Prompt iterations history for Round 1
    versions = db.query(PromptVersion).filter(
        PromptVersion.challenge_id == sub.challenge_id,
        PromptVersion.team_id == sub.team_id
    ).order_by(PromptVersion.version_number.asc()).all()

    versions_data = [
        {
            "version_number": v.version_number,
            "prompt_text": v.prompt_text,
            "explanation": v.explanation,
            "is_final": v.is_final,
            "created_at": v.created_at.isoformat()
        }
        for v in versions
    ]

    # Automated evaluation detail
    auto_eval = next((e for e in sub.evaluations if e.type == "automated"), None)

    # Test cases data - strictly enforce hiding unrevealed test cases from judges and participants
    test_cases_data = []
    if sub.challenge.type == "constraint_challenge":
        all_tests = db.query(TestCase).filter(TestCase.challenge_id == sub.challenge_id).all()
        for tc in all_tests:
            if is_admin or tc.visibility == "revealed":
                test_cases_data.append({
                    "id": tc.id,
                    "input": tc.input,
                    "expected_output": tc.expected_output,
                    "visibility": tc.visibility
                })
            else:
                # Information hiding for Judges & Participants: strip input/output
                test_cases_data.append({
                    "id": tc.id,
                    "visibility": "hidden"
                })

    return {
        "id": sub.id,
        "challenge_id": sub.challenge_id,
        "challenge_title": sub.challenge.title,
        "challenge_type": sub.challenge.type,
        "round_type": sub.challenge.round.type,
        "team_id": sub.team_id,
        "team_name": sub.team.name,
        "prompt_text": sub.prompt_text,
        "explanation": sub.explanation,
        "constraint_violated": sub.constraint_violated,
        "submitted_at": sub.submitted_at.isoformat(),
        "versions": versions_data,
        "auto_evaluation": {
            "auto_score": auto_eval.auto_score if auto_eval else 0.0,
            "pass_count": auto_eval.pass_count if auto_eval else 0,
            "total_count": auto_eval.total_count if auto_eval else 0,
            "pass_rate_display": f"{auto_eval.pass_count}/{auto_eval.total_count}" if auto_eval else "0/0",
            "format_compliant": auto_eval.format_compliant if auto_eval else "true"
        } if auto_eval else None,
        "test_cases": test_cases_data
    }

@router.post("/evaluations/{submission_id}/scores", status_code=status.HTTP_201_CREATED)
def submit_judge_scores(
    submission_id: str,
    payload: SubmitScoresSchema,
    current_user: User = Depends(require_roles(["judge", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Judge submits rubric evaluation scores (FR-082, FR-084).
    Enforces atomic 0-5 integer validation and updates leaderboard cache.
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    round_type = sub.challenge.round.type

    # Server-side validation of 0-5 integer scale (raises 422 if invalid)
    validated_scores = validate_rubric_scores(round_type, payload.scores)

    # Check for existing evaluation by this judge
    eval_obj = db.query(Evaluation).filter(
        Evaluation.submission_id == submission_id,
        Evaluation.judge_user_id == current_user.id
    ).first()

    if not eval_obj:
        eval_obj = Evaluation(
            submission_id=submission_id,
            type="human",
            status="submitted",
            judge_user_id=current_user.id,
            judge_comment=payload.comment
        )
        db.add(eval_obj)
        db.flush()
    else:
        eval_obj.status = "submitted"
        eval_obj.judge_comment = payload.comment
        # Clear existing score entries for clean replacement
        db.query(Score).filter(Score.evaluation_id == eval_obj.id).delete()
        db.flush()

    total_pts = 0.0
    for dim, val, comm in validated_scores:
        score_rec = Score(
            evaluation_id=eval_obj.id,
            dimension=dim,
            value=val,
            comment=comm
        )
        db.add(score_rec)
        total_pts += val

    eval_obj.judge_score = round(total_pts, 2)
    db.commit()

    # Check for multi-judge disagreements (>= 2 points)
    has_disagreement = check_disagreement(submission_id, db)

    # Recompute leaderboard cache
    hackathon_id = sub.challenge.round.hackathon_id
    recompute_leaderboard(hackathon_id, db)

    log_audit_event(
        db,
        action="score.enter",
        target_type="Evaluation",
        target_id=eval_obj.id,
        actor_user_id=current_user.id,
        metadata={
            "submission_id": submission_id,
            "judge_score": total_pts,
            "disagreement": has_disagreement
        }
    )

    return {
        "message": "Evaluation submitted successfully",
        "evaluation_id": eval_obj.id,
        "judge_score": eval_obj.judge_score,
        "disagreement_flag": has_disagreement
    }

@router.get("/rounds/{round_id}/evaluations/progress")
def get_evaluations_progress(
    round_id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Admin Judging Oversight Panel (FR-096):
    Tracks judging progress, per-judge completion, and score disagreement flags.
    """
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    submissions = db.query(Submission).join(Challenge).filter(Challenge.round_id == round_id).all()
    progress_list = []

    for sub in submissions:
        human_evals = [e for e in sub.evaluations if e.type == "human" and e.status == "submitted"]
        scores_by_judge = [
            {
                "judge_id": e.judge_user_id,
                "judge_name": e.judge.name if e.judge else "Unknown",
                "score": e.judge_score,
                "comment": e.judge_comment,
                "dimensions": {s.dimension: s.value for s in e.scores}
            }
            for e in human_evals
        ]
        
        avg_score = round(sum(e.judge_score for e in human_evals) / len(human_evals), 2) if human_evals else None
        disagreement = any(e.disagreement_flag for e in human_evals)

        progress_list.append({
            "submission_id": sub.id,
            "team_id": sub.team_id,
            "team_name": sub.team.name,
            "challenge_title": sub.challenge.title,
            "judges_count": len(human_evals),
            "average_score": avg_score,
            "disagreement_flag": disagreement,
            "evaluations": scores_by_judge
        })

    return {
        "round_id": round_id,
        "total_submissions": len(submissions),
        "submissions_progress": progress_list
    }
