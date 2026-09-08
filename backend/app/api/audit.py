from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.core.rbac import require_roles

router = APIRouter(prefix="/admin/audit-log", tags=["Audit Log"])

@router.get("")
def get_audit_logs(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """Read-only admin endpoint for inspecting append-only audit trail."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    
    res = []
    for l in logs:
        res.append({
            "id": l.id,
            "actor_user_id": l.actor_user_id,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "metadata": l.audit_metadata,
            "created_at": l.created_at.isoformat()
        })
    return res
