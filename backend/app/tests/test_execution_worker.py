import pytest
from app.database import SessionLocal
from app.models.execution import Execution
from app.workers.execution_worker import process_pending_executions, process_single_execution

def test_execution_worker_processes_queued_item():
    db = SessionLocal()
    # Create a queued execution
    item = Execution(
        model="gpt-4o-mini",
        status="queued"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item_id = item.id

    try:
        count = process_pending_executions(db, batch_size=5)
        assert count >= 1

        db.refresh(item)
        assert item.status == "success"
        assert item.output_text is not None
        assert item.latency_ms >= 0
    finally:
        # Cleanup
        db.query(Execution).filter(Execution.id == item_id).delete()
        db.commit()
        db.close()
