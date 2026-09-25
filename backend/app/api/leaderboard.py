import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hackathon import Hackathon
from app.models.leaderboard import LeaderboardEntry
from app.models.user import User
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event
from app.core.scoring import recompute_leaderboard

router = APIRouter(tags=["Leaderboard & Results"])

@router.get("/hackathons/{hackathon_id}/leaderboard")
def get_leaderboard(
    hackathon_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ranked Leaderboard API (FR-087-091).
    Gated behind explicit Admin results publication action (FR-101).
    Participants are blocked with 403 Forbidden until Admin publishes results.
    """
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    is_admin = any(r.name == "admin" for r in current_user.roles)
    is_judge = any(r.name == "judge" for r in current_user.roles)

    # Gating enforcement: participants cannot see results until published
    if not is_admin and not is_judge and not hackathon.results_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Results have not been published by organizers yet"
        )

    # Ensure cache is fresh
    entries = db.query(LeaderboardEntry).filter(
        LeaderboardEntry.hackathon_id == hackathon_id
    ).order_by(LeaderboardEntry.rank.asc()).all()

    if not entries:
        entries = recompute_leaderboard(hackathon_id, db)

    return [
        {
            "rank": e.rank,
            "team_id": e.team_id,
            "team_name": e.team_name,
            "round1_score": e.round1_score,
            "round2_score": e.round2_score,
            "total_score": e.total_score,
            "round2_pass_rate": e.round2_pass_rate,
            "round1_human_score": e.round1_human_score,
            "final_submission_timestamp": e.final_submission_timestamp.isoformat() if e.final_submission_timestamp else None
        }
        for e in entries
    ]

@router.post("/hackathons/{hackathon_id}/results/publish")
def publish_results(
    hackathon_id: str,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Admin publishes final competition results (FR-097, FR-101, FR-115).
    Unlocks participant results view and fires audit event.
    """
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    hackathon.results_published = True
    db.commit()

    # Recompute final leaderboard
    recompute_leaderboard(hackathon_id, db)

    log_audit_event(
        db,
        action="results.publish",
        target_type="Hackathon",
        target_id=hackathon.id,
        actor_user_id=admin_user.id,
        metadata={"hackathon_id": hackathon.id, "results_published": True}
    )

    return {
        "message": "Competition results successfully published to all participants",
        "results_published": True
    }

@router.get("/hackathons/{hackathon_id}/results/export")
def export_results(
    hackathon_id: str,
    format: str = "json",
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Admin exports final rankings and score breakdown in CSV or JSON format (FR-097).
    """
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    entries = db.query(LeaderboardEntry).filter(
        LeaderboardEntry.hackathon_id == hackathon_id
    ).order_by(LeaderboardEntry.rank.asc()).all()

    if not entries:
        entries = recompute_leaderboard(hackathon_id, db)

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Rank", "Team Name", "Total Score", "Round 1 Score",
            "Round 2 Score", "Round 2 Pass Rate", "Final Submission Time"
        ])
        for e in entries:
            writer.writerow([
                e.rank, e.team_name, e.total_score, e.round1_score,
                e.round2_score, f"{round((e.round2_pass_rate or 0.0) * 100, 1)}%",
                e.final_submission_timestamp.isoformat() if e.final_submission_timestamp else "N/A"
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=hackathon_{hackathon_id}_results.csv"}
        )

    # JSON export
    return {
        "hackathon_id": hackathon_id,
        "exported_at": hackathon.updated_at.isoformat() if getattr(hackathon, 'updated_at', None) else datetime.utcnow().isoformat(),
        "rankings": [
            {
                "rank": e.rank,
                "team_id": e.team_id,
                "team_name": e.team_name,
                "total_score": e.total_score,
                "round1_score": e.round1_score,
                "round2_score": e.round2_score,
                "round2_pass_rate": e.round2_pass_rate,
                "final_submission_timestamp": e.final_submission_timestamp.isoformat() if e.final_submission_timestamp else None
            }
            for e in entries
        ]
    }

@router.get("/spectator/runoff-stream")
def get_spectator_runoff_stream(db: Session = Depends(get_db)):
    """
    Returns active runoff stream matrix data for the spectator UI.
    Fetches the latest Round 2 submissions and evaluations.
    """
    from app.models.team import Team
    from app.models.execution import Submission
    from app.models.evaluation import Evaluation

    teams = db.query(Team).all()
    results = []

    for t in teams:
        # Find latest submission
        sub = db.query(Submission).filter(Submission.team_id == t.id).order_by(Submission.created_at.desc()).first()
        if not sub:
            results.append({"team_name": t.name, "status": "idle", "pass_count": 0, "total_count": 3})
            continue

        eval_rec = db.query(Evaluation).filter(Evaluation.submission_id == sub.id, Evaluation.type == "automated").first()
        if not eval_rec:
            results.append({"team_name": t.name, "status": "testing", "pass_count": 0, "total_count": 3})
        else:
            results.append({
                "team_name": t.name,
                "status": "completed",
                "pass_count": eval_rec.pass_count or 0,
                "total_count": eval_rec.total_count or 3
            })

    return {"stream": results}
