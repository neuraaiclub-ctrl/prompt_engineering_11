import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Registration(Base):
    __tablename__ = "registrations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    external_registration_id = Column(String, unique=True, index=True, nullable=True)
    team_name = Column(String, nullable=False, index=True)
    participant_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    college = Column(String, nullable=True)
    course = Column(String, nullable=True)
    year = Column(String, nullable=True)
    member_number = Column(Integer, default=1)
    
    # Registration & Account Lifecycle States
    registration_status = Column(String, default="PENDING") # PENDING, VERIFIED, REJECTED, DISABLED, WITHDRAWN
    verification_status = Column(String, default="PENDING") # PENDING, VERIFIED, REJECTED
    account_status = Column(String, default="NOT_PROVISIONED") # NOT_PROVISIONED, ACTIVE, LOCKED, DISABLED
    
    # Credential & Provisioning Metadata
    password_hash = Column(String, nullable=True)
    password_set = Column(Boolean, default=False)
    activation_token = Column(String, nullable=True, index=True)
    activation_token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Sync & Audit Provenance
    source = Column(String, default="google_sheets") # google_sheets, csv_import, manual_admin
    source_row = Column(Integer, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime, default=datetime.utcnow)

    # Missing from source flag (Safety guard against auto-deletion)
    flagged_for_review = Column(Boolean, default=False)
    review_notes = Column(String, nullable=True)

    # Linked Entities
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id])
