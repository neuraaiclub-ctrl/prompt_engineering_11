from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List

class StartArenaRequest(BaseModel):
    confirm: bool = True

class SubmitChallengeRequest(BaseModel):
    prompt_text: str = Field(..., min_length=15, max_length=5000)

class SecurityEventRequest(BaseModel):
    event_type: str = Field(..., description="tab_switch, window_blur, window_focus, fullscreen_exit, paste_attempt, copy_attempt, context_menu_attempt")
    client_metadata: Optional[Dict[str, Any]] = None

class JudgeScoreRequest(BaseModel):
    submission_id: str
    clarity_score: float = Field(..., description="Clarity score (0, 10, or 20; or legacy 0.0-2.0)")
    specificity_score: float = Field(..., description="Specificity score (0, 10, or 20; or legacy 0.0-2.0)")
    context_score: float = Field(..., description="Context score (0, 10, or 20; or legacy 0.0-2.0)")
    output_format_score: Optional[float] = Field(None, description="Output Format score (0, 10, or 20)")
    output_structure_score: Optional[float] = Field(None, description="Legacy alias for Output Format")
    constraints_score: Optional[float] = Field(None, description="Constraints score (0, 10, or 20)")
    relevance_score: Optional[float] = Field(None, description="Legacy alias for Constraints")
    judge_feedback: Optional[str] = Field("", max_length=1000)

    @field_validator(
        "clarity_score", "specificity_score", "context_score",
        "output_format_score", "output_structure_score",
        "constraints_score", "relevance_score",
        mode="before"
    )
    @classmethod
    def validate_score_discrete_levels(cls, v):
        if v is None:
            return None
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("Score must be numeric.")
        # Only official 0/10/20 discrete rubric levels and legacy 0-2 scale levels are permitted
        valid_values = {0.0, 10.0, 20.0, 0.5, 1.0, 1.5, 2.0}
        if val not in valid_values:
            raise ValueError(f"Score {val} is not a valid rubric score. Only 0, 10, 20 (or legacy 0.0-2.0) are allowed.")
        return val

class EliminateTeamRequest(BaseModel):
    team_id: str
    reason: str = Field(..., min_length=3, max_length=500, description="Authoritative justification for team elimination")

class ArenaConfigUpdateRequest(BaseModel):
    desktop_required: Optional[bool] = None
    fullscreen_required: Optional[bool] = None
    copy_paste_allowed: Optional[bool] = None
    tab_switch_monitoring: Optional[bool] = None
    max_allowed_violations: Optional[int] = None
