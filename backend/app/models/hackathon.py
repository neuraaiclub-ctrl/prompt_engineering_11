import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="draft") # draft, active, ended
    registration_open = Column(Boolean, default=True)
    results_published = Column(Boolean, default=False)
    min_team_size = Column(Integer, default=1)
    max_team_size = Column(Integer, default=4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teams = relationship("Team", back_populates="hackathon")
    rounds = relationship("Round", back_populates="hackathon", order_by="Round.order_index")

class Round(Base):
    __tablename__ = "rounds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    type = Column(String, nullable=False) # round1_fix_the_prompt, round2_constraint_challenge
    order_index = Column(Integer, nullable=False, default=1)
    duration_seconds = Column(Integer, default=180) # 3 minutes default
    start_at = Column(DateTime, nullable=True)
    status = Column(String, default="draft") # draft, published, active, paused, ended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hackathon = relationship("Hackathon", back_populates="rounds")
