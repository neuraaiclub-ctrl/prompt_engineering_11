from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.rbac import get_current_user, require_roles, get_optional_current_user
from app.core.rate_limiter import enforce_rate_limit
from app.schemas.arena import (
    StartArenaRequest,
    SubmitChallengeRequest,
    SecurityEventRequest,
    JudgeScoreRequest,
    EliminateTeamRequest,
    ArenaConfigUpdateRequest
)
from app.services.arena_service import ArenaService

# Backward-compatibility alias exports
get_or_create_config = ArenaService.get_or_create_config
get_user_team = ArenaService.get_user_team
assign_unique_prompts_for_team = ArenaService.assign_unique_prompts_for_team

router = APIRouter(prefix="/arena", tags=["Prompt Fixing Arena"])

# ---------------------------------------------------------------------------
# Competition Lifecycle & Status Endpoints
# ---------------------------------------------------------------------------
@router.get("/status")
def get_arena_status(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Public / Participant status polling endpoint.
    Returns authoritative server state, start time, and participant session progress if authenticated.
    """
    return ArenaService.get_status(db, current_user)

@router.post("/start")
def start_arena(
    payload: StartArenaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "judge"]))
):
    """
    Judge/Admin authoritative start control.
    Sets status to LIVE with server timestamp and logs audit event.
    """
    return ArenaService.start_competition(db, current_user)

@router.post("/end")
def end_arena(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "judge"]))
):
    """
    Judge/Admin control to end the competition and stop accepting submissions.
    """
    return ArenaService.end_competition(db, current_user)

@router.post("/release-results")
def release_arena_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "judge"]))
):
    """
    Judge/Admin release control. Unlocks detailed educational reports and leaderboard for participants.
    """
    return ArenaService.release_results(db, current_user)

# ---------------------------------------------------------------------------
# Participant Challenge & Submission Endpoints
# ---------------------------------------------------------------------------
@router.get("/my-challenge")
def get_my_arena_challenge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the authenticated team's CURRENT challenge.
    If not yet assigned, generates a 5-challenge unique set from prompt bank.
    Returns strictly the active challenge to prevent competitive leakage.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to access the Arena.")
    return ArenaService.get_my_challenge(db, current_user)

@router.post("/submit-challenge")
def submit_arena_challenge(
    request: Request,
    payload: SubmitChallengeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits an improved prompt for the team's current active challenge.
    Enforces server-authoritative timestamps, immutability, and state transitions.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    enforce_rate_limit(request, "arena_submit", limit=30, window_seconds=60, identifier=current_user.id)
    return ArenaService.submit_challenge(db, current_user, payload)

# ---------------------------------------------------------------------------
# Security & Anti-Cheating Endpoints
# ---------------------------------------------------------------------------
@router.post("/security-event")
def log_security_event(
    request: Request,
    payload: SecurityEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logs suspicious browser deterrence events (tab switches, window blur, fullscreen exits).
    """
    enforce_rate_limit(request, "arena_security_event", limit=60, window_seconds=60, identifier=current_user.id)
    return ArenaService.record_security_event(db, current_user, payload)

# ---------------------------------------------------------------------------
# Judge Portal Endpoints
# ---------------------------------------------------------------------------
@router.get("/judge/overview")
def get_judge_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "judge"]))
):
    """
    Aggregates competition statistics, submissions queue, and security flags for the Judge Portal.
    """
    return ArenaService.get_judge_overview(db, current_user)

@router.post("/judge/score")
def score_arena_submission(
    payload: JudgeScoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "judge"]))
):
    """
    Submits 5-dimension rubric scores (0-2 each) and educational feedback.
    Calculates total score (out of 10) automatically.
    """
    return ArenaService.score_submission(db, current_user, payload)

@router.post("/judge/eliminate")
def eliminate_team(
    payload: EliminateTeamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "judge"]))
):
    """
    Judge/Admin authoritative control to eliminate a team from the competition.
    Freezes further submissions, creates an audit record, and excludes the team from podium winners.
    """
    return ArenaService.eliminate_team(db, current_user, payload)

# ---------------------------------------------------------------------------
# Results & Educational Report Endpoints
# ---------------------------------------------------------------------------
@router.get("/my-results")
def get_my_score_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Participant score dashboard showing overall total, average score,
    authoritative rank, completion timestamp, and per-challenge 5-characteristic breakdown.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return ArenaService.get_team_score_dashboard(db, current_user)

@router.get("/report")
def get_team_performance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Detailed 5-challenge educational performance report for the authenticated team.
    Only accessible once results have been released.
    """
    return ArenaService.get_performance_report(db, current_user)

@router.get("/leaderboard")
def get_arena_leaderboard(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Official leaderboard ranking by:
    1. Average Score DESC (out of 100) / Total Score DESC
    2. Completion Timestamp ASC (tie-breaker: earliest final submission wins!)
    Highlights Top 3 Podium (Winner, Runner-up, 2nd Runner-up).
    """
    return ArenaService.get_leaderboard(db, current_user)
