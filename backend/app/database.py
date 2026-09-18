from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Configure SQLite or PostgreSQL connect args
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_initial_data():
    from app.models.user import User, Role
    from app.models.hackathon import Hackathon, Round
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        # 1. Seed 3 Admin Accounts (Strictly isolated admin accounts)
        admin_accounts = [
            (settings.ADMIN1_NAME, settings.ADMIN1_EMAIL, settings.ADMIN1_PASSWORD),
            (settings.ADMIN2_NAME, settings.ADMIN2_EMAIL, settings.ADMIN2_PASSWORD),
            (settings.ADMIN3_NAME, settings.ADMIN3_EMAIL, settings.ADMIN3_PASSWORD),
        ]
        for name, email, raw_pwd in admin_accounts:
            existing = db.query(User).filter(User.email == email.lower()).first()
            if not existing:
                u = User(
                    name=name,
                    email=email.lower(),
                    password_hash=hash_password(raw_pwd),
                    affiliation="NEURA Directorate",
                    status="active"
                )
                db.add(u)
                db.flush()
                db.add(Role(user_id=u.id, name="admin"))

        # 2. Seed Judge Account
        judge_existing = db.query(User).filter(User.email == settings.JUDGE1_EMAIL.lower()).first()
        if not judge_existing:
            j = User(
                name=settings.JUDGE1_NAME,
                email=settings.JUDGE1_EMAIL.lower(),
                password_hash=hash_password(settings.JUDGE1_PASSWORD),
                affiliation="NEURA Evaluation Committee",
                status="active"
            )
            db.add(j)
            db.flush()
            db.add(Role(user_id=j.id, name="judge"))

        # 3. Seed Default Hackathon & Round 1 if none exist
        default_hk = db.query(Hackathon).filter(Hackathon.id == "hk-2026").first()
        if not default_hk:
            hk = Hackathon(
                id="hk-2026",
                title="NEURA Prompt Engineering Hackathon 2026",
                description="Live Two-Round Prompt Engineering Tournament",
                status="active",
                registration_open=True,
                min_team_size=1,
                max_team_size=4
            )
            db.add(hk)
            db.flush()

            r1 = Round(
                id="rnd-r1",
                hackathon_id=hk.id,
                type="round1_fix_the_prompt",
                order_index=1,
                duration_seconds=180,
                status="published"
            )
            db.add(r1)

        # 4. Seed Prompt Fixing Arena Prompt Bank & Config
        from app.models.arena import PromptBankItem, ArenaConfig
        from app.core.arena_seed_data import ARENA_PROMPT_BANK

        existing_config = db.query(ArenaConfig).filter(ArenaConfig.id == "default-arena-config").first()
        if not existing_config:
            arena_conf = ArenaConfig(
                id="default-arena-config",
                hackathon_id="hk-2026",
                status="waiting",
                challenges_count=5,
                marks_per_challenge=10,
                desktop_required=True,
                fullscreen_required=False,
                copy_paste_allowed=False,
                tab_switch_monitoring=True,
                max_allowed_violations=3
            )
            db.add(arena_conf)

        for p_data in ARENA_PROMPT_BANK:
            existing_p = db.query(PromptBankItem).filter(PromptBankItem.code == p_data["code"]).first()
            if not existing_p:
                item = PromptBankItem(
                    code=p_data["code"],
                    category=p_data["category"],
                    title=p_data["title"],
                    difficulty=p_data["difficulty"],
                    original_bad_prompt=p_data["original_bad_prompt"],
                    bad_output_evidence=p_data["bad_output_evidence"],
                    flawed_reasons=p_data["flawed_reasons"],
                    expected_improvements=p_data["expected_improvements"]
                )
                db.add(item)

        # 5. Seed Test Participant Teams & Registrations for Live Testing
        from app.models.registration import Registration
        from app.models.team import Team, TeamMember

        test_teams = [
            {
                "team_name": "Neural Mavericks",
                "college": "MMCOE Pune",
                "invite_code": "NR-4827",
                "members": [
                    {"name": "Alex Mercer", "email": "alex.mercer@neura.io", "role": "leader"},
                    {"name": "Elena Rostova", "email": "elena.rostova@neura.io", "role": "member"}
                ]
            },
            {
                "team_name": "Code Warriors",
                "college": "COEP Pune",
                "invite_code": "CW-1029",
                "members": [
                    {"name": "David Kim", "email": "david.kim@neura.io", "role": "leader"},
                    {"name": "Sarah Lee", "email": "sarah.lee@neura.io", "role": "member"}
                ]
            },
            {
                "team_name": "Byte Force",
                "college": "PICT Pune",
                "invite_code": "BF-3049",
                "members": [
                    {"name": "Priya Nair", "email": "priya.nair@neura.io", "role": "leader"},
                    {"name": "Jonah Hill", "email": "jonah.hill@neura.io", "role": "member"}
                ]
            }
        ]

        # Seed legacy alex@neuralninjas.io login account
        legacy_alex = db.query(User).filter(User.email == "alex@neuralninjas.io").first()
        if not legacy_alex:
            legacy_u = User(
                name="Alex Mercer",
                email="alex@neuralninjas.io",
                password_hash=hash_password("Pass123!"),
                affiliation="MMCOE Pune",
                status="active"
            )
            db.add(legacy_u)
            db.flush()
            db.add(Role(user_id=legacy_u.id, name="participant"))
            db.add(Role(user_id=legacy_u.id, name="team_leader"))

        for t_info in test_teams:
            existing_t = db.query(Team).filter(Team.hackathon_id == "hk-2026", Team.name == t_info["team_name"]).first()
            if not existing_t:
                team = Team(
                    hackathon_id="hk-2026",
                    name=t_info["team_name"],
                    college=t_info["college"],
                    invite_code=t_info["invite_code"],
                    status="forming"
                )
                db.add(team)
                db.flush()
            else:
                team = existing_t

            for m_idx, m_info in enumerate(t_info["members"], start=1):
                m_email = m_info["email"].lower()
                u = db.query(User).filter(User.email == m_email).first()
                if not u:
                    u = User(
                        name=m_info["name"],
                        email=m_email,
                        password_hash=hash_password("Pass123!"),
                        affiliation=t_info["college"],
                        status="active"
                    )
                    db.add(u)
                    db.flush()
                    db.add(Role(user_id=u.id, name="participant"))
                    if m_info["role"] == "leader":
                        db.add(Role(user_id=u.id, name="team_leader"))

                tm = db.query(TeamMember).filter(TeamMember.user_id == u.id).first()
                if not tm:
                    db.add(TeamMember(team_id=team.id, user_id=u.id, role=m_info["role"]))

                reg = db.query(Registration).filter(Registration.email == m_email).first()
                if not reg:
                    db.add(Registration(
                        external_registration_id=f"REG-SEED-{team.invite_code}-M{m_idx}",
                        team_name=t_info["team_name"],
                        participant_name=m_info["name"],
                        email=m_email,
                        college=t_info["college"],
                        member_number=m_idx,
                        registration_status="VERIFIED",
                        verification_status="VERIFIED",
                        account_status="ACTIVE",
                        password_hash=u.password_hash,
                        password_set=True,
                        user_id=u.id,
                        team_id=team.id,
                        source="seed",
                        is_active=True
                    ))

        # 6. Seed Pending & Rejected Registrations for Admin Workflow Testing
        pending_records = [
            ("Kaelen Vance", "kaelen.vance@example.com", "Cyber Dynamics", "MMCOE Pune", 1, "PENDING", "NOT_PROVISIONED"),
            ("Marcus Vance", "marcus.vance@example.com", "Cyber Dynamics", "MMCOE Pune", 2, "PENDING", "NOT_PROVISIONED"),
            ("Sora Takahashi", "sora.takahashi@example.com", "Shadow Protocol", "WCE Sangli", 1, "REJECTED", "DISABLED")
        ]

        for p_name, p_email, p_team, p_coll, p_mno, p_rstatus, p_astatus in pending_records:
            reg = db.query(Registration).filter(Registration.email == p_email.lower()).first()
            if not reg:
                db.add(Registration(
                    external_registration_id=f"REG-FORM-{p_email.split('@')[0]}",
                    team_name=p_team,
                    participant_name=p_name,
                    email=p_email.lower(),
                    college=p_coll,
                    member_number=p_mno,
                    registration_status=p_rstatus,
                    verification_status=p_rstatus,
                    account_status=p_astatus,
                    source="google_sheets",
                    is_active=(p_astatus != "DISABLED")
                ))

        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def init_db():
    import app.models.user
    import app.models.team
    import app.models.hackathon
    import app.models.audit
    import app.models.challenge
    import app.models.execution
    import app.models.evaluation
    import app.models.score
    import app.models.leaderboard
    import app.models.arena
    import app.models.registration
    Base.metadata.create_all(bind=engine)

    # Safe SQLite column migration for existing databases
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(teams);"))
            cols = [row[1] for row in result.fetchall()]
            if cols and "college" not in cols:
                conn.execute(text("ALTER TABLE teams ADD COLUMN college VARCHAR;"))
                conn.commit()

            eval_res = conn.execute(text("PRAGMA table_info(arena_evaluations);"))
            eval_cols = [row[1] for row in eval_res.fetchall()]
            if eval_cols:
                if "output_format_score" not in eval_cols:
                    conn.execute(text("ALTER TABLE arena_evaluations ADD COLUMN output_format_score FLOAT DEFAULT 0.0;"))
                if "constraints_score" not in eval_cols:
                    conn.execute(text("ALTER TABLE arena_evaluations ADD COLUMN constraints_score FLOAT DEFAULT 0.0;"))
                conn.commit()
    except Exception:
        pass
    seed_initial_data()

# Auto-initialize tables on module import
init_db()
