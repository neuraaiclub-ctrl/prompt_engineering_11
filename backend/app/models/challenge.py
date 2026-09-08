import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    round_id = Column(String, ForeignKey("rounds.id"), nullable=False)
    type = Column(String, nullable=False) # prompt_case, constraint_challenge
    title = Column(String, nullable=False)
    status = Column(String, default="published") # draft, published
    created_at = Column(DateTime, default=datetime.utcnow)

    round = relationship("Round")
    prompt_case = relationship("PromptCase", back_populates="challenge", uselist=False, cascade="all, delete-orphan")
    constraint = relationship("Constraint", back_populates="challenge", uselist=False, cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="challenge", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="challenge")
    prompt_versions = relationship("PromptVersion", back_populates="challenge")

class PromptCase(Base):
    __tablename__ = "prompt_cases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_id = Column(String, ForeignKey("challenges.id"), unique=True, nullable=False)
    original_prompt = Column(String, nullable=False)
    bad_output = Column(String, nullable=False)
    bad_output_screenshot_url = Column(String, nullable=True)
    broken_reason = Column(String, nullable=False) # vague, no_format_specified, contradictory, no_role_context, missing_edge_cases, other
    difficulty = Column(String, default="medium") # easy, medium, hard
    description = Column(String, nullable=True)

    challenge = relationship("Challenge", back_populates="prompt_case")

class Constraint(Base):
    __tablename__ = "constraints"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_id = Column(String, ForeignKey("challenges.id"), unique=True, nullable=False)
    type = Column(String, nullable=False) # max_tokens_n, zero_shot, one_shot, no_system_prompt, generalize_unseen_inputs, valid_json_always
    max_tokens = Column(Integer, nullable=True, default=50)
    task_description = Column(String, nullable=False)
    format_rule = Column(String, nullable=True)

    challenge = relationship("Challenge", back_populates="constraint")

class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    input = Column(String, nullable=False) # Hidden by default
    expected_output = Column(String, nullable=False) # Hidden by default
    eval_rule = Column(JSON, nullable=True) # Hidden by default (e.g. {"type": "exact"})
    visibility = Column(String, default="hidden") # hidden, revealed

    challenge = relationship("Challenge", back_populates="test_cases")
