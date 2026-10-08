import os
import time
import logging
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

IS_SQLITE = db_url.startswith("sqlite")

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# NullPool was opening a brand-new TCP+SSL connection (plus SQLAlchemy's
# hstore lookup) for EVERY request. Against the Supabase pooler that burns
# through the client limit under load and produces
# "SSL connection has been closed unexpectedly".
# A small real pool + pre-ping reuses connections and transparently replaces
# dead ones.
if IS_SQLITE:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    connect_args = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "connect_timeout": 10,
    }
    if "sslmode" not in db_url:
        connect_args["sslmode"] = "require"

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,      # test connection before use, replace if dead
        pool_recycle=240,        # recycle before Supabase/pooler idles it out
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
        pool_timeout=15,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Set to True once init_db() has completed successfully.
DB_READY = False


def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy session.
    Checks out a (pre-pinged) connection up front and retries briefly on
    transient errors, then yields the session.
    """
    from fastapi import HTTPException

    MAX_RETRIES = 3
    db = None
    last_err = None

    for attempt in range(MAX_RETRIES):
        try:
            db = SessionLocal()
            db.connection()  # checks out a pooled connection (pre-ping applies)
            break
        except Exception as e:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass
                db = None
            last_err = e
            err_str = str(e).lower()
            is_transient = (
                "ssl" in err_str
                or "connection" in err_str
                or "timeout" in err_str
                or "could not connect" in err_str
                or "too many clients" in err_str
                or "remaining connection slots" in err_str
                or "max clients" in err_str
            )
            if is_transient and attempt < MAX_RETRIES - 1:
                wait = 0.3 * (2 ** attempt)
                logger.warning(
                    f"[DB] Transient connection error (attempt {attempt+1}/{MAX_RETRIES}), "
                    f"retrying in {wait:.1f}s: {e}"
                )
                time.sleep(wait)
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable. Please retry.",
                ) from e

    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please retry.",
        ) from last_err

    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


def check_db() -> bool:
    """Lightweight DB probe for a /health/db endpoint."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"[DB] check_db failed: {e}")
        return False


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

        # Load all existing codes in ONE query instead of one query per item
        existing_codes = {row[0] for row in db.query(PromptBankItem.code).all()}

        for p_data in ARENA_PROMPT_BANK:
            if p_data["code"] not in existing_codes:
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

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _import_models():
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


def _migrate_columns():
    """Safe SQLite and PostgreSQL column migration for existing databases.
    All statements are idempotent, so retrying the whole thing is safe."""
    with engine.connect() as conn:
        if not IS_SQLITE:
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

            # Encapsulated Arena context
            conn.execute(text("ALTER TABLE team_arena_sessions ADD COLUMN IF NOT EXISTS arena_id VARCHAR NOT NULL DEFAULT 'default-arena-config';"))
            conn.execute(text("ALTER TABLE arena_submissions ADD COLUMN IF NOT EXISTS arena_id VARCHAR NOT NULL DEFAULT 'default-arena-config';"))
            conn.execute(text("ALTER TABLE arena_security_events ADD COLUMN IF NOT EXISTS arena_id VARCHAR NOT NULL DEFAULT 'default-arena-config';"))
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

            tas_res = conn.execute(text("PRAGMA table_info(team_arena_sessions);"))
            tas_cols = [row[1] for row in tas_res.fetchall()]
            if tas_cols and "arena_id" not in tas_cols:
                conn.execute(text("ALTER TABLE team_arena_sessions ADD COLUMN arena_id VARCHAR NOT NULL DEFAULT 'default-arena-config';"))

            sub_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(arena_submissions);")).fetchall()]
            if sub_cols and "arena_id" not in sub_cols:
                conn.execute(text("ALTER TABLE arena_submissions ADD COLUMN arena_id VARCHAR NOT NULL DEFAULT 'default-arena-config';"))

            sec_res = conn.execute(text("PRAGMA table_info(arena_security_events);"))
            sec_cols = [row[1] for row in sec_res.fetchall()]
            if sec_cols and "arena_id" not in sec_cols:
                conn.execute(text("ALTER TABLE arena_security_events ADD COLUMN arena_id VARCHAR NOT NULL DEFAULT 'default-arena-config';"))

            conn.commit()


def init_db():
    """Create tables, run column migrations, seed data. Raises on failure."""
    global DB_READY
    _import_models()
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    seed_initial_data()
    DB_READY = True


def _init_db_with_retry(max_attempts: int = 12):
    for attempt in range(1, max_attempts + 1):
        try:
            init_db()
            logger.info("[DB Init] Completed successfully.")
            print("[DB Init] Completed successfully.", flush=True)
            return
        except Exception as e:
            wait = min(3 * attempt, 30)
            msg = f"[DB Init] attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait}s"
            logger.warning(msg)
            print(msg, flush=True)
            time.sleep(wait)
    print("[DB Init] Gave up after all retries. App stays up; DB endpoints will return 503.", flush=True)


def init_db_async():
    """Run init_db in the background so the web server binds its port
    immediately, even if the database is unreachable at boot."""
    t = threading.Thread(target=_init_db_with_retry, name="db-init", daemon=True)
    t.start()
    return t


# Initialise in the background on module import. The port now opens right
# away instead of the whole process dying if the DB is down at boot.
init_db_async()