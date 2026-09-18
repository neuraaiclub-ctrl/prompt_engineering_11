from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.user import User, Role
from app.models.team import TeamMember
from app.models.registration import Registration
from app.core.security import hash_password, verify_password, create_access_token, revoke_token, is_legacy_hash
from app.core.audit import log_audit_event
from app.core.rate_limiter import enforce_rate_limit

from app.schemas.auth import RegisterSchema, LoginSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)

@router.post("/register", status_code=status.HTTP_403_FORBIDDEN)
def register(request: Request, payload: RegisterSchema, db: Session = Depends(get_db)):
    """
    Direct participant registration is disabled.
    All participants must register externally via the official Google Form registration process.
    """
    enforce_rate_limit(request, "auth_register", limit=10, window_seconds=60)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Participant registration is managed through the official registration form."
    )

@router.post("/login")
def login(request: Request, payload: LoginSchema, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_login", limit=20, window_seconds=60, identifier=payload.email.lower())
    
    email_lower = payload.email.lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_lower).first() if hasattr(User, 'email') else None
    
    # Fallback search if exact case differed
    if not user:
        user = db.query(User).filter(User.email == email_lower).first()

    if not user or not verify_password(payload.password, user.password_hash):
        log_audit_event(
            db,
            action="auth.login_failed",
            target_type="User",
            target_id="unauthenticated",
            actor_user_id=None,
            metadata={"attempted_email": email_lower}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account is not active."
        )

    # Check User account status
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials or account is not active."
        )

    roles = [r.name for r in user.roles]

    # Check registration status for participant accounts
    if "participant" in roles or "team_leader" in roles:
        reg = db.query(Registration).filter(func.lower(Registration.email) == email_lower).first()
        if reg:
            if reg.registration_status in ["REJECTED", "DISABLED", "WITHDRAWN"] or reg.account_status in ["DISABLED", "LOCKED"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid credentials or account is not active."
                )
            if reg.registration_status != "VERIFIED" and reg.account_status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid credentials or account is not active."
                )

    # Resolve Team Membership
    team_member = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
    team_id = team_member.team_id if team_member else None

    # Transparently upgrade legacy password hash to salted PBKDF2
    if is_legacy_hash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()

    token_data = {
        "sub": user.id,
        "email": user.email,
        "roles": roles,
        "team_id": team_id
    }
    token = create_access_token(data=token_data)

    log_audit_event(db, action="auth.login", target_type="User", target_id=user.id, actor_user_id=user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": roles,
            "team_id": team_id
        }
    }

@router.post("/logout")
def logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)):
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials)
    return {"message": "Successfully logged out"}
