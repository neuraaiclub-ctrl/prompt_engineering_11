from pydantic import BaseModel
from typing import Optional, List, Any

# Participant-Safe Schemas (Strictly omitting hidden test details and internal hints)
class ParticipantPromptCaseSchema(BaseModel):
    id: str
    challenge_id: str
    title: str
    original_prompt: str
    bad_output: str
    bad_output_screenshot_url: Optional[str] = None
    difficulty: str
    description: Optional[str] = None

class ParticipantConstraintSchema(BaseModel):
    type: str
    max_tokens: Optional[int] = 50
    task_description: str
    format_rule: Optional[str] = None

class ParticipantConstraintChallengeSchema(BaseModel):
    id: str
    round_id: str
    type: str
    title: str
    status: str
    constraint: Optional[ParticipantConstraintSchema] = None
    hidden_test_count: int

# Strict Isolation Schema for Participant (Zero hidden input/output fields)
class ParticipantTestCaseSchema(BaseModel):
    id: str
    challenge_id: str
    visibility: str # strictly 'hidden' - no 'input', 'expected_output', or 'eval_rule'

# Admin-Only Schemas (Privileged access with full details)
class AdminTestCaseSchema(BaseModel):
    id: str
    challenge_id: str
    input: str
    expected_output: str
    eval_rule: Optional[Any] = None
    visibility: str
