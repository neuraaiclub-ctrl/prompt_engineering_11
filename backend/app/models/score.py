import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Score(Base):
    __tablename__ = "scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String, ForeignKey("evaluations.id"), nullable=False)
    dimension = Column(String, nullable=False) 
    # Round 1: diagnosis_quality, improvement_quality, final_output_quality, documentation_clarity
    # Round 2: technique_used, constraint_compliance, test_pass_rate
    value = Column(Float, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="scores")
