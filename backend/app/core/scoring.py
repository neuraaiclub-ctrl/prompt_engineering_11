from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.hackathon import Hackathon, Round
from app.models.team import Team
from app.models.challenge import Challenge
from app.models.execution import Submission
from app.models.evaluation import Evaluation
from app.models.score import Score
from app.models.leaderboard import LeaderboardEntry

ROUND1_DIMENSIONS = [
    "diagnosis_quality",
    "improvement_quality",
    "final_output_quality",
    "documentation_clarity"
]

ROUND2_HUMAN_DIMENSIONS = [
    "technique_used"
]

def validate_rubric_scores(round_type: str, scores_input: Dict[str, Any]) -> List[Tuple[str, float, Optional[str]]]:
    """
    Strict server-side validation of judging rubric (SRS Section 9 & Section 18):
    - Validates 0-5 integer scale atomically.
    - Rejects fractional values (e.g. 5.5), out-of-range (<0 or >5), or non-numeric with HTTP 422.
    - Prevents partial writes: all dimensions must validate before any write.
    """
    required_dims = ROUND1_DIMENSIONS if "round1" in round_type.lower() else ROUND2_HUMAN_DIMENSIONS
    validated_scores: List[Tuple[str, float, Optional[str]]] = []

    for dim in required_dims:
        if dim not in scores_input:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Missing required rubric dimension: {dim}"
            )
        
        entry = scores_input[dim]
        val = entry.get("value") if isinstance(entry, dict) else entry
        comment = entry.get("comment") if isinstance(entry, dict) else None

        # Value must be present and numeric
        if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Dimension '{dim}' score must be an integer between 0 and 5"
            )
        
        # Enforce exact integer check (5.0 is acceptable integer float, 5.5 is not)
        if isinstance(val, float) and not val.is_integer():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Dimension '{dim}' score must be an integer (received fractional {val})"
            )
        
        int_val = int(val)
        if int_val < 0 or int_val > 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Dimension '{dim}' score out of range: must be between 0 and 5 (received {int_val})"
            )
        
        validated_scores.append((dim, float(int_val), comment))

    return validated_scores

def check_disagreement(submission_id: str, db: Session) -> bool:
    """
    Multi-judge disagreement detection (SRS Section 9.3 & Edge Case #9):
    Flags dimensions where judges differ by >= 2 points for organizer review.
    """
    human_evals = db.query(Evaluation).filter(
        Evaluation.submission_id == submission_id,
        Evaluation.type == "human",
        Evaluation.status == "submitted"
    ).all()

    if len(human_evals) < 2:
        return False

    has_disagreement = False
    # Collect scores by dimension
    dim_scores: Dict[str, List[float]] = {}
    for ev in human_evals:
        for sc in ev.scores:
            dim_scores.setdefault(sc.dimension, []).append(sc.value)

    for dim, vals in dim_scores.items():
        if len(vals) >= 2:
            delta = max(vals) - min(vals)
            if delta >= 2.0:
                has_disagreement = True
                break

    for ev in human_evals:
        ev.disagreement_flag = has_disagreement
    db.commit()

    return has_disagreement

