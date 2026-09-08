from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class StartArenaRequest(BaseModel):
    confirm: bool = True

class SubmitChallengeRequest(BaseModel):
    prompt_text: str = Field(..., min_length=15, max_length=1500)

class SecurityEventRequest(BaseModel):
    event_type: str = Field(..., description="tab_switch, window_blur, window_focus, fullscreen_exit, paste_attempt")
    client_metadata: Optional[Dict[str, Any]] = None

class JudgeScoreRequest(BaseModel):
    submission_id: str
    clarity_score: float = Field(..., ge=0.0, le=2.0)
    context_score: float = Field(..., ge=0.0, le=2.0)
    specificity_score: float = Field(..., ge=0.0, le=2.0)
    output_structure_score: float = Field(..., ge=0.0, le=2.0)
    relevance_score: float = Field(..., ge=0.0, le=2.0)
    judge_feedback: Optional[str] = ""

class ArenaConfigUpdateRequest(BaseModel):
    desktop_required: Optional[bool] = None
    fullscreen_required: Optional[bool] = None
    copy_paste_allowed: Optional[bool] = None
    tab_switch_monitoring: Optional[bool] = None
    max_allowed_violations: Optional[int] = None
