import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String, nullable=False)
    college = Column(String, nullable=True) # College / Institution Name
    invite_code = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="forming") # forming, locked, active, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    hackathon = relationship("Hackathon", back_populates="teams")

class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False) # Enforces one team per user
    role = Column(String, default="member") # leader, member
    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_membership")

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="unique_team_user"),
    )
