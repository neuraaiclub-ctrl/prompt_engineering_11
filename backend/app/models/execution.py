import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    prompt_text = Column(String, nullable=False)
    system_prompt_text = Column(String, nullable=True)
    explanation = Column(String, nullable=False) # Mandatory non-empty 1-line explanation
    is_final = Column(Boolean, default=False)
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    challenge = relationship("Challenge", back_populates="prompt_versions")
    team = relationship("Team")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("challenge_id", "team_id", "version_number", name="unique_challenge_team_version"),
    )

class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_version_id = Column(String, ForeignKey("prompt_versions.id"), nullable=True)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=True)
    test_case_id = Column(String, ForeignKey("test_cases.id"), nullable=True)
    model = Column(String, default="gpt-4o-mini")
    output_text = Column(String, nullable=True)
    status = Column(String, default="success") # queued, running, success, error, timeout
    token_count_prompt = Column(Integer, default=0)
    token_count_output = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    final_prompt_version_id = Column(String, ForeignKey("prompt_versions.id"), nullable=True)
    prompt_text = Column(String, nullable=False)
    explanation = Column(String, nullable=True)
    status = Column(String, default="locked") # submitted, locked
    constraint_violated = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    challenge = relationship("Challenge", back_populates="submissions")
    team = relationship("Team")
    evaluations = relationship("Evaluation", back_populates="submission", cascade="all, delete-orphan")

    @property
    def evaluation(self):
        return self.evaluations[0] if self.evaluations else None

    __table_args__ = (
        # DB-level unique constraint preventing double submission
        UniqueConstraint("challenge_id", "team_id", name="unique_challenge_team_submission"),
    )
