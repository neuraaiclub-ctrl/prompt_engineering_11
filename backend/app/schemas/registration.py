from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class RegistrationOut(BaseModel):
    id: str
    external_registration_id: Optional[str] = None
    team_name: str
    participant_name: str
    email: str
    college: Optional[str] = None
    course: Optional[str] = None
    year: Optional[str] = None
    member_number: int = 1
    registration_status: str
    verification_status: str
    account_status: str
    is_active: bool
    source: str
    last_synced_at: Optional[datetime] = None
    flagged_for_review: bool = False
    review_notes: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None

    class Config:
        from_attributes = True

class RegistrationImportReport(BaseModel):
    success: bool
    source: str
    total_rows: int
    created: int
    updated: int
    unchanged: int
    invalid: int
    duplicates: int
    flagged: int
    duration_ms: int
    errors: List[Dict[str, Any]] = []

class ActivatePayload(BaseModel):
    token: str
    password: str

class RegistrationActionPayload(BaseModel):
    notes: Optional[str] = None
