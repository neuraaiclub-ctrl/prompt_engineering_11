import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal, init_db
from app.models.user import User, Role
from app.models.team import Team, TeamMember
from app.models.hackathon import Hackathon
from app.models.arena import ArenaConfig
from app.core.security import hash_password
import uuid

def seed_test_data():
    db = SessionLocal()
    
    # Check if a Hackathon exists, otherwise create one
    hackathon = db.query(Hackathon).first()
    if not hackathon:
        hackathon = Hackathon(
            title="NEURA Prompt Engineering Hackathon 2026",
            description="The premier AI hackathon.",
            status="active"
        )
        db.add(hackathon)
        db.commit()
        db.refresh(hackathon)
        print(f"Created Hackathon: {hackathon.id}")
    else:
        print(f"Using existing Hackathon: {hackathon.id}")

    # Ensure ArenaConfig exists
    arena_config = db.query(ArenaConfig).first()
    if not arena_config:
        arena_config = ArenaConfig(status="inactive", challenges_count=5)
        db.add(arena_config)
        db.commit()

    teams_data = [
        {"name": "Neural Ninjas", "code": "NR-4827", "members": [("Alex Mercer", "alex@neuralninjas.io"), ("Elena Rostova", "elena@neuralninjas.io"), ("Kaelen Vance", "kaelen@neuralninjas.io")]},
        {"name": "Code Warriors", "code": "CW-1029", "members": [("David Kim", "david@codewarriors.io"), ("Sarah L.", "sarah@codewarriors.io")]},
        {"name": "Byte Force", "code": "BF-3049", "members": [("Priya Nair", "priya@byteforce.io"), ("Jonah H.", "jonah@byteforce.io")]},
        {"name": "Ghost Protocol", "code": "GP-9912", "members": [("Aria Stark", "aria@ghostprotocol.io"), ("Chen Wei", "chen@ghostprotocol.io")]},
    ]

    password_hash = hash_password("password123")
    admin_password_hash = hash_password("admin123")
    
    # Create Admin User
    admin_email = "admin@neura.dev"
    admin_user = db.query(User).filter(User.email == admin_email).first()
    if not admin_user:
        admin_user = User(
            name="Super Admin",
            email=admin_email,
            password_hash=admin_password_hash
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Assign Admin role
        admin_role = Role(user_id=admin_user.id, name="admin")
        db.add(admin_role)
        db.commit()
        print(f"Created Admin User: {admin_email}")
        
    
    for t_data in teams_data:
        # Create Team
        team = db.query(Team).filter(Team.invite_code == t_data["code"]).first()
        if not team:
            team = Team(
                hackathon_id=hackathon.id,
                name=t_data["name"],
                invite_code=t_data["code"],
                status="locked"
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            print(f"Created Team: {team.name}")
        
        is_leader = True
        for m_name, m_email in t_data["members"]:
            # Create User
            user = db.query(User).filter(User.email == m_email).first()
            if not user:
                user = User(
                    name=m_name,
                    email=m_email,
                    password_hash=password_hash
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                
                # Assign Participant role
                role = Role(user_id=user.id, name="participant", hackathon_id=hackathon.id)
                db.add(role)
                
                # Assign to Team
                tm_role = "leader" if is_leader else "member"
                team_member = TeamMember(team_id=team.id, user_id=user.id, role=tm_role)
                db.add(team_member)
                db.commit()
                
                print(f"  Created User: {m_name} ({m_email}) as {tm_role} in {team.name}")
            is_leader = False

    db.close()
    print("Test data seeded successfully. All participant passwords are 'password123'.")
    print("Admin password is 'admin123'.")

if __name__ == "__main__":
    seed_test_data()