def recompute_leaderboard(hackathon_id: str, db: Session) -> List[LeaderboardEntry]:
    """
    Derived leaderboard view recomputation engine (SRS Section 5.6 & Section 12.1):
    - Computes aggregated scores per team across Round 1 & Round 2.
    - Applies deterministic 3-tier tie-breaking order:
        1. Higher Round 2 % test cases passed
        2. Higher Round 1 human score
        3. Earlier final-submission timestamp
    - Updates cached LeaderboardEntry rows.
    """
    teams = db.query(Team).filter(Team.hackathon_id == hackathon_id).all()
    entries_data = []

    for team in teams:
        # 1. Round 1 Score: average human score across judges
        r1_submissions = db.query(Submission).join(Challenge).join(Round).filter(
            Submission.team_id == team.id,
            Round.type.contains("round1")
        ).all()

        r1_human_scores = []
        r1_latest_ts = None
        for sub in r1_submissions:
            if sub.submitted_at and (r1_latest_ts is None or sub.submitted_at > r1_latest_ts):
                r1_latest_ts = sub.submitted_at
            
            human_evals = [e for e in sub.evaluations if e.type == "human" and e.status == "submitted"]
            for ev in human_evals:
                if ev.scores:
                    ev_total = sum(s.value for s in ev.scores)
                    r1_human_scores.append(ev_total)
                elif ev.judge_score is not None:
                    r1_human_scores.append(ev.judge_score)

        avg_r1_score = round(sum(r1_human_scores) / len(r1_human_scores), 2) if r1_human_scores else 0.0

        # 2. Round 2 Score: automated score (% passed + constraint) + human technique score
        r2_submission = db.query(Submission).join(Challenge).join(Round).filter(
            Submission.team_id == team.id,
            Round.type.contains("round2")
        ).first()

        r2_pass_rate = 0.0
        r2_score = 0.0
        r2_ts = None

        if r2_submission:
            r2_ts = r2_submission.submitted_at
            # Automated evaluation
            auto_eval = next((e for e in r2_submission.evaluations if e.type == "automated"), None)
            if auto_eval:
                r2_score += (auto_eval.auto_score or 0.0)
                if auto_eval.total_count > 0:
                    r2_pass_rate = round(auto_eval.pass_count / auto_eval.total_count, 4)
            
            # Human evaluation for Round 2 (technique used)
            human_r2_evals = [e for e in r2_submission.evaluations if e.type == "human" and e.status == "submitted"]
            r2_human_vals = []
            for ev in human_r2_evals:
                for sc in ev.scores:
                    if sc.dimension == "technique_used":
                        r2_human_vals.append(sc.value)
            if r2_human_vals:
                r2_score += round(sum(r2_human_vals) / len(r2_human_vals), 2)

        # Most recent final submission timestamp
        candidates = [t for t in [r1_latest_ts, r2_ts] if t is not None]
        final_ts = max(candidates) if candidates else None

        total_score = round(avg_r1_score + r2_score, 2)

        entries_data.append({
            "hackathon_id": hackathon_id,
            "team_id": team.id,
            "team_name": team.name,
            "round1_score": avg_r1_score,
            "round2_score": round(r2_score, 2),
            "total_score": total_score,
            "round2_pass_rate": r2_pass_rate,
            "round1_human_score": avg_r1_score,
            "final_submission_timestamp": final_ts
        })

    # Deterministic 3-Tier Tie-Breaking Sort (SRS Section 5.6):
    # Tier 1: Total score DESC
    # Tier 2: Round 2 % passed DESC
    # Tier 3: Round 1 human score DESC
    # Tier 4: Earlier final submission timestamp ASC (None treated as latest)
    default_max_date = datetime(2099, 12, 31)
    entries_data.sort(
        key=lambda x: (
            -x["total_score"],
            -x["round2_pass_rate"],
            -x["round1_human_score"],
            x["final_submission_timestamp"] or default_max_date
        )
    )

    # Sync cache in DB
    db.query(LeaderboardEntry).filter(LeaderboardEntry.hackathon_id == hackathon_id).delete()
    db.flush()

    saved_entries = []
    for rank_idx, item in enumerate(entries_data, start=1):
        lb_entry = LeaderboardEntry(
            hackathon_id=item["hackathon_id"],
            team_id=item["team_id"],
            team_name=item["team_name"],
            round1_score=item["round1_score"],
            round2_score=item["round2_score"],
            total_score=item["total_score"],
            round2_pass_rate=item["round2_pass_rate"],
            round1_human_score=item["round1_human_score"],
            final_submission_timestamp=item["final_submission_timestamp"],
            rank=rank_idx
        )
        db.add(lb_entry)
        saved_entries.append(lb_entry)

    db.commit()
    return saved_entries
