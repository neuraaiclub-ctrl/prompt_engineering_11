from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.arena_scoring import ArenaProviderUsage
from datetime import datetime
import uuid

class DatabaseRateLimiter:
    @staticmethod
    def acquire_quota(
        db: Session,
        lane_id: str,
        calls: int = 1,
        tokens: int = 0,
        rpm_limit: int = 20,
        tpm_limit: int = 100000
    ) -> bool:
        """
        Atomically increment the quota for the current minute if limits aren't exceeded.
        Returns True if acquired, False if limit exceeded.
        """
        # Truncate to the minute
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        window_start_str = window_start.strftime("%Y-%m-%d %H:%M:00.000000")

        # Upsert in SQLite logic (since we use SQLite for dev)
        # We need an atomic increment. 
        # First ensure row exists
        row = db.query(ArenaProviderUsage).filter(
            ArenaProviderUsage.lane_id == lane_id,
            ArenaProviderUsage.window_start == window_start
        ).first()

        if not row:
            # Create if it doesn't exist. There could be a race condition, so we ignore duplicates.
            try:
                new_usage = ArenaProviderUsage(
                    id=str(uuid.uuid4()),
                    lane_id=lane_id,
                    window_start=window_start,
                    count=0,
                    tokens=0
                )
                db.add(new_usage)
                db.commit()
            except Exception:
                db.rollback()
        
        # Now do atomic update check
        # UPDATE arena_provider_usage 
        # SET count = count + :calls, tokens = tokens + :tokens 
        # WHERE lane_id = :lane AND window_start = :window 
        # AND (count + :calls) <= :rpm AND (tokens + :tokens) <= :tpm
        
        update_stmt = text('''
            UPDATE arena_provider_usage
            SET count = count + :calls, tokens = tokens + :tokens
            WHERE lane_id = :lane_id 
              AND window_start = :window_start
              AND (count + :calls) <= :rpm_limit
              AND (tokens + :tokens) <= :tpm_limit
        ''')
        
        result = db.execute(update_stmt, {
            "calls": calls,
            "tokens": tokens,
            "lane_id": lane_id,
            "window_start": window_start_str,
            "rpm_limit": rpm_limit,
            "tpm_limit": tpm_limit
        })
        
        db.commit()
        return result.rowcount > 0
