import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class RegisterSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    affiliation: Optional[str] = Field(None, max_length=150)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format.")
        return clean

class LoginSchema(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format.")
        return clean

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
