import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class PromptBankItem(Base):
    __tablename__ = "prompt_bank_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, unique=True, nullable=False, index=True) # e.g. P001, P002...
    dataset_tag = Column(String, default="default", nullable=False, index=True)
    category = Column(String, nullable=False) # marketing, coding, extraction, etc.
    title = Column(String, nullable=False)
    difficulty = Column(String, default="medium") # easy, medium, hard
    original_bad_prompt = Column(String, nullable=False)
    bad_output_evidence = Column(String, nullable=False)
    flawed_reasons = Column(JSON, nullable=True) # List of weaknesses e.g. ["Too vague", "No format specified"]
    expected_improvements = Column(JSON, nullable=True) # Guidance points
    expected_good_prompt = Column(String, nullable=True) # Reference for scoring engine
    created_at = Column(DateTime, default=datetime.utcnow)

class TeamArenaSession(Base):
    __tablename__ = "team_arena_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    arena_id = Column(String, ForeignKey("arena_config.id"), nullable=False, default="default-arena-config")
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    prompt_ids = Column(JSON, nullable=False) # List of 5 prompt_bank_items.id assigned to this team
    current_challenge_index = Column(Integer, default=1, nullable=False) # 1 to 5, 6 when completed
    status = Column(String, default="waiting", nullable=False) # waiting, active, completed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True) # Server timestamp for tie-breaker
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Team")
    
    __table_args__ = (
        UniqueConstraint("team_id", "arena_id", name="unique_team_arena_session"),
    )

class ArenaSubmission(Base):
    __tablename__ = "arena_submissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    arena_id = Column(String, ForeignKey("arena_config.id"), nullable=False, default="default-arena-config")
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    prompt_bank_item_id = Column(String, ForeignKey("prompt_bank_items.id"), nullable=False)
    challenge_index = Column(Integer, nullable=False) # 1 to 5
    submitted_prompt = Column(String, nullable=False)
    # Phase 0 / Defect #4: optional team diagnosis rationale
    diagnosis_notes = Column(String, nullable=True)
    server_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False) # Server authoritative
    status = Column(String, default="locked", nullable=False) # locked, immutable

    team = relationship("Team")
    prompt_item = relationship("PromptBankItem")
    evaluations = relationship("ArenaEvaluation", back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("team_id", "arena_id", "challenge_index", name="unique_team_arena_challenge_submission"),
    )

class ArenaEvaluation(Base):
    __tablename__ = "arena_evaluations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("arena_submissions.id"), nullable=False)
    judge_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 5 Official Characteristics (Clarity, Specificity, Context, Output Format, Constraints)
    clarity_score = Column(Float, default=0.0, nullable=False)
    specificity_score = Column(Float, default=0.0, nullable=False)
    context_score = Column(Float, default=0.0, nullable=False)
    output_format_score = Column(Float, default=0.0, nullable=True)
    output_structure_score = Column(Float, default=0.0, nullable=False) # Legacy alias
    constraints_score = Column(Float, default=0.0, nullable=True)
    relevance_score = Column(Float, default=0.0, nullable=False) # Legacy alias
    
    total_score = Column(Float, default=0.0, nullable=False) # Question Total: 0 to 100 (or legacy 0 to 10)
    judge_feedback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("ArenaSubmission", back_populates="evaluations")
    judge = relationship("User")

    __table_args__ = (
        UniqueConstraint("submission_id", "judge_user_id", name="unique_submission_judge_evaluation"),
    )

class ArenaSecurityEvent(Base):
    __tablename__ = "arena_security_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    arena_id = Column(String, ForeignKey("arena_config.id"), nullable=False, default="default-arena-config")
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False) # tab_switch, window_blur, window_focus, fullscreen_exit, paste_attempt
    violation_count = Column(Integer, default=1, nullable=False)
    client_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    team = relationship("Team")

class ArenaConfig(Base):
    __tablename__ = "arena_config"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False, default="Main Arena")
    is_active = Column(Boolean, default=True, nullable=False)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False, default="hk-2026")
    status = Column(String, default="waiting", nullable=False) # waiting, live, completed, results_available
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    results_released_at = Column(DateTime, nullable=True)
    active_dataset_tag = Column(String, default="default", nullable=False)
    
    # Configurable rules
    challenges_count = Column(Integer, default=5, nullable=False)
    # Phase 0 / Defect #1: 100 points per challenge (5 dims × 20), not 10
    marks_per_challenge = Column(Integer, default=100, nullable=False)
    desktop_required = Column(Boolean, default=True, nullable=False)
    fullscreen_required = Column(Boolean, default=False, nullable=False)
    copy_paste_allowed = Column(Boolean, default=False, nullable=False)
    tab_switch_monitoring = Column(Boolean, default=True, nullable=False)
    max_allowed_violations = Column(Integer, default=3, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_results_released(self) -> bool:
        """Phase 0 / Defect #6: computed property so overview can read it safely."""
        return self.status == "results_available"

class ArchivedTeamArenaSession(Base):
    __tablename__ = 'archive_team_arena_sessions'
    archive_pk = Column(String, primary_key=True)
    arena_id = Column(String, nullable=False)
    id = Column(String, nullable=False)
    team_id = Column(String, nullable=False)
    hackathon_id = Column(String, nullable=False)
    prompt_ids = Column(JSON, nullable=False)
    current_challenge_index = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

class ArchivedArenaSubmission(Base):
    __tablename__ = 'archive_arena_submissions'
    archive_pk = Column(String, primary_key=True)
    arena_id = Column(String, nullable=False)
    id = Column(String, nullable=False)
    team_id = Column(String, nullable=False)
    prompt_bank_item_id = Column(String, nullable=False)
    challenge_index = Column(Integer, nullable=False)
    submitted_prompt = Column(String, nullable=False)
    diagnosis_notes = Column(String, nullable=True)
    server_timestamp = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)

class ArchivedArenaEvaluation(Base):
    __tablename__ = 'archive_arena_evaluations'
    archive_pk = Column(String, primary_key=True)
    arena_id = Column(String, nullable=False)
    id = Column(String, nullable=False)
    submission_id = Column(String, nullable=False)
    judge_user_id = Column(String, nullable=False)
    clarity_score = Column(Float, nullable=False)
    specificity_score = Column(Float, nullable=False)
    context_score = Column(Float, nullable=False)
    output_format_score = Column(Float, nullable=True)
    output_structure_score = Column(Float, nullable=False)
    constraints_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=False)
    total_score = Column(Float, nullable=False)
    judge_feedback = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
