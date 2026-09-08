from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, Role
from app.core.security import hash_password, verify_password, create_access_token
from app.core.audit import log_audit_event

from app.schemas.auth import RegisterSchema, LoginSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterSchema, db: Session = Depends(get_db)):
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
def login(payload: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )
    
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
def logout():
    return {"message": "Successfully logged out"}
