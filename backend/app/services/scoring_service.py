from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from app.core.scoring import (
    validate_rubric_scores,
    check_disagreement,
    recompute_leaderboard,
    ROUND1_DIMENSIONS,
    ROUND2_HUMAN_DIMENSIONS
)

class ScoringService:
    """
    Domain service for rubric score validation, multi-judge divergence checks,
    and deterministic 4-tier leaderboard ranking calculation.
    """
    ROUND1_DIMENSIONS = ROUND1_DIMENSIONS
    ROUND2_HUMAN_DIMENSIONS = ROUND2_HUMAN_DIMENSIONS

    @staticmethod
    def validate_rubric(round_type: str, scores_input: Dict[str, Any]) -> List[Tuple[str, float, Optional[str]]]:
        return validate_rubric_scores(round_type, scores_input)

    @staticmethod
    def evaluate_multi_judge_disagreement(db: Session, submission_id: str) -> bool:
        return check_disagreement(db, submission_id)

    @staticmethod
    def update_leaderboard(db: Session, hackathon_id: str) -> None:
        recompute_leaderboard(db, hackathon_id)
