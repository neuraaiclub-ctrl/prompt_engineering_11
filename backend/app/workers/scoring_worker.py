import time
import signal
import uuid
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.arena import PromptBankItem, ArenaSubmission
from app.models.arena_scoring import (
    ArenaScoringJob, ArenaScoringRun, ArenaFinalScore,
    ArenaDimensionScore, ArenaTestResult,
    ArenaChallengeSpec, ArenaIntegrityFlag
)
from app.scoring.harness import ScoringHarness
from app.scoring.judges import LLMJudgePanel
from app.scoring.aggregate import aggregate_scores
from app.scoring.integrity import IntegrityScanner
from app.scoring.providers.adapter import MockScoringProvider
from app.scoring.providers.groq_adapter import GroqProviderAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_should_exit = False

def handle_sigint(sig, frame):
    global _should_exit
    logger.info("Signal received. Initiating graceful shutdown...")
    _should_exit = True

def process_scoring_jobs():
    logger.info("Scoring worker started.")
    provider_key = os.environ.get("LLM_P1_A_KEY")
    if provider_key and os.environ.get("USE_MOCK_PROVIDER", "1") != "1":
        provider = GroqProviderAdapter(provider_key)
    else:
        provider = MockScoringProvider()
        
    harness = ScoringHarness(provider)
    judges = LLMJudgePanel(provider)
    scanner = IntegrityScanner()
    
    while not _should_exit:
        db = SessionLocal()
        try:
            job = db.query(ArenaScoringJob).filter(
                ArenaScoringJob.status == "queued"
            ).first()
            
            if not job:
                db.close()
                time.sleep(2)
                continue
                
            job.status = "locked"
            job.lock_token = str(uuid.uuid4())
            job.lease_expires_at = datetime.utcnow() + timedelta(minutes=5)
            db.commit()
            
            logger.info(f"Processing job {job.id} for submission {job.submission_id}")
            
            sub = db.query(ArenaSubmission).filter(ArenaSubmission.id == job.submission_id).first()
            if not sub:
                raise Exception("Submission not found")
                
            spec_rec = db.query(ArenaChallengeSpec).filter(ArenaChallengeSpec.prompt_bank_item_id == sub.prompt_bank_item_id).first()
            if not spec_rec:
                # If no spec, we mock one for testing gracefully
                spec = {"test_cases": []}
            else:
                spec = spec_rec.spec
                
            prompt_item = db.query(PromptBankItem).filter(PromptBankItem.id == sub.prompt_bank_item_id).first()
            bad_prompt = prompt_item.original_bad_prompt if prompt_item else ""
            
            # Phase 5: Integrity
            flags = scanner.scan_submission(db, sub.submitted_prompt, bad_prompt)
            for f in flags:
                db.add(ArenaIntegrityFlag(
                    submission_id=sub.id,
                    kind=f["flag_type"],
                    severity=f["severity"],
                    detail={"description": f.get("description")}
                ))
            db.commit()
            
            # Create Run
            run = ArenaScoringRun(
                submission_id=sub.id,
                job_id=job.id,
                engine_version="v2.0",
                spec_version=spec_rec.spec_version if spec_rec else 1,
                rubric_version=1,
                models_used=[provider.__class__.__name__]
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            
            try:
                # Harness (B)
                l2_result = harness.evaluate_submission_l2(sub.submitted_prompt, spec)
                b_scores = l2_result["dimension_scores"]
                
                total_tokens_in = 0
                total_tokens_out = 0
                total_cost = 0.0
                
                # Save test results
                for idx, t_res in enumerate(l2_result.get("test_results", [])):
                    res_data = t_res["result"]
                    total_tokens_in += res_data.get("tokens_in", 0)
                    total_tokens_out += res_data.get("tokens_out", 0)
                    total_cost += res_data.get("cost_usd", 0.0)
                    db.add(ArenaTestResult(
                        run_id=run.id,
                        case_id=t_res["test_case_id"],
                        sample_idx=0,
                        output_text=res_data.get("output", ""),
                        checks=res_data.get("check_results", []),
                        passed=res_data.get("passed", False),
                        tokens=res_data.get("tokens_in", 0) + res_data.get("tokens_out", 0)
                    ))
                
                # Judges (R)
                if job.degradation_level in ["L0", "L1"]:
                    r_result = judges.evaluate_rubric(sub.submitted_prompt, spec, k=1) # k=1 for MVC speed
                    r_scores = r_result.get("rubric_scores", b_scores) # fallback
                else:
                    r_scores = b_scores
                    
                # Aggregate
                final_scores = aggregate_scores(b_scores, r_scores)
                confidence = l2_result.get("confidence", 0.8)
                
                total = sum(final_scores.values())
                
                # Save Dimensions
                dimensions = ["clarity", "specificity", "context", "output_format", "constraints"]
                for dim in dimensions:
                    db.add(ArenaDimensionScore(
                        run_id=run.id,
                        dimension=dim,
                        behavioral_score=b_scores.get(dim, 0.0),
                        rubric_score=r_scores.get(dim, 0.0),
                        final_score=final_scores.get(dim, 0.0),
                        confidence=confidence,
                        evidence={"b": "Harness data", "r": "Judge data"}
                    ))
                
                # Create Final Score
                final = ArenaFinalScore(
                    submission_id=sub.id,
                    clarity_score=final_scores["clarity"],
                    specificity_score=final_scores["specificity"],
                    context_score=final_scores["context"],
                    output_format_score=final_scores["output_format"],
                    constraints_score=final_scores["constraints"],
                    total=total,
                    source="engine",
                    scoring_run_id=run.id
                )
                db.add(final)
                
                # Update run
                run.status = "succeeded"
                run.tokens_in = total_tokens_in
                run.tokens_out = total_tokens_out
                run.cost_usd = total_cost
                run.completed_at = datetime.utcnow()
                job.status = "succeeded"
                
                db.commit()
                logger.info(f"Job {job.id} completed. Total score: {total}")
                
            except Exception as e:
                logger.error(f"Error executing scoring for job {job.id}: {e}")
                run.status = "failed"
                run.error = str(e)
                run.completed_at = datetime.utcnow()
                
                job.attempts += 1
                if job.attempts >= 3:
                    job.status = "dead_lettered"
                else:
                    job.status = "queued"
                job.last_error = str(e)
                db.commit()
                
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(2)
        finally:
            db.close()
            
    logger.info("Worker cleanly exited.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)
    process_scoring_jobs()
