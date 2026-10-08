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
) -> Optional[AuditLog]:
    """Record an append-only audit log entry. Never raises — audit failure must not block login."""
    try:
        log_entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            audit_metadata=metadata or {}
        )
        db.add(log_entry)
        db.commit()
        # Note: do NOT call db.refresh() here — it makes an extra DB round-trip
        # that can fail if the Supabase connection drops after commit.
        return log_entry
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        import logging
        logging.getLogger(__name__).warning(f"[Audit] Failed to log event '{action}': {e}")
        return None
