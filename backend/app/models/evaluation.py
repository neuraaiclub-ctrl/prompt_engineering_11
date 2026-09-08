import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    type = Column(String, default="automated") # automated, human
    status = Column(String, default="submitted") # in_progress, submitted
    
    # Automated Score fields
    auto_score = Column(Float, default=0.0)
    pass_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    format_compliant = Column(String, default="true")
    
    # Human Judging score fields
    judge_score = Column(Float, nullable=True)
    judge_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    judge_comment = Column(String, nullable=True)
    disagreement_flag = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="evaluations")
    judge = relationship("User", foreign_keys=[judge_user_id])
    scores = relationship("Score", back_populates="evaluation", cascade="all, delete-orphan")
