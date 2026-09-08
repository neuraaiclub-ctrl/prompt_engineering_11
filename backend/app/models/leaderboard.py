import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    team_name = Column(String, nullable=False)
    
    round1_score = Column(Float, default=0.0)
    round2_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    
    # Tie-break tracking fields (SRS Section 5.6)
    round2_pass_rate = Column(Float, default=0.0)
    round1_human_score = Column(Float, default=0.0)
    final_submission_timestamp = Column(DateTime, nullable=True)
    
    rank = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hackathon = relationship("Hackathon")
    team = relationship("Team")
