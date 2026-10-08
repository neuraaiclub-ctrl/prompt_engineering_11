from typing import List, Optional
import os
import time
import threading
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, Role

security_scheme = HTTPBearer(auto_error=False)

_user_cache = {}
_user_cache_lock = threading.Lock()
# How long an authenticated user (and their roles) is served from memory
# without touching the database. A suspended account therefore stops working
# within this many seconds. Call invalidate_user_cache(user_id) after
# suspending/changing roles to apply it immediately.
USER_CACHE_TTL = float(os.getenv("USER_CACHE_TTL", "20"))


def invalidate_user_cache(user_id: Optional[str] = None) -> None:
    with _user_cache_lock:
        if user_id is None:
            _user_cache.clear()
        else:
            _user_cache.pop(user_id, None)


def _load_user(db: Session, user_id: str) -> Optional[User]:
    """Return the user (with roles loaded) from the in-memory cache if fresh,
    otherwise from the DB in ONE query (roles joined, so role checks never
    trigger a second lazy-load query)."""
    now_ts = time.time()

    with _user_cache_lock:
        cached = _user_cache.get(user_id)

    if cached and now_ts - cached[0] < USER_CACHE_TTL:
        try:
            # Attach the detached cached user to this request's session
            # without querying the DB.
            return db.merge(cached[1], load=False)
        except Exception:
            # Cached object unusable (e.g. expired by a commit) -> fall back.
            with _user_cache_lock:
                _user_cache.pop(user_id, None)

    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_id)
        .first()
    )
    if user is not None:
        with _user_cache_lock:
            if len(_user_cache) > 2000:
                _user_cache.clear()
            _user_cache[user_id] = (now_ts, user)
    return user


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

    user = _load_user(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found"
        )

    if user.status != "active":
        invalidate_user_cache(payload["sub"])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended"
        )

    return user


def require_roles(allowed_roles: List[str]):
    def role_checker(
        current_user: User = Depends(get_current_user),
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
        return _load_user(db, payload["sub"])
    except HTTPException:
        # e.g. breaker-open 503: let the client see it instead of silently
        # treating a logged-in user as anonymous.
        raise
    except Exception:
        return None
