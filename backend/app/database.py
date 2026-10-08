import os
import time
import logging
import threading
from fastapi import HTTPException
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SAPoolTimeoutError
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

IS_SQLITE = db_url.startswith("sqlite")
# Supabase pooler (Supavisor) transaction mode listens on :6543
IS_PGBOUNCER = ":6543" in db_url or os.getenv("USE_PGBOUNCER", "0") == "1"

# ---------------------------------------------------------------------------
# Engine - ALWAYS a small, hard-capped pool.
# Max connections this instance can ever hold = POOL_SIZE + MAX_OVERFLOW.
# (Never NullPool: it has no ceiling and caused EMAXCONN on the pooler.)
# ---------------------------------------------------------------------------
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "5"))

if IS_SQLITE:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    connect_args = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
    if "sslmode" not in db_url:
        connect_args["sslmode"] = "require"

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_pre_ping=True,
        pool_recycle=240,
    )
    print(
        f"[DB] Pooled engine: pool_size={POOL_SIZE} max_overflow={MAX_OVERFLOW} "
        f"timeout={POOL_TIMEOUT}s pooler={IS_PGBOUNCER} (max {POOL_SIZE + MAX_OVERFLOW} conns)",
        flush=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Set to True once init_db() has completed successfully.
DB_READY = False

# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
# * It is driven by real connection-level errors (SQLAlchemy "handle_error"
#   event), not by string-matching endpoint exceptions.
# * It is enforced when a connection is CHECKED OUT (pool "checkout" event),
#   not when a request starts. So endpoints that are served from a cache and
#   never touch the DB keep working while the breaker is open.
# * A good checkout (pre-ping already passed) closes the breaker again.
BREAKER_THRESHOLD = int(os.getenv("DB_BREAKER_THRESHOLD", "5"))
BREAKER_COOLDOWN = float(os.getenv("DB_BREAKER_COOLDOWN", "10"))

_breaker_lock = threading.Lock()
_breaker = {"failures": 0, "open_until": 0.0}


def _breaker_allow():
    """Returns (allowed, retry_after_seconds)."""
    now = time.monotonic()
    with _breaker_lock:
        if now < _breaker["open_until"]:
            return False, int(_breaker["open_until"] - now) + 1
        return True, 0


def _breaker_success():
    with _breaker_lock:
        was_tripped = _breaker["failures"] >= BREAKER_THRESHOLD
        _breaker["failures"] = 0
        _breaker["open_until"] = 0.0
    if was_tripped:
        print("[DB] Circuit breaker CLOSED - database is reachable again.", flush=True)


def _breaker_failure():
    opened = False
    now = time.monotonic()
    with _breaker_lock:
        was_open = now < _breaker["open_until"]
        _breaker["failures"] += 1
        if _breaker["failures"] >= BREAKER_THRESHOLD:
            _breaker["open_until"] = now + BREAKER_COOLDOWN
            opened = not was_open
    if opened:
        print(
            f"[DB] Circuit breaker OPEN - no new DB connections for {BREAKER_COOLDOWN:.0f}s "
            f"after {BREAKER_THRESHOLD} connection failures.",
            flush=True,
        )
        try:
            engine.dispose()  # release our pooled client connections
        except Exception:
            pass


def db_breaker_status() -> dict:
    """For a health endpoint."""
    now = time.monotonic()
    with _breaker_lock:
        is_open = now < _breaker["open_until"]
        return {
            "state": "open" if is_open else "closed",
            "consecutive_failures": _breaker["failures"],
            "retry_in_seconds": max(0, int(_breaker["open_until"] - now)) if is_open else 0,
        }


def _raise_if_breaker_open():
    allowed, retry_after = _breaker_allow()
    if not allowed:
        # Not wrapped by SQLAlchemy; FastAPI turns it into a clean 503.
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please retry shortly.",
            headers={"Retry-After": str(retry_after)},
        )


@event.listens_for(engine, "do_connect")
def _on_do_connect(dialect, conn_rec, cargs, cparams):
    # Fires BEFORE a new DBAPI connection is opened. While the breaker is
    # open we make no connection attempts at all (this is what protects the
    # Supabase pooler when it is answering EMAXCONN / dropping SSL).
    _raise_if_breaker_open()


@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_connection, connection_record, connection_proxy):
    # Fires after pre-ping passed, for new AND reused connections.
    _raise_if_breaker_open()
    _breaker_success()


@event.listens_for(engine, "handle_error")
def _on_db_error(ctx):
    se = ctx.sqlalchemy_exception
    if ctx.is_disconnect or isinstance(se, (OperationalError, InterfaceError)):
        _breaker_failure()


def register_db_exception_handlers(app):
    """Call once in main.py right after `app = FastAPI(...)`.
    Turns DB connection/pool errors into a clean 503 + Retry-After
    instead of a 500 with a traceback."""
    from fastapi.responses import JSONResponse

    last_log = {"t": 0.0}

    async def _handler(request, exc):
        # Rate-limited diagnostics: which error caused this 503, and how busy
        # the pool is. (Pool timeouts are otherwise completely silent.)
        now = time.monotonic()
        if now - last_log["t"] > 2.0:
            last_log["t"] = now
            try:
                pool_info = engine.pool.status()
            except Exception:
                pool_info = "n/a"
            print(f"[DB] 503 from {type(exc).__name__}: {str(exc)[:160]} | {pool_info}", flush=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable. Please retry shortly."},
            headers={"Retry-After": "3"},
        )

    for exc_cls in (SAPoolTimeoutError, OperationalError, InterfaceError):
        app.add_exception_handler(exc_cls, _handler)


def get_db():
    """
    FastAPI dependency: a lazy session. No connection is taken until the
    endpoint actually runs a query, so cache hits cost nothing.
    """
    db = SessionLocal()
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


# NOTE: init_db_async() is called by main.py lifespan only.
# Do NOT call it here — a second call would spawn a duplicate init thread
# competing for connections during startup.