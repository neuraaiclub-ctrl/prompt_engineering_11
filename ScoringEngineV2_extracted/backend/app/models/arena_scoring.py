import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class ArenaChallengeSpec(Base):
    __tablename__ = "arena_challenge_specs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_bank_item_id = Column(String, ForeignKey("prompt_bank_items.id"), nullable=False, unique=True, index=True)
    spec_version = Column(Integer, default=1, nullable=False)
    spec = Column(JSON, nullable=False) # The JSON defining execution, test_cases, output_contract, constraints, rubric_anchors
    status = Column(String, default="draft", nullable=False) # draft, validated, published
    validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prompt_item = relationship("PromptBankItem")

class ArenaScoringJob(Base):
    __tablename__ = "arena_scoring_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("arena_submissions.id"), nullable=False, index=True)
    wave_id = Column(String, nullable=True, index=True) # Optional grouping
    profile_id = Column(String, nullable=False)
    degradation_level = Column(String, nullable=False)
    status = Column(String, default="queued", nullable=False, index=True) # queued, locked, succeeded, failed, dead_lettered
    lock_token = Column(String, nullable=True) # Worker UUID
    lease_expires_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submission = relationship("ArenaSubmission")
    
    __table_args__ = (
        UniqueConstraint("submission_id", "profile_id", name="unique_sub_profile_job"),
    )

class ArenaScoringRun(Base):
    __tablename__ = "arena_scoring_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("arena_submissions.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("arena_scoring_jobs.id"), nullable=False)
    engine_version = Column(String, nullable=False)
    spec_version = Column(Integer, nullable=False)
    rubric_version = Column(Integer, nullable=False)
    models_used = Column(JSON, nullable=False) # Which models were actually queried
    status = Column(String, default="running", nullable=False) # running, succeeded, failed, needs_review
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    submission = relationship("ArenaSubmission")
    job = relationship("ArenaScoringJob")
    dimension_scores = relationship("ArenaDimensionScore", back_populates="run", cascade="all, delete-orphan")
    test_results = relationship("ArenaTestResult", back_populates="run", cascade="all, delete-orphan")

class ArenaDimensionScore(Base):
    __tablename__ = "arena_dimension_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("arena_scoring_runs.id"), nullable=False, index=True)
    dimension = Column(String, nullable=False) # clarity, specificity, context, output_format, constraints
    behavioral_score = Column(Float, nullable=False)
    rubric_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False) # Aggregated 0-20
    confidence = Column(Float, nullable=False) # 0.0-1.0
    evidence = Column(JSON, nullable=False) # Spans, checks, rationale
    
    run = relationship("ArenaScoringRun", back_populates="dimension_scores")

    __table_args__ = (
        UniqueConstraint("run_id", "dimension", name="unique_run_dimension"),
    )

class ArenaTestResult(Base):
    __tablename__ = "arena_test_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("arena_scoring_runs.id"), nullable=False, index=True)
    case_id = Column(String, nullable=False)
    sample_idx = Column(Integer, nullable=False)
    output_text = Column(String, nullable=False)
    checks = Column(JSON, nullable=False) # Array of pass/fail check results
    passed = Column(Boolean, nullable=False) # Aggregate pass/fail for this sample
    latency_ms = Column(Integer, nullable=True)
    tokens = Column(Integer, nullable=True)

    run = relationship("ArenaScoringRun", back_populates="test_results")

class ArenaIntegrityFlag(Base):
    __tablename__ = "arena_integrity_flags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("arena_submissions.id"), nullable=False, index=True)
    kind = Column(String, nullable=False) # copy, injection, duplicate, gibberish
    severity = Column(String, nullable=False) # low, medium, high
    detail = Column(JSON, nullable=True)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    submission = relationship("ArenaSubmission")

class ArenaFinalScore(Base):
    __tablename__ = "arena_final_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("arena_submissions.id"), nullable=False, unique=True)
    clarity_score = Column(Float, nullable=False)
    specificity_score = Column(Float, nullable=False)
    context_score = Column(Float, nullable=False)
    output_format_score = Column(Float, nullable=False)
    constraints_score = Column(Float, nullable=False)
    total = Column(Float, nullable=False) # Sum of the 5
    source = Column(String, nullable=False) # engine, human, blended
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    scoring_run_id = Column(String, ForeignKey("arena_scoring_runs.id"), nullable=True)
    override_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    submission = relationship("ArenaSubmission")

class ArenaProviderUsage(Base):
    """Token bucket usage tracker for preflight and rate limiting."""
    __tablename__ = "arena_provider_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lane_id = Column(String, nullable=False)
    window_start = Column(DateTime, nullable=False) # e.g. truncated to the minute
    count = Column(Integer, default=0, nullable=False)
    tokens = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("lane_id", "window_start", name="unique_lane_window"),
    )

class ArenaScoringState(Base):
    """Singleton for tracking active profile and failover state."""
    __tablename__ = "arena_scoring_state"

    id = Column(String, primary_key=True, default="default-scoring-state")
    version = Column(Integer, default=1, nullable=False) # For CAS (Compare-And-Swap)
    active_profile_id = Column(String, nullable=True)
    profile_frozen = Column(Boolean, default=False, nullable=False)
    failover_policy = Column(String, default="any_lane_down", nullable=False)
    auto_switches_count = Column(Integer, default=0, nullable=False)
    last_switch_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
