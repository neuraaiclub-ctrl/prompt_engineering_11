from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CreateTeamSchema(BaseModel):
    name: str
    hackathon_id: str
    college: Optional[str] = None

class JoinTeamSchema(BaseModel):
    invite_code: str

class AdminRegisterTeamSchema(BaseModel):
    team_name: str
    college: str
    members: List[str]
    hackathon_id: Optional[str] = None

class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    name: str
    email: str
    role: str

class TeamResponse(BaseModel):
    id: str
    name: str
    college: Optional[str] = None
    invite_code: str
    status: str
    members: List[TeamMemberResponse]
