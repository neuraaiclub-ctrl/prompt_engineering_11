from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class SubmitScoresSchema(BaseModel):
    scores: Dict[str, Any]
    comment: Optional[str] = None

class AssignJudgeSchema(BaseModel):
    judge_user_id: str

class JudgeAssignmentResponse(BaseModel):
    submission_id: str
    team_id: str
    team_name: str
    challenge_id: str
    challenge_title: str
    round_type: str
    round_number: int
    submitted_at: str
    status: str
    my_evaluation_id: Optional[str] = None
