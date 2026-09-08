from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.team import Team, TeamMember
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event
from app.schemas.team import CreateTeamSchema, JoinTeamSchema, AdminRegisterTeamSchema
from app.services.team_service import TeamService

# Backward compatibility re-exports
generate_invite_code = TeamService.generate_invite_code
sanitize_email_slug = TeamService.sanitize_email_slug
generate_strong_password = TeamService.generate_strong_password

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create_team(
    payload: CreateTeamSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return TeamService.create_team(db, payload, current_user)

@router.post("/join")
def join_team(
    payload: JoinTeamSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return TeamService.join_team(db, payload, current_user)

@router.get("/{team_id}")
def get_team_detail(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    is_admin = any(r.name == "admin" for r in current_user.roles)
    is_judge = any(r.name == "judge" for r in current_user.roles)
    is_member = any(m.user_id == current_user.id for m in team.members)
    can_view_private = is_admin or is_judge or is_member

    members_data = []
    for m in team.members:
        members_data.append({
            "user_id": m.user_id,
            "name": m.user.name,
            "email": m.user.email if can_view_private else None,
            "role": m.role
        })

    return {
        "id": team.id,
        "name": team.name,
        "college": team.college,
        "invite_code": team.invite_code if can_view_private else None,
        "status": team.status,
        "members": members_data
    }

@router.delete("/{team_id}/members/me")
def leave_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    membership = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="User is not on this team")

    team = membership.team
    if team.status == "locked":
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Teams are locked. Leaving a team is not allowed during active competition."
        )

    is_leader = membership.role == "leader"
    db.delete(membership)
    db.flush()

    remaining = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    if is_leader and remaining:
        next_leader = remaining[0]
        next_leader.role = "leader"
        log_audit_event(db, action="team.leader_reassigned", target_type="Team", target_id=team_id, actor_user_id=current_user.id, metadata={"new_leader_id": next_leader.user_id})

    db.commit()
    log_audit_event(db, action="team.leave", target_type="Team", target_id=team_id, actor_user_id=current_user.id)
    return {"message": "Left team successfully"}

@router.post("/admin/register", status_code=status.HTTP_201_CREATED)
def admin_register_team(
    payload: AdminRegisterTeamSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Dedicated Admin Team Registration & Credential Provisioning Workflow.
    Delegates to TeamService for atomic provisioning, uniqueness checks, and credentials generation.
    """
    return TeamService.admin_register_team(db, payload, admin_user)

@router.get("/admin/all")
def get_all_teams_admin(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Returns all registered teams for Admin Team Management.
    """
    return TeamService.get_all_teams_admin(db)
