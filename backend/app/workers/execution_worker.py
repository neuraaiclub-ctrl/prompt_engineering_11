"""
Asynchronous Execution Worker (Queue Processing & Auto-Eval)
SRS Reference: Section 15 (Model Execution Adapter), Section 7 (Execution Engine), docker-compose.yml worker service
"""
import time
import signal
import sys
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.execution import Execution, PromptVersion
from app.models.challenge import TestCase
from app.core.ai_adapter import AIProviderAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [execution_worker] %(message)s"
)
logger = logging.getLogger("execution_worker")

_should_exit = False

def _signal_handler(signum, frame):
    global _should_exit
    logger.info(f"Shutdown signal received (signal {signum}). Terminating gracefully...")
    _should_exit = True

def process_single_execution(db: Session, execution: Execution) -> bool:
    """
    Process a single queued Execution record.
    Returns True if processed successfully, False otherwise.
    """
    try:
        execution.status = "running"
        db.commit()

        user_prompt = ""
        system_prompt = None

        if execution.prompt_version_id:
            pv = db.query(PromptVersion).filter(PromptVersion.id == execution.prompt_version_id).first()
            if pv:
                user_prompt = pv.prompt_text
                system_prompt = pv.system_prompt_text

        if execution.test_case_id:
            tc = db.query(TestCase).filter(TestCase.id == execution.test_case_id).first()
            if tc:
                user_prompt = f"{user_prompt}\n\nInput: {tc.input}".strip()

        if not user_prompt:
            user_prompt = "Default prompt execution"

        res = AIProviderAdapter.execute(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model=execution.model or "gpt-4o-mini"
        )

        execution.output_text = res.get("output_text")
        execution.token_count_prompt = res.get("token_count_prompt", 0)
        execution.token_count_output = res.get("token_count_output", 0)
        execution.latency_ms = res.get("latency_ms", 0)
        execution.status = res.get("status", "success")
        db.commit()

        logger.info(f"Execution {execution.id} processed: status={execution.status}, latency={execution.latency_ms}ms")
        return True

    except Exception as e:
        logger.error(f"Error processing execution {execution.id}: {e}", exc_info=True)
        execution.status = "error"
        db.commit()
        return False

def process_pending_executions(db: Session, batch_size: int = 10) -> int:
    """
    Find and process all queued executions up to batch_size.
    Returns the count of processed executions.
    """
    queued = db.query(Execution).filter(
        Execution.status == "queued"
    ).order_by(Execution.created_at.asc()).limit(batch_size).all()

    processed_count = 0
    for execution in queued:
        if _should_exit:
            break
        if process_single_execution(db, execution):
            processed_count += 1

    return processed_count

def run_worker_loop(poll_interval_seconds: float = 1.0):
    """
    Main background daemon loop for docker worker service.
    """
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("Execution worker daemon started. Waiting for queued tasks...")

    while not _should_exit:
        db = SessionLocal()
        try:
            processed = process_pending_executions(db)
            if processed > 0:
                logger.info(f"Processed {processed} queued execution(s)")
            else:
                time.sleep(poll_interval_seconds)
        except Exception as e:
            logger.error(f"Worker loop exception: {e}", exc_info=True)
            time.sleep(poll_interval_seconds)
        finally:
            db.close()

    logger.info("Execution worker daemon shut down cleanly.")

if __name__ == "__main__":
    run_worker_loop()
