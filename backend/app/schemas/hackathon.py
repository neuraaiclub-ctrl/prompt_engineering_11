from pydantic import BaseModel
from typing import Optional

class HackathonCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None

class RoundCreateSchema(BaseModel):
    type: str  # round1_fix_the_prompt or round2_constraint_challenge
    duration_seconds: Optional[int] = 180

class TimerResponse(BaseModel):
    round_id: str
    remaining_seconds: int
    is_active: bool
    status: str
