import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

from sqlalchemy.pool import NullPool

# Configure SQLite or PostgreSQL connect args
# For PostgreSQL, we add TCP keepalive settings to prevent Supabase from
# abruptly dropping SSL connections under high concurrent load.
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {
        "keepalives": 1,
        "keepalives_idle": 10,
        "keepalives_interval": 5,
        "keepalives_count": 3,
        "connect_timeout": 10,
    }

engine_kwargs = {"connect_args": connect_args, "echo": False}
if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "poolclass": NullPool
    })

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy session with automatic retry
    on transient SSL/connection errors from Supabase under high concurrent load.
    """
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        db = SessionLocal()
        try:
            yield db
            return  # Success — exit the retry loop
        except Exception as e:
            db.close()
            err_str = str(e).lower()
            is_transient = (
                "ssl connection has been closed" in err_str
                or "connection refused" in err_str
                or "could not connect" in err_str
                or "connection reset by peer" in err_str
                or "emaxconnsession" in err_str
            )
            if is_transient and attempt < MAX_RETRIES - 1:
                wait = 0.3 * (2 ** attempt)  # 0.3s, 0.6s, 1.2s
                logger.warning(f"[DB] Transient connection error (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait:.1f}s: {e}")
                time.sleep(wait)
                continue
            raise  # Non-transient or final attempt — propagate the error
        finally:
            try:
                db.close()
            except Exception:
                pass

def seed_initial_data():
    from app.models.user import User, Role
    from app.models.hackathon import Hackathon, Round
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        # 1. Seed 1 Admin Account (Strictly isolated admin account)
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

        def _fix_str(val):
            if isinstance(val, str):
                return val.encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore').encode('utf-8', 'ignore').decode('utf-8')
            elif isinstance(val, list):
                return [_fix_str(x) for x in val]
            elif isinstance(val, dict):
                return {_fix_str(k): _fix_str(v) for k, v in val.items()}
            return val

        for p_data in ARENA_PROMPT_BANK:
            existing_p = db.query(PromptBankItem).filter(PromptBankItem.code == p_data["code"]).first()
            if not existing_p:
                item = PromptBankItem(
                    code=_fix_str(p_data["code"]),
                    category=_fix_str(p_data["category"]),
                    title=_fix_str(p_data["title"]),
                    difficulty=_fix_str(p_data["difficulty"]),
                    original_bad_prompt=_fix_str(p_data["original_bad_prompt"]),
                    bad_output_evidence=_fix_str(p_data["bad_output_evidence"]),
                    flawed_reasons=_fix_str(p_data["flawed_reasons"]),
                    expected_improvements=_fix_str(p_data["expected_improvements"])
                )
                db.add(item)

        # (Removed test teams, legacy accounts, and pending registrations as per user request)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
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
    import app.models.arena_scoring
    import app.models.registration
    Base.metadata.create_all(bind=engine)

    # Safe SQLite and PostgreSQL column migration for existing databases
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            db_url = settings.DATABASE_URL.lower()
            is_postgres = db_url.startswith("postgresql") or "postgres" in db_url

            if is_postgres:
                conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS college VARCHAR;"))
                conn.execute(text("ALTER TABLE arena_submissions ADD COLUMN IF NOT EXISTS diagnosis_notes VARCHAR;"))
                conn.execute(text("ALTER TABLE arena_evaluations ADD COLUMN IF NOT EXISTS output_format_score FLOAT DEFAULT 0.0;"))
                conn.execute(text("ALTER TABLE arena_evaluations ADD COLUMN IF NOT EXISTS constraints_score FLOAT DEFAULT 0.0;"))
                # Dynamic dataset tags (added 2026-10-06)
                conn.execute(text("ALTER TABLE prompt_bank_items ADD COLUMN IF NOT EXISTS dataset_tag VARCHAR NOT NULL DEFAULT 'default';"))
                conn.execute(text("ALTER TABLE arena_config ADD COLUMN IF NOT EXISTS active_dataset_tag VARCHAR NOT NULL DEFAULT 'default';"))
                conn.execute(text("ALTER TABLE prompt_bank_items ADD COLUMN IF NOT EXISTS expected_good_prompt VARCHAR;"))
                conn.execute(text("ALTER TABLE arena_config ADD COLUMN IF NOT EXISTS title VARCHAR NOT NULL DEFAULT 'Main Arena';"))
                conn.execute(text("ALTER TABLE arena_config ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;"))
                conn.commit()
            else:
                result = conn.execute(text("PRAGMA table_info(teams);"))
                cols = [row[1] for row in result.fetchall()]
                if cols and "college" not in cols:
                    conn.execute(text("ALTER TABLE teams ADD COLUMN college VARCHAR;"))

                sub_res = conn.execute(text("PRAGMA table_info(arena_submissions);"))
                sub_cols = [row[1] for row in sub_res.fetchall()]
                if sub_cols and "diagnosis_notes" not in sub_cols:
                    conn.execute(text("ALTER TABLE arena_submissions ADD COLUMN diagnosis_notes VARCHAR;"))

                eval_res = conn.execute(text("PRAGMA table_info(arena_evaluations);"))
                eval_cols = [row[1] for row in eval_res.fetchall()]
                if eval_cols:
                    if "output_format_score" not in eval_cols:
                        conn.execute(text("ALTER TABLE arena_evaluations ADD COLUMN output_format_score FLOAT DEFAULT 0.0;"))
                    if "constraints_score" not in eval_cols:
                        conn.execute(text("ALTER TABLE arena_evaluations ADD COLUMN constraints_score FLOAT DEFAULT 0.0;"))
                        
                pb_res = conn.execute(text("PRAGMA table_info(prompt_bank_items);"))
                pb_cols = [row[1] for row in pb_res.fetchall()]
                if pb_cols:
                    if "dataset_tag" not in pb_cols:
                        conn.execute(text("ALTER TABLE prompt_bank_items ADD COLUMN dataset_tag VARCHAR NOT NULL DEFAULT 'default';"))
                    if "expected_good_prompt" not in pb_cols:
                        conn.execute(text("ALTER TABLE prompt_bank_items ADD COLUMN expected_good_prompt VARCHAR;"))
                        
                conf_res = conn.execute(text("PRAGMA table_info(arena_config);"))
                conf_cols = [row[1] for row in conf_res.fetchall()]
                if conf_cols:
                    if "active_dataset_tag" not in conf_cols:
                        conn.execute(text("ALTER TABLE arena_config ADD COLUMN active_dataset_tag VARCHAR NOT NULL DEFAULT 'default';"))
                    if "title" not in conf_cols:
                        conn.execute(text("ALTER TABLE arena_config ADD COLUMN title VARCHAR NOT NULL DEFAULT 'Main Arena';"))
                    if "is_active" not in conf_cols:
                        conn.execute(text("ALTER TABLE arena_config ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;"))

                conn.commit()
    except Exception as e:
        print(f"[DB Migration Notice]: {e}")
    seed_initial_data()

# Auto-initialize tables on module import
init_db()
