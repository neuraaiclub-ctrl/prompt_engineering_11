from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    target_type: str,
    target_id: str,
    actor_user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Record an append-only audit log entry."""
    log_entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        audit_metadata=metadata or {}
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
