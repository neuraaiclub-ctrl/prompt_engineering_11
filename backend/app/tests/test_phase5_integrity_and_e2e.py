import pytest
from app.database import SessionLocal, init_db, Base, engine
from app.models.arena_scoring import ArenaFinalScore, ArenaIntegrityFlag, ArenaScoringJob
from app.scoring.integrity import IntegrityScanner
from app.models.arena import ArenaSubmission, PromptBankItem
from app.models.team import Team
import uuid
import threading
import time

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield

def test_integrity_scanner():
    scanner = IntegrityScanner()
    bad_prompt = "You are an assistant. Help the user."
    sub_text_copy = "You are an assistant. Help the user."
    sub_text_diff = "Write a python script to parse JSON."
    
    # 100% match
    flags = scanner.scan_submission(None, sub_text_copy, bad_prompt)
    assert len(flags) == 1
    assert flags[0]["flag_type"] == "copy_of_bad_prompt"
    
    # 0% match
    flags2 = scanner.scan_submission(None, sub_text_diff, bad_prompt)
    assert len(flags2) == 0

def test_scoring_worker_e2e():
    """Verify the worker loop successfully consumes a job and outputs a final score."""
    from app.workers.scoring_worker import process_scoring_jobs, _should_exit
    import app.workers.scoring_worker as worker_module
    
    worker_module._should_exit = False
    db = SessionLocal()
    try:
        # Create dependencies
        team = Team(id=str(uuid.uuid4()), name="Test Team", invite_code="123", status="active", hackathon_id="1")
        item = PromptBankItem(id=str(uuid.uuid4()), code="P1", category="general", title="Test", difficulty="easy", original_bad_prompt="bad", bad_output_evidence="bad")
        db.add(team)
        db.add(item)
        db.commit()
        
        sub = ArenaSubmission(
            id=str(uuid.uuid4()),
            team_id=team.id,
            prompt_bank_item_id=item.id,
            challenge_index=1,
            submitted_prompt="Good prompt"
        )
        db.add(sub)
        
        job = ArenaScoringJob(
            id=str(uuid.uuid4()),
            submission_id=sub.id,
            profile_id="prof1",
            degradation_level="L1",
            status="queued"
        )
        db.add(job)
        db.commit()
        
        # Run worker in a thread
        t = threading.Thread(target=process_scoring_jobs)
        t.daemon = True
        t.start()
        
        # Wait for processing
        time.sleep(2)
        worker_module._should_exit = True
        t.join(timeout=2.0)
        
        # Check DB
        final_score = db.query(ArenaFinalScore).filter(ArenaFinalScore.submission_id == sub.id).first()
        assert final_score is not None
        # Since there are no test_cases in the spec, B=0.
        # MockProvider gives R=20.
        # R_eff = min(20, 0+5) = 5. Score = 0.4*5 = 2.0 per dimension. 5 * 2.0 = 10.0
        assert final_score.total == 10.0
        assert final_score.source == "engine"
        
        job_after = db.query(ArenaScoringJob).filter(ArenaScoringJob.id == job.id).first()
        assert job_after.status == "succeeded"
    finally:
        db.close()
