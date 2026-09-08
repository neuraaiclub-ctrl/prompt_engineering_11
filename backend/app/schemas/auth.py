from pydantic import BaseModel, EmailStr
from typing import Optional, List

class RegisterSchema(BaseModel):
    name: str
    email: str
    password: str
    affiliation: Optional[str] = None

class LoginSchema(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    roles: List[str]

class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    affiliation: Optional[str] = None
    roles: List[str]
    status: str
