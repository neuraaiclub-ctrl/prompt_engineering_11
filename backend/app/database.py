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
