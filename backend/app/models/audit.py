import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id = Column(String, nullable=True) # Nullable for unauthenticated/system actions
    action = Column(String, nullable=False) # e.g. auth.register, team.create, round.start
    target_type = Column(String, nullable=False) # e.g. User, Team, Round
    target_id = Column(String, nullable=False)
    audit_metadata = Column(JSON, nullable=True) # Renamed to audit_metadata to avoid SQLAlchemy reserved keywords
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
