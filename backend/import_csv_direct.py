from dotenv import load_dotenv
load_dotenv('.env')

from app.database import SessionLocal
from app.models.hackathon import Hackathon
from app.models.registration import Registration
from app.models.team import Team, TeamMember
from app.models.user import Role, User
from app.core.security import hash_password
import uuid
import csv
from datetime import datetime

db = SessionLocal()
try:
    with open('responses.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            email = row.get('Email Address', '').strip()
            if not email:
                continue
                
            clean_phone = row.get('Mobile Number', '').strip().replace('+91', '').replace(' ', '')
            pwd_hash = hash_password(row.get('Generated Password', '').strip())
            now = datetime.utcnow()
            
            reg = db.query(Registration).filter(Registration.email == email).first()
            is_new = reg is None

            team_name = row.get('Team Name', '').strip() or 'Team'
            member1_name = row.get('Member 1 Name (Team Leader)', '').strip() or 'Leader'
            member2_name = row.get('Member 2 Name (Optional)', '').strip()
            department = row.get('Department / Branch', '').strip() or 'Dept'
            year = row.get('Year of Study', '').strip() or '1st Year'

            if is_new:
                ext_id = f"FORM-{uuid.uuid4().hex[:8].upper()}"
                reg = Registration(
                    id=str(uuid.uuid4()),
                    external_registration_id=ext_id,
                    team_name=team_name,
                    participant_name=member1_name,
                    member2_name=member2_name,
                    email=email,
                    phone=clean_phone,
                    department=department,
                    year=year,
                    registration_status="VERIFIED",
                    verification_status="VERIFIED",
                    account_status="ACTIVE",
                    password_hash=pwd_hash,
                    password_set=True,
                    is_active=True,
                    source="csv_import",
                    imported_at=now,
                    last_synced_at=now,
                )
                db.add(reg)
            
            db.flush()

            team = db.query(Team).filter(Team.name == team_name).first()
            if not team:
                hk = db.query(Hackathon).first()
                hk_id = hk.id if hk else "hk-2026"
                team = Team(
                    id=f"team-{uuid.uuid4().hex[:8]}",
                    hackathon_id=hk_id,
                    name=team_name,
                    college=department,
                    invite_code=f"NR-{uuid.uuid4().hex[:4].upper()}",
                    status="forming",
                )
                db.add(team)
                db.flush()

            reg.team_id = team.id

            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    id=f"usr-{uuid.uuid4().hex[:8]}",
                    name=member1_name,
                    email=email,
                    password_hash=pwd_hash,
                    affiliation=department,
                    status="active",
                )
                db.add(user)
                db.flush()
                db.add(Role(user_id=user.id, name="participant"))
            else:
                user.password_hash = pwd_hash
                user.name = member1_name
            
            reg.user_id = user.id

            if not db.query(TeamMember).filter(TeamMember.user_id == user.id).first():
                tcount = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
                db.add(TeamMember(team_id=team.id, user_id=user.id, role="leader" if tcount == 0 else "member"))

            count += 1
            print(f"Imported: {email}")

    db.commit()
    print(f"\nSUCCESS! Total records directly imported into Supabase: {count}")

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
