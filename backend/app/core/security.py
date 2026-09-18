import hmac
import hashlib
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import jwt, JWTError
from app.config import settings

# Thread-safe in-memory token revocation blacklist (hash -> expiration datetime)
_token_blacklist_lock = threading.Lock()
_revoked_token_hashes: Dict[str, datetime] = {}

def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _prune_expired_blacklisted_tokens():
    """Prunes expired tokens from the blacklist to prevent unbounded memory growth."""
    now = _get_utc_now()
    with _token_blacklist_lock:
        expired_keys = [k for k, exp in _revoked_token_hashes.items() if exp < now]
        for k in expired_keys:
            del _revoked_token_hashes[k]

def revoke_token(token: str) -> bool:
    """Revokes a JWT token by recording its hash in the blacklist."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)
        else:
            exp_dt = _get_utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with _token_blacklist_lock:
            _revoked_token_hashes[token_hash] = exp_dt
        
        _prune_expired_blacklisted_tokens()
        return True
    except Exception:
        # If decode fails, still blacklist the hash for standard duration
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with _token_blacklist_lock:
            _revoked_token_hashes[token_hash] = _get_utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return True

def is_token_revoked(token: str) -> bool:
    """Checks whether the token has been revoked."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _token_blacklist_lock:
        exp_dt = _revoked_token_hashes.get(token_hash)
        if exp_dt:
            if exp_dt > _get_utc_now():
                return True
            else:
                del _revoked_token_hashes[token_hash]
                return False
    return False

def hash_password(password: str, iterations: int = 100000) -> str:
    """
    Hash password using PBKDF2-HMAC-SHA256 with a cryptographically secure random salt.
    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${derived}"

def is_legacy_hash(hashed_password: str) -> bool:
    """Returns True if the hash was produced with the old single-pass SHA-256 scheme."""
    return not hashed_password.startswith("pbkdf2_sha256$")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a password using constant-time comparison.
    Supports PBKDF2-HMAC-SHA256 and legacy single-pass salted SHA-256.
    """
    if not hashed_password or not plain_password:
        return False

    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            iterations = int(parts[1])
            salt = parts[2]
            expected_hash = parts[3]
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                bytes.fromhex(salt),
                iterations
            ).hex()
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False
    else:
        # Backward compatibility for legacy single-pass hash: sha256(secret_key:password)
        legacy_salted = f"{settings.SECRET_KEY}:{plain_password}"
        legacy_hash = hashlib.sha256(legacy_salted.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = _get_utc_now()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Include unique token ID (jti) and issued-at (iat)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": uuid.uuid4().hex
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    # Check revocation blacklist first
    if is_token_revoked(token):
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_random_token(length: int = 32) -> str:
    """Generates a cryptographically secure random token string."""
    return secrets.token_urlsafe(length)

