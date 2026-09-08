import random
import string
import secrets
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.user import User, Role
from app.models.team import Team, TeamMember
from app.models.hackathon import Hackathon
from app.core.security import hash_password
from app.core.audit import log_audit_event
from app.schemas.team import CreateTeamSchema, JoinTeamSchema, AdminRegisterTeamSchema

class TeamService:
    @staticmethod
    def generate_invite_code() -> str:
        return "NR-" + "".join(random.choices(string.digits, k=4))

    @staticmethod
    def sanitize_email_slug(name: str) -> str:
        cleaned = re.sub(r'[^a-zA-Z0-9]+', '.', name.strip().lower()).strip('.')
        return cleaned if cleaned else "team"

    @staticmethod
    def generate_strong_password(length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            pwd = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in pwd)
                and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*" for c in pwd)):
                return pwd

    @classmethod
    def create_team(cls, db: Session, payload: CreateTeamSchema, current_user: User) -> Dict[str, Any]:
        existing_member = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of an existing team. Leave current team first."
            )

        existing_team = db.query(Team).filter(
            Team.hackathon_id == payload.hackathon_id,
            Team.name == payload.name
        ).first()
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A team with this name already exists in this hackathon"
            )

        team = Team(
            hackathon_id=payload.hackathon_id,
            name=payload.name,
            college=payload.college,
            invite_code=cls.generate_invite_code(),
            status="forming"
        )
        db.add(team)
        db.flush()

        team_member = TeamMember(team_id=team.id, user_id=current_user.id, role="leader")
        db.add(team_member)

        if not any(r.name == "team_leader" for r in current_user.roles):
            db.add(Role(user_id=current_user.id, name="team_leader"))

        db.commit()
        db.refresh(team)

        log_audit_event(db, action="team.create", target_type="Team", target_id=team.id, actor_user_id=current_user.id)

        return {
            "id": team.id,
            "name": team.name,
            "invite_code": team.invite_code,
            "status": team.status,
            "members_count": 1
        }

    @classmethod
    def join_team(cls, db: Session, payload: JoinTeamSchema, current_user: User) -> Dict[str, Any]:
        existing_member = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of a team. Leave current team first."
            )

        team = db.query(Team).filter(Team.invite_code == payload.invite_code.upper()).first()
        if not team:
            raise HTTPException(status_code=404, detail="Invalid team invite code")

        if team.status == "locked":
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Teams are locked for this round. Roster changes disabled."
            )

        if len(team.members) >= 4:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Team has reached maximum capacity (4 members)"
            )

        team_member = TeamMember(team_id=team.id, user_id=current_user.id, role="member")
        db.add(team_member)
        db.commit()

        log_audit_event(db, action="team.join", target_type="Team", target_id=team.id, actor_user_id=current_user.id)

        return {
            "message": f"Successfully joined team {team.name}",
            "team_id": team.id,
            "team_name": team.name
        }

    @classmethod
    def admin_register_team(cls, db: Session, payload: AdminRegisterTeamSchema, admin_user: User) -> Dict[str, Any]:
        team_name = (payload.team_name or "").strip()
        college = (payload.college or "").strip()
        raw_members = [m.strip() for m in (payload.members or []) if m and m.strip()]

        if not team_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Team name is required and cannot be blank."
            )
        if not college:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="College / Institution name is required and cannot be blank."
            )

        if len(raw_members) < 1 or len(raw_members) > 4:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Team must have between 1 and 4 members (received {len(raw_members)})."
            )

        lower_members = [m.lower() for m in raw_members]
        if len(lower_members) != len(set(lower_members)):
            for m in raw_members:
                if lower_members.count(m.lower()) > 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Duplicate member detected inside the same team: '{m}' is entered multiple times."
                    )

        hk_id = payload.hackathon_id
        if not hk_id:
            hk = db.query(Hackathon).first()
            if not hk:
                hk = Hackathon(
                    id="hk-2026",
                    title="NEURA Prompt Engineering Hackathon 2026",
                    status="active"
                )
                db.add(hk)
                db.flush()
            hk_id = hk.id
        else:
            hk = db.query(Hackathon).filter(Hackathon.id == hk_id).first()
            if not hk:
                raise HTTPException(status_code=404, detail="Specified hackathon not found.")

        existing_team = db.query(Team).filter(
            Team.hackathon_id == hk_id,
            func.lower(Team.name) == team_name.lower()
        ).first()
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The team name '{team_name}' is already registered in this hackathon."
            )

        for m_name in raw_members:
            existing_participant = db.query(User).join(TeamMember).join(Team).filter(
                Team.hackathon_id == hk_id,
                func.lower(User.name) == m_name.lower()
            ).first()
            if existing_participant:
                team_title = existing_participant.team_membership.team.name if existing_participant.team_membership else "another team"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Member '{m_name}' is already associated with another participating team ({team_title})."
                )

        slug = cls.sanitize_email_slug(team_name)
        base_email = f"{slug}@neura.io"
        generated_email = base_email
        counter = 1
        while db.query(User).filter(User.email == generated_email.lower()).first():
            generated_email = f"{slug}.{counter}@neura.io"
            counter += 1

        raw_password = cls.generate_strong_password(10)
        hashed_pwd = hash_password(raw_password)

        try:
            team = Team(
                hackathon_id=hk_id,
                name=team_name,
                college=college,
                invite_code=cls.generate_invite_code(),
                status="forming"
            )
            db.add(team)
            db.flush()

            leader_name = raw_members[0]
            leader_user = User(
                name=leader_name,
                email=generated_email.lower(),
                password_hash=hashed_pwd,
                affiliation=college,
                status="active"
            )
            db.add(leader_user)
            db.flush()

            db.add(Role(user_id=leader_user.id, name="participant"))
            db.add(Role(user_id=leader_user.id, name="team_leader"))
            db.add(TeamMember(team_id=team.id, user_id=leader_user.id, role="leader"))

            for idx in range(1, len(raw_members)):
                m_name = raw_members[idx]
                m_slug = cls.sanitize_email_slug(m_name)
                m_email = f"{m_slug}.{slug}@neura.io"
                m_counter = 1
                while db.query(User).filter(User.email == m_email.lower()).first():
                    m_email = f"{m_slug}.{slug}.{m_counter}@neura.io"
                    m_counter += 1

                m_user = User(
                    name=m_name,
                    email=m_email.lower(),
                    password_hash=hashed_pwd,
                    affiliation=college,
                    status="active"
                )
                db.add(m_user)
                db.flush()

                db.add(Role(user_id=m_user.id, name="participant"))
                db.add(TeamMember(team_id=team.id, user_id=m_user.id, role="member"))

            log_audit_event(
                db,
                action="TEAM_REGISTERED",
                target_type="TEAM",
                target_id=team.id,
                actor_user_id=admin_user.id,
                metadata={
                    "team_name": team.name,
                    "college": team.college,
                    "member_count": len(raw_members),
                    "login_email": generated_email.lower()
                }
            )

            db.commit()
            db.refresh(team)

            return {
                "message": "Team successfully registered and provisioned.",
                "team": {
                    "id": team.id,
                    "name": team.name,
                    "college": team.college,
                    "invite_code": team.invite_code,
                    "status": team.status,
                    "members": raw_members,
                    "login_email": generated_email.lower()
                },
                "credentials": {
                    "email": generated_email.lower(),
                    "password": raw_password
                }
            }
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to provision team atomically: {str(e)}"
            )

    @classmethod
    def get_all_teams_admin(cls, db: Session) -> List[Dict[str, Any]]:
        teams = db.query(Team).order_by(Team.created_at.desc()).all()
        results = []
        for t in teams:
            members_list = [m.user.name for m in t.members if m.user]
            leader_member = next((m for m in t.members if m.role == "leader"), None)
            leader_email = leader_member.user.email if (leader_member and leader_member.user) else None
            results.append({
                "id": t.id,
                "name": t.name,
                "college": t.college or "N/A",
                "invite_code": t.invite_code,
                "status": t.status,
                "members": members_list,
                "members_count": len(members_list),
                "login_email": leader_email,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
        return results
