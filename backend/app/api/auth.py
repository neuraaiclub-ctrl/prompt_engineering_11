from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, Role
from app.core.security import hash_password, verify_password, create_access_token, revoke_token, is_legacy_hash
from app.core.audit import log_audit_event
from app.core.rate_limiter import enforce_rate_limit

from app.schemas.auth import RegisterSchema, LoginSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, payload: RegisterSchema, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_register", limit=10, window_seconds=60)
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with this email already exists"
        )
    
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        affiliation=payload.affiliation,
        status="active"
    )
    db.add(user)
    db.flush()

    # Assign default participant role
    role = Role(user_id=user.id, name="participant")
    db.add(role)
    db.commit()
    db.refresh(user)

    log_audit_event(db, action="auth.register", target_type="User", target_id=user.id, actor_user_id=user.id)

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "email": user.email,
        "role": "participant"
    }

@router.post("/login")
def login(request: Request, payload: LoginSchema, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_login", limit=20, window_seconds=60, identifier=payload.email.lower())
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        log_audit_event(
            db,
            action="auth.login_failed",
            target_type="User",
            target_id="unauthenticated",
            actor_user_id=None,
            metadata={"attempted_email": payload.email.lower()}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )
    
    # Transparently upgrade legacy SHA-256 password hash to salted PBKDF2
    if is_legacy_hash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
    
    roles = [r.name for r in user.roles]
    token = create_access_token(data={"sub": user.id, "email": user.email, "roles": roles})

    log_audit_event(db, action="auth.login", target_type="User", target_id=user.id, actor_user_id=user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": roles
        }
    }

@router.post("/logout")
def logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)):
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials)
    return {"message": "Successfully logged out"}
