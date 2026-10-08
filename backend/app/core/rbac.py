from typing import List, Optional
import time
import threading
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, Role

security_scheme = HTTPBearer(auto_error=False)

_user_cache = {}
_user_cache_lock = threading.Lock()
USER_CACHE_TTL = 1.0  # Aggressive 1s cache to match arena_service

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload["sub"]
    now_ts = time.time()
    
    with _user_cache_lock:
        cached = _user_cache.get(user_id)
        if cached and now_ts - cached[0] < USER_CACHE_TTL:
            # Merge the detached cached user into the current session without querying the DB
            return db.merge(cached[1], load=False)
            
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended"
        )
        
    with _user_cache_lock:
        if len(_user_cache) > 2000:
            _user_cache.clear()
        _user_cache[user_id] = (now_ts, user)
    
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_roles = [r.name for r in current_user.roles]
        
        # Check if user holds any of the allowed roles
        has_permission = any(role in allowed_roles for role in user_roles)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for roles: {user_roles}. Required: {allowed_roles}"
            )
        return current_user

    return role_checker

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        if not payload or "sub" not in payload:
            return None
        return db.query(User).filter(User.id == payload["sub"]).first()
    except Exception:
        return None
