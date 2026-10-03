from dotenv import load_dotenv
load_dotenv('.env')

from app.database import SessionLocal
from app.models.hackathon import Hackathon
from app.models.registration import Registration
from app.models.team import Team, TeamMember
from app.models.user import Role, User
from app.core.security import hash_password
import uuid
from datetime import datetime
import re

db = SessionLocal()
try:
    payload_email = "sohamghatol2025.ainds@mmcoe.edu.in"
    clean_phone = "8532264873"
    pwd_hash = hash_password("soha2264")
    now = datetime.utcnow()

    reg = db.query(Registration).filter(Registration.email == payload_email).first()
    is_new = reg is None

    if is_new:
        ext_id = f"FORM-{uuid.uuid4().hex[:8].upper()}"
        reg = Registration(
            id=str(uuid.uuid4()),
            external_registration_id=ext_id,
            team_name="TOPI",
            participant_name="Soham G",
            member2_name="Bharghav G",
            email=payload_email,
            phone=clean_phone,
            department="AI & DS",
            year="3rd Year",
            registration_status="VERIFIED",
            verification_status="VERIFIED",
            account_status="ACTIVE",
            password_hash=pwd_hash,
            password_set=True,
            is_active=True,
            source="google_forms_webhook",
            imported_at=now,
            last_synced_at=now,
        )
        db.add(reg)
    
    db.flush()

    team = db.query(Team).filter(Team.name == "TOPI").first()
    if not team:
        hk = db.query(Hackathon).first()
        hk_id = hk.id if hk else "hk-2026"
        team = Team(
            id=f"team-{uuid.uuid4().hex[:8]}",
            hackathon_id=hk_id,
            name="TOPI",
            college="AI & DS",
            invite_code=f"NR-{uuid.uuid4().hex[:4].upper()}",
            status="forming",
        )
        db.add(team)
        db.flush()

    reg.team_id = team.id

    user = db.query(User).filter(User.email == payload_email).first()
    if not user:
        user = User(
            id=f"usr-{uuid.uuid4().hex[:8]}",
            name="Soham G",
            email=payload_email,
            password_hash=pwd_hash,
            affiliation="AI & DS",
            status="active",
        )
        db.add(user)
        db.flush()
        db.add(Role(user_id=user.id, name="participant"))
    
    reg.user_id = user.id

    if not db.query(TeamMember).filter(TeamMember.user_id == user.id).first():
        count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
        db.add(TeamMember(team_id=team.id, user_id=user.id, role="leader" if count == 0 else "member"))

    db.commit()
    print("SUCCESS")

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
