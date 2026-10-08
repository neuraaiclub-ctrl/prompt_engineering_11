import hashlib
import json
import random
import threading
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.audit import AuditLog
from app.models.arena import (
    PromptBankItem,
    TeamArenaSession,
    ArenaSubmission,
    ArenaEvaluation,
    ArenaSecurityEvent,
    ArenaConfig
)
from app.schemas.arena import (
    StartArenaRequest,
    SubmitChallengeRequest,
    SecurityEventRequest,
    JudgeScoreRequest,
    EliminateTeamRequest,
    ArenaConfigUpdateRequest
)

# ---------------------------------------------------------------------------
# Groq Contextual Scoring — runs in a background thread after each submission
# ---------------------------------------------------------------------------
_GROQ_EVAL_PROMPT = """You are an expert prompt engineering judge. Your job is to evaluate whether a student correctly fixed a specific broken prompt.

## THE BROKEN PROMPT THE STUDENT HAD TO FIX
Challenge Title: {challenge_title}
Category: {category}

<broken_prompt>
{original_bad_prompt}
</broken_prompt>

## EXPERT REFERENCE FIX (for calibration only)
<reference_fix>
{expected_good_prompt}
</reference_fix>

## STUDENT'S SUBMITTED ANSWER
<student_submission>
{submitted_prompt}
</student_submission>

---

## STEP 1 — MANDATORY RELEVANCE GATE

First, decide: Is the student's submission a genuine attempt to fix THIS specific broken prompt about "{challenge_title}"?

AUTOMATIC ZERO (all 5 scores = 0) if ANY of the following are true:
- The submission is identical or nearly identical to the original broken prompt (the student must actually make changes)
- The submission is about a completely different topic or domain than the broken prompt
- The submission addresses a different task goal than what the broken prompt was trying to accomplish
- The submission appears to be a generic, pre-written, or copy-pasted prompt for a different use case
- Example: broken prompt is about computing expected value of a probability game → student submits a business earnings-call summarization prompt → AUTOMATIC ZERO

If ANY of the above are true, output EXACTLY this and stop:
{{"clarity_score": 0, "specificity_score": 0, "context_score": 0, "output_format_score": 0, "constraints_score": 0, "relevance_note": "FAIL relevance gate: <one-line reason why it is off-topic>"}}

## STEP 2 — RUBRIC SCORING (only if the submission passed the relevance gate)

Score each dimension 0, 10, or 20. Scores must be one of those three values only.

- clarity_score: Is the prompt's intent clear and unambiguous for this specific task?
- specificity_score: Does it add task-specific details that directly improve the broken prompt?
- context_score: Does it provide sufficient context so an AI can execute the task correctly?
- output_format_score: Does it define a clear, appropriate output format for this task?
- constraints_score: Does it add boundaries/rules/constraints suited to this specific task?

Scale: 0=missing or wrong, 10=partial, 20=strong and directly applicable.

Output valid JSON only, no markdown:
{{"clarity_score": <0|10|20>, "specificity_score": <0|10|20>, "context_score": <0|10|20>, "output_format_score": <0|10|20>, "constraints_score": <0|10|20>, "relevance_note": "<one sentence on relevance and scoring rationale>"}}"""

def _groq_eval_worker(submission_id: str, submitted_prompt: str, original_bad_prompt: str,
                       expected_good_prompt: str, challenge_title: str, category: str):
    """Background worker: calls Groq and updates ArenaFinalScore with contextual scores."""
    try:
        from app.config import settings
        from app.database import SessionLocal
        from app.models.arena_scoring import ArenaFinalScore
        import httpx, json as _json

        groq_key = (settings.GROQ_API_KEY or settings.LLM_P1_A_KEY 
                    or settings.LLM_P1_B_KEY or settings.LLM_P2_A_KEY 
                    or settings.LLM_P2_B_KEY or settings.TEST_RUN_KEY)
        if not groq_key or groq_key == "mock":
            return  # No key configured — keep heuristic score

        prompt_text = _GROQ_EVAL_PROMPT.format(
            challenge_title=challenge_title,
            category=category,
            original_bad_prompt=original_bad_prompt or "(not provided)",
            expected_good_prompt=expected_good_prompt or "(not provided)",
            submitted_prompt=submitted_prompt
        )

        payload = {
            "model": "llama3-70b-8192",  # 70b for more accurate relevance judgement
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.0,
            "max_tokens": 256,
            "response_format": {"type": "json_object"}
        }
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post("https://api.groq.com/openai/v1/chat/completions",
                               headers=headers, json=payload)
            resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
        
        # Clean markdown code blocks if Llama-3 adds them
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
            
        scores = _json.loads(content)

        # Validate scores are in allowed set {0, 10, 20}
        allowed = {0, 10, 20}
        clarity     = scores.get("clarity_score",      0) if scores.get("clarity_score",      0) in allowed else 0
        specificity = scores.get("specificity_score",  0) if scores.get("specificity_score",  0) in allowed else 0
        context     = scores.get("context_score",      0) if scores.get("context_score",      0) in allowed else 0
        output_fmt  = scores.get("output_format_score",0) if scores.get("output_format_score",0) in allowed else 0
        constraints = scores.get("constraints_score",  0) if scores.get("constraints_score",  0) in allowed else 0
        total       = clarity + specificity + context + output_fmt + constraints

        # Update the existing ArenaFinalScore row in a fresh session
        db = SessionLocal()
        try:
            row = db.query(ArenaFinalScore).filter(ArenaFinalScore.submission_id == submission_id).first()
            if row:
                row.clarity_score      = float(clarity)
                row.specificity_score  = float(specificity)
                row.context_score      = float(context)
                row.output_format_score = float(output_fmt)
                row.constraints_score  = float(constraints)
                row.total              = float(total)
                row.source             = "groq"
                db.commit()
        finally:
            db.close()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Groq evaluation failed for submission {submission_id}: {type(e).__name__} {str(e)}")
        pass   # Never crash submission because of background scoring failure


def _fire_groq_eval(submission_id: str, submitted_prompt: str, original_bad_prompt: str,
                     expected_good_prompt: str, challenge_title: str, category: str):
    """Spawn a daemon thread to run Groq eval without blocking the API response."""
    t = threading.Thread(
        target=_groq_eval_worker,
        args=(submission_id, submitted_prompt, original_bad_prompt,
              expected_good_prompt, challenge_title, category),
        daemon=True
    )
    t.start()


class ArenaService:

    @staticmethod
    def get_or_create_config(db: Session) -> ArenaConfig:
        conf = db.query(ArenaConfig).filter(ArenaConfig.id == "default-arena-config").first()
        if not conf:
            conf = ArenaConfig(
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
            db.add(conf)
            db.commit()
            db.refresh(conf)
        return conf

    @staticmethod
    def get_user_team(db: Session, user: User) -> Optional[Team]:
        membership = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
        if membership:
            return db.query(Team).filter(Team.id == membership.team_id).first()
        return db.query(Team).filter(func.lower(Team.name) == func.lower(user.name)).first()

    @classmethod
    def assign_unique_prompts_for_team(cls, db: Session, team: Team) -> List[str]:
        conf = cls.get_or_create_config(db)
        active_tag = conf.active_dataset_tag
        all_prompts = db.query(PromptBankItem).filter(PromptBankItem.dataset_tag == active_tag).order_by(PromptBankItem.code.asc()).all()
        if not all_prompts and active_tag == "default":
            from app.core.arena_seed_data import ARENA_PROMPT_BANK
            for p_data in ARENA_PROMPT_BANK:
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
            all_prompts = db.query(PromptBankItem).filter(PromptBankItem.dataset_tag == "default").order_by(PromptBankItem.code.asc()).all()

        if not all_prompts:
            raise HTTPException(status_code=500, detail="Prompt bank is empty. Seed initial prompt data.")
        
        total = len(all_prompts)
        if total < 5:
            return [p.id for p in all_prompts]

        existing_sessions = db.query(TeamArenaSession).all()
        assigned_sets = {
            tuple(s.prompt_ids)
            for s in existing_sessions
            if s.prompt_ids and s.team_id != team.id
        }

        easy_prompts = [p for p in all_prompts if p.difficulty.lower() == "easy"]
        medium_prompts = [p for p in all_prompts if p.difficulty.lower() == "medium"]
        hard_prompts = [p for p in all_prompts if p.difficulty.lower() == "hard"]

        seed_str = f"{team.id}_{team.name}_{team.invite_code}"
        salt_idx = 0
        while True:
            cur_seed_str = f"{seed_str}_{salt_idx}" if salt_idx > 0 else seed_str
            seed_val = int(hashlib.sha256(cur_seed_str.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed_val)
            
            if len(easy_prompts) >= 1 and len(medium_prompts) >= 3 and len(hard_prompts) >= 1:
                sampled = (
                    rng.sample(easy_prompts, 1) +
                    rng.sample(medium_prompts, 3) +
                    rng.sample(hard_prompts, 1)
                )
                rng.shuffle(sampled)
            else:
                sampled = rng.sample(all_prompts, 5)
                
            candidate = [p.id for p in sampled]
            if tuple(candidate) not in assigned_sets or salt_idx > 1000:
                return candidate
            salt_idx += 1

    @classmethod
    def update_config(cls, db: Session, current_user: User, payload: Any) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        if payload.desktop_required is not None: conf.desktop_required = payload.desktop_required
        if payload.fullscreen_required is not None: conf.fullscreen_required = payload.fullscreen_required
        if payload.copy_paste_allowed is not None: conf.copy_paste_allowed = payload.copy_paste_allowed
        if payload.tab_switch_monitoring is not None: conf.tab_switch_monitoring = payload.tab_switch_monitoring
        if payload.max_allowed_violations is not None: conf.max_allowed_violations = payload.max_allowed_violations
        if payload.active_dataset_tag is not None: conf.active_dataset_tag = payload.active_dataset_tag
        db.commit()
        db.refresh(conf)
        return {"success": True, "message": "Arena config updated successfully.", "config": {
            "active_dataset_tag": conf.active_dataset_tag
        }}

    @classmethod
    def get_status(cls, db: Session, current_user: Optional[User] = None) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        server_now = datetime.utcnow()

        ends_at_val = None
        if conf.status == "live" and conf.started_at:
            ends_at_val = (conf.started_at + timedelta(minutes=30)).isoformat() + "Z"
        elif conf.ended_at:
            ends_at_val = conf.ended_at.isoformat() + "Z"

        response: Dict[str, Any] = {
            "status": conf.status,
            "server_time": server_now.isoformat() + "Z",
            "started_at": conf.started_at.isoformat() + "Z" if conf.started_at else None,
            "ended_at": conf.ended_at.isoformat() + "Z" if conf.ended_at else None,
            "ends_at": ends_at_val,
            "results_released_at": conf.results_released_at.isoformat() + "Z" if conf.results_released_at else None,
            "config": {
                "challenges_count": conf.challenges_count,
                "marks_per_challenge": conf.marks_per_challenge,
                "desktop_required": conf.desktop_required,
                "fullscreen_required": conf.fullscreen_required,
                "copy_paste_allowed": conf.copy_paste_allowed,
                "tab_switch_monitoring": conf.tab_switch_monitoring,
                "max_allowed_violations": conf.max_allowed_violations
            }
        }

        if current_user:
            team = cls.get_user_team(db, current_user)
            if team:
                session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
                if session:
                    response["team_session"] = {
                        "team_id": team.id,
                        "team_name": team.name,
                        "current_challenge_index": session.current_challenge_index,
                        "total_challenges": conf.challenges_count,
                        "status": session.status,
                        "is_completed": session.current_challenge_index > conf.challenges_count,
                        "completed_at": session.completed_at.isoformat() if session.completed_at else None
                    }
                else:
                    response["team_session"] = {
                        "team_id": team.id,
                        "team_name": team.name,
                        "current_challenge_index": 1,
                        "total_challenges": conf.challenges_count,
                        "status": "active" if conf.status == "live" else "waiting",
                        "is_completed": False,
                        "completed_at": None
                    }

        return response

    @classmethod
    def start_competition(cls, db: Session, current_user: User, force: bool = False) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        
        if conf.status not in ["waiting", "completed", "results_available"] and not force:
            raise HTTPException(status_code=400, detail="Cannot start competition: Arena is in an invalid state.")

        # Clear old arena data so only teams and prompt questions remain
        from app.models.arena_scoring import (
            ArenaFinalScore, ArenaIntegrityFlag, ArenaScoringJob, 
            ArenaScoringRun, ArenaTestResult, ArenaDimensionScore
        )
        # --- ARCHIVE EXISTING DATA BEFORE DELETING ---
        import uuid
        from sqlalchemy import text
        arena_id = str(uuid.uuid4())
        
        # Archive Sessions
        db.execute(text(
            f"INSERT INTO archive_team_arena_sessions (archive_pk, arena_id, id, team_id, hackathon_id, prompt_ids, current_challenge_index, status, started_at, completed_at, created_at, updated_at) "
            f"SELECT id || '-' || '{arena_id}', '{arena_id}', id, team_id, hackathon_id, prompt_ids, current_challenge_index, status, started_at, completed_at, created_at, updated_at FROM team_arena_sessions"
        ))
        
        # Archive Submissions
        db.execute(text(
            f"INSERT INTO archive_arena_submissions (archive_pk, arena_id, id, team_id, prompt_bank_item_id, challenge_index, submitted_prompt, diagnosis_notes, server_timestamp, status) "
            f"SELECT id || '-' || '{arena_id}', '{arena_id}', id, team_id, prompt_bank_item_id, challenge_index, submitted_prompt, diagnosis_notes, server_timestamp, status FROM arena_submissions"
        ))
        
        # Archive Evaluations
        db.execute(text(
            f"INSERT INTO archive_arena_evaluations (archive_pk, arena_id, id, submission_id, judge_user_id, clarity_score, specificity_score, context_score, output_format_score, output_structure_score, constraints_score, relevance_score, total_score, judge_feedback, created_at) "
            f"SELECT id || '-' || '{arena_id}', '{arena_id}', id, submission_id, judge_user_id, clarity_score, specificity_score, context_score, output_format_score, output_structure_score, constraints_score, relevance_score, total_score, judge_feedback, created_at FROM arena_evaluations"
        ))
        
        # Delete original data
        db.query(ArenaTestResult).delete(synchronize_session=False)
        db.query(ArenaDimensionScore).delete(synchronize_session=False)
        db.query(ArenaScoringRun).delete(synchronize_session=False)
        db.query(ArenaScoringJob).delete(synchronize_session=False)
        db.query(ArenaIntegrityFlag).delete(synchronize_session=False)
        db.query(ArenaFinalScore).delete(synchronize_session=False)

        db.query(ArenaEvaluation).delete(synchronize_session=False)
        db.query(ArenaSubmission).delete(synchronize_session=False)
        db.query(ArenaSecurityEvent).delete(synchronize_session=False)
        db.query(TeamArenaSession).delete(synchronize_session=False)

        now = datetime.utcnow()
        conf.status = "live"
        conf.started_at = now
        
        audit = AuditLog(
            actor_user_id=current_user.id,
            action="arena.competition_started",
            target_type="ArenaConfig",
            target_id=conf.id,
            audit_metadata={"started_by": current_user.email, "timestamp": now.isoformat()}
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "message": "Competition officially started.",
            "status": "live",
            "started_at": now.isoformat()
        }

    @classmethod
    def end_competition(cls, db: Session, current_user: User) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        now = datetime.utcnow()
        conf.status = "completed"
        conf.ended_at = now

        # Auto-submit missing challenges with 0 marks for all active teams
        sessions = db.query(TeamArenaSession).filter(
            TeamArenaSession.status.in_(["active", "waiting"])
        ).all()
        
        for session in sessions:
            team = session.team
            if not team or team.status == "eliminated":
                continue
            
            prompt_ids = cls.parse_prompt_ids(session.prompt_ids)
            # Ensure prompt_ids has enough challenges
            if not prompt_ids or len(prompt_ids) < conf.challenges_count:
                prompt_ids = cls.assign_unique_prompts_for_team(db, team)
                session.prompt_ids = prompt_ids
            
            # Fill in submissions for every missing index
            for idx in range(session.current_challenge_index, conf.challenges_count + 1):
                prompt_id = prompt_ids[idx - 1] if idx <= len(prompt_ids) else None
                if not prompt_id:
                    prompt_item = db.query(PromptBankItem).filter(PromptBankItem.code == f"P00{idx}").first() or db.query(PromptBankItem).first()
                    prompt_id = prompt_item.id if prompt_item else "fallback-id"
                
                # Create the blank submission
                sub_id = str(uuid.uuid4())
                sub = ArenaSubmission(
                    id=sub_id,
                    team_id=team.id,
                    prompt_bank_item_id=prompt_id,
                    challenge_index=idx,
                    submitted_prompt="[NO SUBMISSION - TIME EXPIRED]",
                    diagnosis_notes="Team failed to submit an answer before the arena ended.",
                    server_timestamp=now,
                    status="locked"
                )
                db.add(sub)

                # Assign automatic 0 marks
                from app.models.arena_scoring import ArenaFinalScore
                final_eval = ArenaFinalScore(
                    id=str(uuid.uuid4()),
                    submission_id=sub.id,
                    clarity_score=0.0,
                    specificity_score=0.0,
                    context_score=0.0,
                    output_format_score=0.0,
                    constraints_score=0.0,
                    total=0.0,
                    source="engine"
                )
                db.add(final_eval)
            
            # Mark session as completed
            session.current_challenge_index = conf.challenges_count + 1
            session.status = "completed"
            session.completed_at = now
            team.status = "completed"

        audit = AuditLog(
            actor_user_id=current_user.id,
            action="arena.competition_ended",
            target_type="ArenaConfig",
            target_id=conf.id,
            audit_metadata={"ended_by": current_user.email, "timestamp": now.isoformat()}
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "message": "Competition marked as completed. All missing submissions were auto-filled with 0 marks.",
            "status": "completed",
            "ended_at": now.isoformat()
        }

    @classmethod
    def release_results(cls, db: Session, current_user: User) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        
        if conf.status not in ["completed", "results_available"]:
            cls.end_competition(db, current_user)
            
        now = datetime.utcnow()
        if not conf.ended_at:
            conf.ended_at = now
        conf.status = "results_available"
        conf.results_released_at = now

        audit = AuditLog(
            actor_user_id=current_user.id,
            action="arena.results_released",
            target_type="ArenaConfig",
            target_id=conf.id,
            audit_metadata={"released_by": current_user.email, "timestamp": now.isoformat()}
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "message": "Results released! Participants can now view detailed performance reports.",
            "status": "results_available",
            "results_released_at": now.isoformat()
        }

    @classmethod
    def reset_arena(cls, db: Session, current_user: User) -> Dict[str, Any]:
        """
        Full reset: clears all session, submission, evaluation, and scoring data.
        Returns arena_config to 'waiting' state.
        Prompt bank is NOT touched — questions remain intact.
        """
        from app.models.arena_scoring import (
            ArenaFinalScore, ArenaIntegrityFlag, ArenaScoringJob,
            ArenaScoringRun, ArenaTestResult, ArenaDimensionScore
        )
        # --- ARCHIVE EXISTING DATA BEFORE DELETING ---
        import uuid
        from sqlalchemy import text
        arena_id = str(uuid.uuid4())
        
        # Archive Sessions
        db.execute(text(
            f"INSERT INTO archive_team_arena_sessions (archive_pk, arena_id, id, team_id, hackathon_id, prompt_ids, current_challenge_index, status, started_at, completed_at, created_at, updated_at) "
            f"SELECT id || '-' || '{arena_id}', '{arena_id}', id, team_id, hackathon_id, prompt_ids, current_challenge_index, status, started_at, completed_at, created_at, updated_at FROM team_arena_sessions"
        ))
        
        # Archive Submissions
        db.execute(text(
            f"INSERT INTO archive_arena_submissions (archive_pk, arena_id, id, team_id, prompt_bank_item_id, challenge_index, submitted_prompt, diagnosis_notes, server_timestamp, status) "
            f"SELECT id || '-' || '{arena_id}', '{arena_id}', id, team_id, prompt_bank_item_id, challenge_index, submitted_prompt, diagnosis_notes, server_timestamp, status FROM arena_submissions"
        ))
        
        # Archive Evaluations
        db.execute(text(
            f"INSERT INTO archive_arena_evaluations (archive_pk, arena_id, id, submission_id, judge_user_id, clarity_score, specificity_score, context_score, output_format_score, output_structure_score, constraints_score, relevance_score, total_score, judge_feedback, created_at) "
            f"SELECT id || '-' || '{arena_id}', '{arena_id}', id, submission_id, judge_user_id, clarity_score, specificity_score, context_score, output_format_score, output_structure_score, constraints_score, relevance_score, total_score, judge_feedback, created_at FROM arena_evaluations"
        ))
        
        # Delete original data
        db.query(ArenaTestResult).delete(synchronize_session=False)
        db.query(ArenaDimensionScore).delete(synchronize_session=False)
        db.query(ArenaScoringRun).delete(synchronize_session=False)
        db.query(ArenaScoringJob).delete(synchronize_session=False)
        db.query(ArenaIntegrityFlag).delete(synchronize_session=False)
        db.query(ArenaFinalScore).delete(synchronize_session=False)
        db.query(ArenaEvaluation).delete(synchronize_session=False)
        db.query(ArenaSubmission).delete(synchronize_session=False)
        db.query(ArenaSecurityEvent).delete(synchronize_session=False)
        db.query(TeamArenaSession).delete(synchronize_session=False)

        conf = cls.get_or_create_config(db)
        conf.status = "waiting"
        conf.started_at = None
        conf.ended_at = None
        conf.results_released_at = None

        audit = AuditLog(
            actor_user_id=current_user.id,
            action="arena.reset",
            target_type="ArenaConfig",
            target_id=conf.id,
            audit_metadata={"reset_by": current_user.email, "timestamp": datetime.utcnow().isoformat()}
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "message": "Arena fully reset. All sessions and submissions cleared. Prompt bank intact. Status: waiting.",
            "status": "waiting"
        }


    @staticmethod
    def parse_prompt_ids(raw_prompt_ids) -> List[str]:
        if isinstance(raw_prompt_ids, str):
            try:
                import json
                return json.loads(raw_prompt_ids)
            except Exception:
                return []
        if isinstance(raw_prompt_ids, list):
            return raw_prompt_ids
        return []

    @classmethod
    def get_my_challenge(cls, db: Session, current_user: User) -> Dict[str, Any]:
        team = cls.get_user_team(db, current_user)
        if not team:
            raise HTTPException(status_code=403, detail="User is not associated with an active participating team.")

        conf = cls.get_or_create_config(db)

        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        is_eliminated = (team.status == "eliminated" or (session and session.status == "eliminated"))
        if is_eliminated:
            return {
                "competition_status": "eliminated",
                "is_eliminated": True,
                "is_completed": True,
                "team_name": team.name,
                "college": team.college,
                "message": "Team has been eliminated by the competition adjudicator.",
                "challenge": None
            }

        if not session:
            try:
                assigned_ids = cls.assign_unique_prompts_for_team(db, team)
                session = TeamArenaSession(
                    team_id=team.id,
                    hackathon_id="hk-2026",
                    prompt_ids=assigned_ids,
                    current_challenge_index=1,
                    status="active" if conf.status == "live" else "waiting",
                    started_at=datetime.utcnow() if conf.status == "live" else None
                )
                db.add(session)
                db.commit()
                db.refresh(session)
            except IntegrityError:
                db.rollback()
                session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
                if not session:
                    raise HTTPException(status_code=500, detail="Failed to initialize arena session due to concurrent load.")

        violation_count = db.query(ArenaSecurityEvent).filter(ArenaSecurityEvent.team_id == team.id).count()

        if session.current_challenge_index > conf.challenges_count:
            return {
                "competition_status": conf.status,
                "is_completed": True,
                "message": "All 5 challenges completed.",
                "team_name": team.name,
                "security_violation_count": violation_count,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "results_available": conf.status == "results_available"
            }

        if conf.status == "waiting":
            return {
                "competition_status": "waiting",
                "is_completed": False,
                "current_challenge_index": session.current_challenge_index,
                "total_challenges": conf.challenges_count,
                "team_name": team.name,
                "security_violation_count": violation_count,
                "challenge": None,
                "message": "Waiting for the Judge to start the competition."
            }

        prompt_ids = cls.parse_prompt_ids(session.prompt_ids)
        if not prompt_ids or len(prompt_ids) < session.current_challenge_index:
            prompt_ids = cls.assign_unique_prompts_for_team(db, team)
            session.prompt_ids = prompt_ids
            db.commit()
            db.refresh(session)

        active_prompt_id = prompt_ids[session.current_challenge_index - 1]
        prompt_item = db.query(PromptBankItem).filter(PromptBankItem.id == active_prompt_id).first()
        if not prompt_item:
            # Fallback lookup by code or first available item if database was reseeded
            prompt_item = db.query(PromptBankItem).filter(PromptBankItem.code == f"P00{session.current_challenge_index}").first() or db.query(PromptBankItem).first()
            if not prompt_item:
                raise HTTPException(status_code=404, detail="Assigned prompt item not found in bank.")

        return {
            "competition_status": conf.status,
            "is_completed": False,
            "current_challenge_index": session.current_challenge_index,
            "total_challenges": conf.challenges_count,
            "team_name": team.name,
            "college": team.college,
            "security_violation_count": violation_count,
            "challenge": {
                "id": prompt_item.id,
                "code": prompt_item.code,
                "title": prompt_item.title,
                "category": prompt_item.category,
                "difficulty": prompt_item.difficulty,
                "original_bad_prompt": prompt_item.original_bad_prompt,
                "bad_output_evidence": prompt_item.bad_output_evidence,
                "challenge_number": session.current_challenge_index
            }
        }

    @classmethod
    def submit_challenge(cls, db: Session, current_user: User, payload: SubmitChallengeRequest) -> Dict[str, Any]:
        import unicodedata # Phase 0 / Defect #13
        team = cls.get_user_team(db, current_user)
        if not team:
            raise HTTPException(status_code=403, detail="Unauthorized: User is not linked to an active team.")

        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        if team.status == "eliminated" or (session and session.status == "eliminated"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team has been eliminated from the competition and cannot submit challenges."
            )

        conf = cls.get_or_create_config(db)
        if conf.status == "waiting":
            raise HTTPException(status_code=400, detail="Competition has not started yet. Please remain on the waiting screen.")
        if conf.status in ["completed", "results_available"]:
            raise HTTPException(status_code=400, detail="Submissions are closed. The competition has ended.")

        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        if not session:
            assigned_ids = cls.assign_unique_prompts_for_team(db, team)
            session = TeamArenaSession(
                team_id=team.id,
                hackathon_id="hk-2026",
                prompt_ids=assigned_ids,
                current_challenge_index=1,
                status="active" if conf.status == "live" else "waiting",
                started_at=datetime.utcnow() if conf.status == "live" else None
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        curr_idx = session.current_challenge_index
        if curr_idx > conf.challenges_count:
            raise HTTPException(status_code=400, detail="Team has already completed all 5 challenges.")

        existing = db.query(ArenaSubmission).filter(
            ArenaSubmission.team_id == team.id,
            ArenaSubmission.challenge_index == curr_idx
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Challenge {curr_idx} has already been submitted and is locked.")

        prompt_ids = cls.parse_prompt_ids(session.prompt_ids)
        if not prompt_ids or len(prompt_ids) < curr_idx:
            prompt_ids = cls.assign_unique_prompts_for_team(db, team)
            session.prompt_ids = prompt_ids
            db.commit()
            db.refresh(session)

        if not prompt_ids or len(prompt_ids) < curr_idx:
            raise HTTPException(status_code=400, detail=f"No assigned prompt found for challenge index {curr_idx}.")

        prompt_id = prompt_ids[curr_idx - 1]
        prompt_item = db.query(PromptBankItem).filter(PromptBankItem.id == prompt_id).first()
        if not prompt_item:
            prompt_item = db.query(PromptBankItem).filter(PromptBankItem.code == f"P00{curr_idx}").first() or db.query(PromptBankItem).first()
            if prompt_item:
                prompt_id = prompt_item.id

        server_now = datetime.utcnow()

        # Phase 0 / Defect #13: Unicode normalization
        normalized_prompt = unicodedata.normalize("NFC", payload.prompt_text.strip())

        try:
            sub_id = str(uuid.uuid4())
            sub = ArenaSubmission(
                id=sub_id,
                team_id=team.id,
                prompt_bank_item_id=prompt_id,
                challenge_index=curr_idx,
                submitted_prompt=normalized_prompt,
                diagnosis_notes=payload.diagnosis_notes, # Phase 0 / Defect #4
                server_timestamp=server_now,
                status="locked"
            )
            db.add(sub)
            db.flush()

            # Compute instant Evaluation Engine scores (5 dimensions: 0, 10, 20 marks each)
            def _analyze_text(txt, challenge_title="", original_bad_prompt=""):
                if not txt or len(txt.strip()) < 8:
                    return [0, 0, 0, 0, 0]
                
                import difflib
                if original_bad_prompt:
                    seq = difflib.SequenceMatcher(None, txt.strip().lower(), original_bad_prompt.strip().lower())
                    if seq.ratio() > 0.85:
                        return [0, 0, 0, 0, 0]
                
                lower = txt.lower()
                import re
                
                # Heuristic Relevance Gate
                if challenge_title:
                    title_words = set(re.findall(r'\b[a-z]{4,}\b', challenge_title.lower()))
                    title_words -= {"question", "write", "create", "generate", "draft", "make", "good", "clear", "with", "this", "that", "what", "how", "when", "where", "why", "who", "which"}
                    if title_words:
                        overlap = sum(1 for w in title_words if w in lower)
                        if overlap == 0:
                            # Completely off-topic based on heuristic
                            return [0, 0, 0, 0, 0]

                words = len(txt.split())
                lines = len([l for l in txt.split('\n') if l.strip()])
                
                # Clarity
                clarity = 0
                if re.search(r'\b(write|draft|extract|classify|summarize|summarise|generate|return|list|convert|translate|identify|analyze|analyse|produce|create|answer|rewrite|turn|respond|reply|explain|compare|decide|output)\b', lower):
                    clarity += 0.4
                clarity += 0.3 if words >= 30 else (0.18 if words >= 14 else 0.06)
                if lines >= 2 or len(re.findall(r'[.!?](\s|$)', txt)) >= 2:
                    clarity += 0.15
                if re.search(r'\b(so that|in order to|goal|objective|purpose|because|to help|used for|will be used)\b', lower):
                    clarity += 0.15

                # Specificity
                specificity = 0
                if re.search(r'\d', txt):
                    specificity += 0.3
                if re.search(r'\b(exactly|at most|at least|no more than|no fewer than|maximum|minimum|under|between|within|up to)\b', lower):
                    specificity += 0.25
                if re.search(r'\b(e\.g\.|for example|such as|like:)\b|"[^"]{3,}"', txt):
                    specificity += 0.25
                if re.search(r'^\s*([-*•]|\d+[.)])\s+', txt, re.M):
                    specificity += 0.2

                # Context
                context = 0
                if re.search(r'\b(you are|act as|your role|as an? [a-z-]+ (?:expert|analyst|engineer|assistant|editor|writer|strategist|agent|reviewer))\b', lower):
                    context += 0.4
                if re.search(r'\b(audience|reader|readers|customer|customers|user|users|manager|managers|student|students|beginner|team)\b', lower):
                    context += 0.3
                if re.search(r'\b(context|background|scenario|given|input|the following|below|based on|using only)\b', lower):
                    context += 0.3

                # Output format
                fmt = 0
                if re.search(r'\b(json|xml|yaml|csv|markdown|table|schema|sql|list|bullet|bullets|key|keys|value|values|object|array|string|number|boolean)\b', lower):
                    fmt += 0.35
                if re.search(r'\b(field|fields|column|columns|heading|headings|section|sections|paragraph|paragraphs|response|structure|structured|template)\b', lower):
                    fmt += 0.35
                if re.search(r'\b(format|form|layout|pattern|delimiter|delimiters|wrapper|valid|strictly|only|no preamble|no conversational|no extra|return only|output only|respond only)\b', lower):
                    fmt += 0.35
                if re.search(r'[:{}\[\]```\-*#]', txt):
                    fmt += 0.25

                # Constraints — only explicit constraint/rule language, NOT common words
                constraints = 0
                if re.search(r'\b(must not|never|do not|don\'t|cannot|forbidden|prohibit|prohibited|restrict|restricted|prevent|avoid using|exclude|no [a-z]+)\b', lower):
                    constraints += 0.4
                if re.search(r'\b(unless|fallback|edge case|do not hallucinate|no hallucination|fact-based|factual only|guardrail|guardrails)\b', lower):
                    constraints += 0.4
                if re.search(r'\b(tone|style|max [0-9]|maximum [0-9]|min [0-9]|minimum [0-9]|word limit|character limit|sentence limit|banned words|banned:)\b', lower):
                    constraints += 0.4

                def map_s(v):
                    v_cap = min(1.0, max(0.0, v))
                    return 20.0 if v_cap >= 0.65 else (10.0 if v_cap >= 0.25 else 0.0)

                return [map_s(clarity), map_s(specificity), map_s(context), map_s(fmt), map_s(constraints)]

            scores = _analyze_text(normalized_prompt, prompt_item.title if prompt_item else "", prompt_item.original_bad_prompt if prompt_item else "")
            tot = sum(scores)

            from app.models.arena_scoring import ArenaFinalScore
            final_eval = ArenaFinalScore(
                id=str(uuid.uuid4()),
                submission_id=sub.id,
                clarity_score=scores[0],
                specificity_score=scores[1],
                context_score=scores[2],
                output_format_score=scores[3],
                constraints_score=scores[4],
                total=round(tot, 2),
                source="engine"
            )
            db.add(final_eval)

            session.current_challenge_index += 1
            is_now_completed = session.current_challenge_index > conf.challenges_count

            if is_now_completed:
                session.status = "completed"
                session.completed_at = server_now
                team.status = "completed"
                
                db.add(AuditLog(
                    actor_user_id=current_user.id,
                    action="arena.team_completed",
                    target_type="Team",
                    target_id=team.id,
                    audit_metadata={"completed_at": server_now.isoformat(), "team_name": team.name}
                ))

            db.add(AuditLog(
                actor_user_id=current_user.id,
                action="arena.submit_challenge",
                target_type="ArenaSubmission",
                target_id=sub.id,
                audit_metadata={
                    "challenge_index": curr_idx,
                    "team_id": team.id,
                    "server_timestamp": server_now.isoformat()
                }
            ))

            db.commit()

            # Fire Groq contextual evaluation in a background thread
            # (submission API responds instantly; Groq updates score asynchronously)
            _fire_groq_eval(
                submission_id=sub.id,
                submitted_prompt=normalized_prompt,
                original_bad_prompt=prompt_item.original_bad_prompt if prompt_item else "",
                expected_good_prompt=prompt_item.expected_good_prompt if prompt_item else "",
                challenge_title=prompt_item.title if prompt_item else "",
                category=prompt_item.category if prompt_item else ""
            )
        except IntegrityError as ie:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Submission conflict: Challenge {curr_idx} has already been submitted for your team."
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database submission failed: {str(e)}"
            )

        return {
            "success": True,
            "message": f"Challenge {curr_idx} submitted and locked.",
            "submitted_index": curr_idx,
            "next_challenge_index": session.current_challenge_index,
            "is_completed": is_now_completed,
            "server_timestamp": server_now.isoformat()
        }

    @classmethod
    def record_security_event(cls, db: Session, current_user: Optional[User], payload: SecurityEventRequest) -> Dict[str, Any]:
        team = cls.get_user_team(db, current_user) if current_user else None
        team_id = team.id if team else "unknown-team"

        count = db.query(ArenaSecurityEvent).filter(ArenaSecurityEvent.team_id == team_id).count() + 1

        sec_event = ArenaSecurityEvent(
            team_id=team_id,
            event_type=payload.event_type,
            violation_count=count,
            client_metadata=payload.client_metadata or {}
        )
        db.add(sec_event)
        db.commit()

        return {
            "success": True,
            "event_id": sec_event.id,
            "total_violations": count,
            "flagged": count >= 3
        }

    @classmethod
    def get_judge_overview(cls, db: Session, current_user: User) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        teams = db.query(Team).all()
        sessions = db.query(TeamArenaSession).all()

        total_teams = len(teams)
        completed_count = sum(1 for s in sessions if s.status == "completed")
        active_count = sum(1 for s in sessions if s.status == "active")
        waiting_count = total_teams - completed_count - active_count

        flagged_query = db.query(
            ArenaSecurityEvent.team_id,
            func.count(ArenaSecurityEvent.id).label("violation_count")
        ).group_by(ArenaSecurityEvent.team_id).all()
        
        flagged_team_map = {t_id: count for t_id, count in flagged_query if count >= 3}
        from sqlalchemy.orm import joinedload
        submissions = db.query(ArenaSubmission).options(
            joinedload(ArenaSubmission.team),
            joinedload(ArenaSubmission.prompt_item)
        ).order_by(ArenaSubmission.server_timestamp.desc()).all()
        from app.models.arena_scoring import ArenaFinalScore
        sub_ids = [s.id for s in submissions]
        eval_records = db.query(ArenaFinalScore).filter(ArenaFinalScore.submission_id.in_(sub_ids)).all() if sub_ids else []
        eval_map = {e.submission_id: e for e in eval_records}
        
        sub_list = []
        for sub in submissions:
            t = sub.team
            p = sub.prompt_item
            eval_record = eval_map.get(sub.id)

            sub_list.append({
                "id": sub.id,
                "team_id": sub.team_id,
                "team_name": t.name if t else "Unknown",
                "team_status": t.status if t else "unknown",
                "is_eliminated": (t.status == "eliminated") if t else False,
                "college": t.college if t else "N/A",
                "challenge_index": sub.challenge_index,
                "prompt_code": p.code if p else "P--",
                "prompt_title": p.title if p else "Flawed Prompt",
                "challenge_difficulty": p.difficulty if p else "medium",
                "original_bad_prompt": p.original_bad_prompt if p else "",
                "bad_output_evidence": p.bad_output_evidence if p else "",
                "submitted_prompt": sub.submitted_prompt,
                "submitted_at": sub.server_timestamp.isoformat() + "Z", # Phase 0 / Defect #6: ISO-8601
                "is_evaluated": eval_record is not None, # Phase 0 / Defect #6: UI expects is_evaluated
                "evaluation": {
                    "clarity_score": eval_record.clarity_score,
                    "context_score": eval_record.context_score,
                    "specificity_score": eval_record.specificity_score,
                    "output_format_score": eval_record.output_format_score,
                    "constraints_score": eval_record.constraints_score,
                    "total_score": eval_record.total,
                    "source": eval_record.source
                } if eval_record else None
            })

        recent_events = db.query(ArenaSecurityEvent).options(joinedload(ArenaSecurityEvent.team)).order_by(ArenaSecurityEvent.created_at.desc()).limit(25).all()
        events_list = []
        for ev in recent_events:
            t = ev.team
            events_list.append({
                "id": ev.id,
                "team_name": t.name if t else "Unknown",
                "event_type": ev.event_type,
                "violation_count": ev.violation_count,
                "metadata": ev.client_metadata, # Phase 0 / Defect #6: UI expects metadata
                "timestamp": ev.created_at.isoformat() + "Z" # Phase 0 / Defect #6: ISO-8601
            })
        flagged_list = [{
            "team_id": tid,
            "team_name": next((t.name for t in teams if t.id == tid), "Unknown"),
            "violation_count": count,
            "is_eliminated": next((t.status == "eliminated" for t in teams if t.id == tid), False)
        } for tid, count in flagged_team_map.items()]
        total_submissions_count = len(sub_list)
        evaluated_submissions_count = sum(1 for s in sub_list if s.get("is_evaluated"))
        pending_evaluations_count = total_submissions_count - evaluated_submissions_count

        metrics_dict = {
            "total_teams": total_teams,
            "waiting_teams": max(waiting_count, 0),
            "active_teams": active_count,
            "completed_teams": completed_count,
            "total_submissions": total_submissions_count,
            "evaluated_submissions": evaluated_submissions_count,
            "pending_evaluations": pending_evaluations_count,
            "flagged_teams_count": len(flagged_team_map),
            "flagged_teams": len(flagged_team_map),
            "flagged_teams_list": flagged_list
        }

        ends_at_val = None
        if conf.status == "live" and conf.started_at:
            ends_at_val = (conf.started_at + timedelta(minutes=30)).isoformat() + "Z"
        elif conf.ended_at:
            ends_at_val = conf.ended_at.isoformat() + "Z"

        return {
            "status": conf.status,
            "is_results_released": getattr(conf, 'is_results_released', False),
            "started_at": conf.started_at.isoformat() + "Z" if conf.started_at else None,
            "ends_at": ends_at_val,
            "active_dataset_tag": getattr(conf, 'active_dataset_tag', None),
            "metrics": metrics_dict,
            "stats": metrics_dict,
            "submissions": sub_list,
            "security_events": events_list
        }

    @classmethod
    def score_submission(cls, db: Session, current_user: User, payload: JudgeScoreRequest) -> Dict[str, Any]:
        sub = db.query(ArenaSubmission).filter(ArenaSubmission.id == payload.submission_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Submission not found.")

        output_val = payload.output_format_score if payload.output_format_score is not None else (payload.output_structure_score or 0.0)
        constraints_val = payload.constraints_score if payload.constraints_score is not None else (payload.relevance_score or 0.0)

        total = (
            payload.clarity_score +
            payload.specificity_score +
            payload.context_score +
            output_val +
            constraints_val
        )

        evaluation = db.query(ArenaEvaluation).filter(
            ArenaEvaluation.submission_id == payload.submission_id,
            ArenaEvaluation.judge_user_id == current_user.id
        ).first()

        if not evaluation:
            evaluation = ArenaEvaluation(
                id=str(uuid.uuid4()),
                submission_id=payload.submission_id,
                judge_user_id=current_user.id
            )
            db.add(evaluation)
        db.flush()

        evaluation.clarity_score = payload.clarity_score
        evaluation.specificity_score = payload.specificity_score
        evaluation.context_score = payload.context_score
        evaluation.output_format_score = output_val
        evaluation.output_structure_score = output_val
        evaluation.constraints_score = constraints_val
        evaluation.relevance_score = constraints_val
        evaluation.total_score = round(total, 2)
        
        # Phase 0 schema compat logic
        fb = payload.feedback if payload.feedback is not None else payload.judge_feedback
        evaluation.judge_feedback = fb.strip() if fb else ""

        db.add(AuditLog(
            actor_user_id=current_user.id,
            action="arena.judge_score_submitted",
            target_type="ArenaEvaluation",
            target_id=evaluation.id,
            audit_metadata={
                "submission_id": sub.id,
                "team_id": sub.team_id,
                "total_score": round(total, 2)
            }
        ))

        db.commit()

        return {
            "success": True,
            "message": "Evaluation scored and recorded.",
            "total_score": round(total, 2)
        }

    @classmethod
    def eliminate_team(cls, db: Session, current_user: User, payload: EliminateTeamRequest) -> Dict[str, Any]:
        team = db.query(Team).filter(Team.id == payload.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found.")

        prev_status = team.status
        team.status = "eliminated"

        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        if session:
            session.status = "eliminated"

        db.add(AuditLog(
            actor_user_id=current_user.id,
            action="arena.team_eliminated",
            target_type="Team",
            target_id=team.id,
            audit_metadata={
                "reason": payload.reason,
                "previous_status": prev_status,
                "eliminated_by": current_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        ))
        db.commit()

        return {
            "success": True,
            "message": f"Team '{team.name}' has been eliminated from the competition.",
            "team_id": team.id,
            "team_name": team.name,
            "status": "eliminated",
            "reason": payload.reason
        }

    @classmethod
    def uneliminate_team(cls, db: Session, current_user: User, payload: EliminateTeamRequest) -> Dict[str, Any]:
        team = db.query(Team).filter(Team.id == payload.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found.")

        prev_status = team.status
        team.status = "active"

        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        if session:
            # Check if they have 5 challenges done
            submissions = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == team.id).count()
            session.status = "completed" if submissions >= 5 else "active"

        db.add(AuditLog(
            actor_user_id=current_user.id,
            action="arena.team_uneliminated",
            target_type="Team",
            target_id=team.id,
            audit_metadata={
                "reason": payload.reason,
                "previous_status": prev_status,
                "uneliminated_by": current_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        ))
        db.commit()

        return {
            "success": True,
            "message": f"Team '{team.name}' has been restored to active status.",
            "team_id": team.id,
            "team_name": team.name,
            "status": team.status,
            "reason": payload.reason
        }

    @classmethod
    def get_performance_report(cls, db: Session, current_user: User) -> Dict[str, Any]:
        team = cls.get_user_team(db, current_user)
        if not team:
            raise HTTPException(status_code=403, detail="Team membership required.")

        conf = cls.get_or_create_config(db)
        if conf.status != "results_available":
            return {
                "available": False,
                "message": "Final performance reports will become available once the Evaluation Committee officially releases the results."
            }

        submissions = db.query(ArenaSubmission).filter(
            ArenaSubmission.team_id == team.id
        ).order_by(ArenaSubmission.challenge_index.asc()).all()

        challenges_report = []
        total_team_score = 0.0
        sum_clarity = 0.0
        sum_context = 0.0
        sum_specificity = 0.0
        sum_structure = 0.0
        sum_relevance = 0.0

        from app.models.arena_scoring import ArenaFinalScore

        for sub in submissions:
            p = sub.prompt_item
            evals = sub.evaluations
            if evals:
                avg_clarity = sum(e.clarity_score for e in evals) / len(evals)
                avg_context = sum(e.context_score for e in evals) / len(evals)
                avg_spec = sum(e.specificity_score for e in evals) / len(evals)
                avg_struct = sum(e.output_structure_score for e in evals) / len(evals)
                avg_rel = sum(e.relevance_score for e in evals) / len(evals)
                c_total = sum(e.total_score for e in evals) / len(evals)
                feedback = "; ".join([e.judge_feedback for e in evals if e.judge_feedback])
            else:
                engine_score = db.query(ArenaFinalScore).filter(ArenaFinalScore.submission_id == sub.id).first()
                if engine_score:
                    avg_clarity = engine_score.clarity_score
                    avg_context = engine_score.context_score
                    avg_spec = engine_score.specificity_score
                    avg_struct = engine_score.output_format_score
                    avg_rel = engine_score.constraints_score
                    c_total = engine_score.total
                    feedback = "Evaluated by AI Engine."
                else:
                    avg_clarity = avg_context = avg_spec = avg_struct = avg_rel = c_total = 0.0
                    feedback = "No comments recorded."

            total_team_score += c_total
            sum_clarity += avg_clarity
            sum_context += avg_context
            sum_specificity += avg_spec
            sum_structure += avg_struct
            sum_relevance += avg_rel

            challenges_report.append({
                "challenge_index": sub.challenge_index,
                "code": p.code if p else f"C0{sub.challenge_index}",
                "title": p.title if p else "Prompt Case",
                "category": p.category if p else "general",
                "original_bad_prompt": p.original_bad_prompt if p else "",
                "submitted_prompt": sub.submitted_prompt,
                "score": round(c_total, 1),
                "dimensions": {
                    "clarity": round(avg_clarity, 1),
                    "context": round(avg_context, 1),
                    "specificity": round(avg_spec, 1),
                    "output_structure": round(avg_struct, 1),
                    "relevance": round(avg_rel, 1)
                },
                "judge_feedback": feedback
            })

        dimension_map = {
            "Clarity": sum_clarity,
            "Context": sum_context,
            "Specificity": sum_specificity,
            "Output Structure": sum_structure,
            "Relevance": sum_relevance
        }
        sorted_dims = sorted(dimension_map.items(), key=lambda x: x[1], reverse=True)
        strengths = f"Strong mastery of {sorted_dims[0][0]} and {sorted_dims[1][0]} under iterative pressure."
        improvements = f"Focus on elevating {sorted_dims[-1][0]} and {sorted_dims[-2][0]} by providing sharper schema constraints."

        return {
            "available": True,
            "team_name": team.name,
            "college": team.college,
            "total_score": round(total_team_score, 1),
            "max_score": 500, # Phase 0 / Defect #1: 5 challenges * 100 max = 500
            "dimension_totals": {
                "clarity": round(sum_clarity, 1),
                "context": round(sum_context, 1),
                "specificity": round(sum_specificity, 1),
                "output_structure": round(sum_structure, 1),
                "relevance": round(sum_relevance, 1)
            },
            "strengths": strengths,
            "areas_to_improve": improvements,
            "challenges": challenges_report
        }

    @classmethod
    def get_leaderboard(cls, db: Session, current_user: Optional[User] = None) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        user_roles = [r.name for r in current_user.roles] if (current_user and current_user.roles) else []
        is_staff = any(r in ["admin", "judge"] for r in user_roles)
        
        if conf.status != "results_available" and not is_staff:
            return {
                "results_available": False,
                "message": "Official standings are masked during active competition. Standings will be visible when results are released.",
                "standings": []
            }

        # ── Filter out test/dev teams — never shown in leaderboard ──────────
        TEST_TEAM_NAMES = {"test", "test2", "topibazz"}
        teams = [
            t for t in db.query(Team).all()
            if t.name.strip().lower() not in TEST_TEAM_NAMES
        ]
        eligible_standings = []
        eliminated_standings = []
        
        from app.models.arena_scoring import ArenaFinalScore

        from sqlalchemy.orm import joinedload
        
        # Bulk fetch to prevent N+1 queries under load
        all_sessions = {s.team_id: s for s in db.query(TeamArenaSession).all()}
        all_submissions = db.query(ArenaSubmission).options(joinedload(ArenaSubmission.evaluations)).all()
        subs_by_team = {}
        for s in all_submissions:
            subs_by_team.setdefault(s.team_id, []).append(s)
            
        all_engine_scores = {es.submission_id: es for es in db.query(ArenaFinalScore).all()}

        from sqlalchemy import func
        from app.models.arena import ArenaSecurityEvent
        flagged_query = db.query(
            ArenaSecurityEvent.team_id,
            func.count(ArenaSecurityEvent.id).label("violation_count")
        ).group_by(ArenaSecurityEvent.team_id).all()
        violation_counts = {t_id: count for t_id, count in flagged_query}

        for t in teams:
            session = all_sessions.get(t.id)
            submissions = subs_by_team.get(t.id, [])
            
            is_eliminated = (t.status == "eliminated" or (session and session.status == "eliminated"))

            total_score = 0.0
            for sub in submissions:
                evals = sub.evaluations
                if evals:
                    total_score += sum(e.total_score for e in evals) / len(evals)
                else:
                    engine_score = all_engine_scores.get(sub.id)
                    if engine_score:
                        total_score += engine_score.total

            avg_score = round(total_score / 5.0, 2)
            completed_time = session.completed_at if session else None
            
            total_time_taken = 9999999999.0
            average_lockin_time = 9999999999.0
            violations = violation_counts.get(t.id, 0)
            
            if session and session.started_at:
                started = session.started_at
                last_time = started
                total_lockin = 0.0
                submissions.sort(key=lambda s: s.server_timestamp)
                for sub in submissions:
                    time_taken = (sub.server_timestamp - last_time).total_seconds()
                    total_lockin += max(0, time_taken)
                    last_time = sub.server_timestamp
                
                if submissions:
                    average_lockin_time = total_lockin / len(submissions)
                
                if len(submissions) >= 5 and session.completed_at:
                    total_time_taken = (session.completed_at - session.started_at).total_seconds()
            
            item = {
                "team_id": t.id,
                "team_name": t.name,
                "college": t.college or "N/A",
                "total_score": round(total_score, 1),
                "average_score": avg_score,
                "completed_challenges": len(submissions),
                "completed_at": completed_time.isoformat() + "Z" if completed_time else None,
                "total_time_taken": total_time_taken,
                "average_lockin_time": average_lockin_time,
                "violations": violations,
                "created_at": t.created_at.timestamp() if t.created_at else 0,
                "is_eliminated": is_eliminated,
                "status": "eliminated" if is_eliminated else ("completed" if len(submissions) >= 5 else (t.status or "active"))
            }

            if is_eliminated:
                item["rank"] = None
                item["podium"] = None
                item["tie_breaker_reason"] = None
                eliminated_standings.append(item)
            else:
                eligible_standings.append(item)

        # ── Authoritative 5-tier sort (draws broken by time then violations) ──
        # Tier 1: Total score (higher is better)
        # Tier 2: Total completion time (lower = faster = better)
        # Tier 3: Average per-prompt lock-in time (lower = faster responses)
        # Tier 4: Fewer security violations (lower is better)
        # Tier 5: Earlier registration (team created_at, lower is earlier)
        eligible_standings.sort(key=lambda x: (
            -x["total_score"],
            x["total_time_taken"],
            x["average_lockin_time"],
            x["violations"],
            x["created_at"]
        ))

        from collections import Counter
        score_counts = Counter(x["total_score"] for x in eligible_standings)

        for idx, entry in enumerate(eligible_standings):
            entry["rank"] = idx + 1
            entry["podium"] = "winner" if idx == 0 else "runner_up" if idx == 1 else "second_runner_up" if idx == 2 else None

            tied_peers = [
                e for e in eligible_standings
                if e["total_score"] == entry["total_score"] and e["team_id"] != entry["team_id"]
            ]

            if not tied_peers:
                # No draw — no tiebreaker needed
                entry["tie_breaker_reason"] = None
            else:
                # Determine which tier actually resolved the tie for this entry
                # Tier 2: total completion time differed among tied peers?
                peer_times = [e["total_time_taken"] for e in tied_peers]
                all_same_time = all(t == entry["total_time_taken"] for t in peer_times)

                if not all_same_time and entry["total_time_taken"] < 9999999999.0:
                    entry["tie_breaker_reason"] = (
                        f"Tiebreak \u2192 Completion time: {round(entry['total_time_taken']/60, 1)}m"
                    )
                else:
                    # Tier 3: average per-prompt lock-in time
                    peer_lockins = [e["average_lockin_time"] for e in tied_peers]
                    all_same_lockin = all(l == entry["average_lockin_time"] for l in peer_lockins)

                    if not all_same_lockin and entry["average_lockin_time"] < 9999999999.0:
                        entry["tie_breaker_reason"] = (
                            f"Tiebreak \u2192 Avg lock-in: {round(entry['average_lockin_time'], 1)}s/prompt"
                        )
                    else:
                        # Tier 4: violations
                        peer_violations = [e["violations"] for e in tied_peers]
                        all_same_violations = all(v == entry["violations"] for v in peer_violations)

                        if not all_same_violations:
                            entry["tie_breaker_reason"] = (
                                f"Tiebreak \u2192 Violations: {entry['violations']}"
                            )
                        else:
                            # Tier 5: registration time
                            entry["tie_breaker_reason"] = "Tiebreak \u2192 Earlier registration"
            
            # Clean up sort keys to reduce payload size if desired, but we can leave them for debug

        return {
            "results_available": conf.status == "results_available",
            "standings": eligible_standings + eliminated_standings
        }

    @classmethod
    def get_team_score_dashboard(cls, db: Session, current_user: User) -> Dict[str, Any]:
        team = cls.get_user_team(db, current_user)
        if not team:
            raise HTTPException(status_code=403, detail="Team membership required.")

        conf = cls.get_or_create_config(db)
        session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == team.id).first()
        is_eliminated = (team.status == "eliminated" or (session and session.status == "eliminated"))

        submissions = db.query(ArenaSubmission).filter(
            ArenaSubmission.team_id == team.id
        ).order_by(ArenaSubmission.challenge_index.asc()).all()

        total_score = 0.0
        challenges_report = []

        from app.models.arena_scoring import ArenaFinalScore

        for sub in submissions:
            p = db.query(PromptBankItem).filter(PromptBankItem.id == sub.prompt_bank_item_id).first()
            evals = sub.evaluations
            if evals:
                avg_clarity = sum(e.clarity_score for e in evals) / len(evals)
                avg_spec = sum(e.specificity_score for e in evals) / len(evals)
                avg_context = sum(e.context_score for e in evals) / len(evals)
                avg_format = sum((e.output_format_score if e.output_format_score is not None else e.output_structure_score) for e in evals) / len(evals)
                avg_constraints = sum((e.constraints_score if e.constraints_score is not None else e.relevance_score) for e in evals) / len(evals)
                c_total = sum(e.total_score for e in evals) / len(evals)
                feedback = "; ".join([e.judge_feedback for e in evals if e.judge_feedback])
            else:
                engine_score = db.query(ArenaFinalScore).filter(ArenaFinalScore.submission_id == sub.id).first()
                if engine_score:
                    avg_clarity = engine_score.clarity_score
                    avg_spec = engine_score.specificity_score
                    avg_context = engine_score.context_score
                    avg_format = engine_score.output_format_score
                    avg_constraints = engine_score.constraints_score
                    c_total = engine_score.total
                    feedback = "Evaluated by AI Engine."
                else:
                    avg_clarity = avg_spec = avg_context = avg_format = avg_constraints = c_total = 0.0
                    feedback = "Pending evaluation."

            total_score += c_total

            challenges_report.append({
                "challenge_index": sub.challenge_index,
                "code": p.code if p else f"Q0{sub.challenge_index}",
                "title": p.title if p else f"Question {sub.challenge_index}",
                "category": p.category if p else "general",
                "submitted_prompt": sub.submitted_prompt,
                "score": round(c_total, 1),
                "characteristics": {
                    "clarity": round(avg_clarity, 1),
                    "specificity": round(avg_spec, 1),
                    "context": round(avg_context, 1),
                    "output_format": round(avg_format, 1),
                    "constraints": round(avg_constraints, 1)
                },
                "server_timestamp": sub.server_timestamp.isoformat(),
                "judge_feedback": feedback
            })

        avg_score = round(total_score / 5.0, 2)
        
        # Rank from authoritative leaderboard
        lb = cls.get_leaderboard(db, current_user=None)
        standings = lb.get("standings", [])
        my_standing = next((s for s in standings if s["team_id"] == team.id), None)
        rank = my_standing["rank"] if my_standing else None

        # Phase 0 / Defect #11: Gate results securely until released
        if conf.status != "results_available":
            return {
                "team_id": team.id,
                "team_name": team.name,
                "college": team.college or "N/A",
                "is_eliminated": is_eliminated,
                "status": "eliminated" if is_eliminated else (session.status if session else team.status),
                "total_score": None, # Masked
                "average_score": None, # Masked
                "rank": None,
                "completion_time": session.completed_at.isoformat() if (session and session.completed_at) else None,
                "challenges": [], # Masked
                "results_released": False
            }

        return {
            "team_id": team.id,
            "team_name": team.name,
            "college": team.college or "N/A",
            "is_eliminated": is_eliminated,
            "status": "eliminated" if is_eliminated else (session.status if session else team.status),
            "total_score": round(total_score, 1),
            "average_score": avg_score,
            "rank": rank,
            "completion_time": session.completed_at.isoformat() if (session and session.completed_at) else None,
            "challenges": challenges_report,
            "results_released": True
        }

    # ---------------------------------------------------------------------------
    # Archived Arena Service Methods
    # ---------------------------------------------------------------------------

    @classmethod
    def list_archived_arenas(cls, db: Session) -> Dict[str, Any]:
        """
        Returns a list of all past arena runs stored in the archive tables.
        Groups by arena_id and derives run metadata (date, team count, submission count).
        """
        from app.models.arena import ArchivedTeamArenaSession, ArchivedArenaSubmission
        from sqlalchemy import func, text

        # Get distinct arena_ids ordered by most recent
        rows = db.execute(text(
            "SELECT arena_id, COUNT(DISTINCT team_id) as team_count, "
            "MIN(created_at) as started_at, MAX(updated_at) as ended_at "
            "FROM archive_team_arena_sessions "
            "GROUP BY arena_id ORDER BY MIN(created_at) DESC"
        )).fetchall()

        archives = []
        for row in rows:
            arena_id = row[0]
            sub_count = db.execute(text(
                f"SELECT COUNT(*) FROM archive_arena_submissions WHERE arena_id = :aid"
            ), {"aid": arena_id}).scalar() or 0

            eval_count = db.execute(text(
                f"SELECT COUNT(*) FROM archive_arena_evaluations WHERE arena_id = :aid"
            ), {"aid": arena_id}).scalar() or 0

            archives.append({
                "arena_id": arena_id,
                "team_count": row[1],
                "submission_count": sub_count,
                "evaluated_count": eval_count,
                "started_at": row[2].isoformat() + "Z" if row[2] else None,
                "ended_at": row[3].isoformat() + "Z" if row[3] else None,
                "has_evaluations": eval_count > 0,
            })

        return {"archives": archives, "total": len(archives)}

    @classmethod
    def get_archived_standings(cls, db: Session, arena_id: str) -> Dict[str, Any]:
        """
        Compute full team standings from a specific archived arena run.
        Merges archived human evaluations and archived auto-scores.
        Returns ranked list of teams with per-challenge breakdown.
        """
        from app.models.arena import (
            ArchivedTeamArenaSession, ArchivedArenaSubmission, ArchivedArenaEvaluation
        )
        from sqlalchemy import text

        # Verify arena_id exists
        check = db.execute(text(
            "SELECT COUNT(*) FROM archive_team_arena_sessions WHERE arena_id = :aid"
        ), {"aid": arena_id}).scalar()
        if not check:
            raise HTTPException(status_code=404, detail=f"No archived arena found with ID: {arena_id}")

        # Load all archived sessions for this run
        sessions = db.execute(text(
            "SELECT id, team_id, status, current_challenge_index, started_at, completed_at "
            "FROM archive_team_arena_sessions WHERE arena_id = :aid"
        ), {"aid": arena_id}).fetchall()

        # Load all archived submissions for this run
        subs = db.execute(text(
            "SELECT id, team_id, challenge_index, submitted_prompt, server_timestamp "
            "FROM archive_arena_submissions WHERE arena_id = :aid ORDER BY challenge_index ASC"
        ), {"aid": arena_id}).fetchall()

        # Load all archived evaluations for this run
        evals = db.execute(text(
            "SELECT submission_id, clarity_score, specificity_score, context_score, "
            "output_format_score, constraints_score, total_score "
            "FROM archive_arena_evaluations WHERE arena_id = :aid"
        ), {"aid": arena_id}).fetchall()

        eval_by_sub = {e[0]: e for e in evals}
        subs_by_team: Dict[str, list] = {}
        for s in subs:
            subs_by_team.setdefault(s[1], []).append(s)

        # Fetch team names from live teams table (they still exist)
        team_ids = list({s[1] for s in sessions})
        team_names: Dict[str, str] = {}
        team_colleges: Dict[str, str] = {}
        if team_ids:
            team_rows = db.execute(text(
                "SELECT id, name, college FROM teams WHERE id = ANY(:ids)"
            ), {"ids": team_ids}).fetchall()
            team_names = {r[0]: r[1] for r in team_rows}
            team_colleges = {r[0]: (r[2] or "N/A") for r in team_rows}

        # Fetch team members
        team_members: Dict[str, list] = {}
        if team_ids:
            members = db.execute(text(
                "SELECT tm.team_id, u.name, u.email FROM team_members tm JOIN users u ON tm.user_id = u.id WHERE tm.team_id = ANY(:ids)"
            ), {"ids": team_ids}).fetchall()
            for m in members:
                team_members.setdefault(m[0], []).append({"name": m[1], "email": m[2]})

        standings = []
        for sess in sessions:
            sess_id, team_id, sess_status, challenge_index, started_at, completed_at = sess
            team_subs = subs_by_team.get(team_id, [])

            total_score = 0.0
            challenges = []
            
            total_time_taken = 9999999999.0
            average_lockin_time = 9999999999.0
            
            if started_at:
                last_time = started_at
                total_lockin = 0.0
                team_subs.sort(key=lambda x: x[4])
                for sub in team_subs:
                    sub_time = sub[4]
                    if sub_time:
                        time_taken = (sub_time - last_time).total_seconds()
                        total_lockin += max(0, time_taken)
                        last_time = sub_time
                if team_subs:
                    average_lockin_time = total_lockin / len(team_subs)
                if len(team_subs) >= 5 and completed_at:
                    total_time_taken = (completed_at - started_at).total_seconds()

            for sub in team_subs:
                sub_id, _, ch_idx, submitted_prompt, sub_time = sub
                ev = eval_by_sub.get(sub_id)
                ch_score = float(ev[6]) if ev else 0.0
                total_score += ch_score
                challenges.append({
                    "challenge_index": ch_idx,
                    "score": ch_score,
                    "submitted_at": sub_time.isoformat() + "Z" if sub_time else None,
                    "has_evaluation": ev is not None,
                })

            standings.append({
                "team_id": team_id,
                "team_name": team_names.get(team_id, f"Team {team_id[:8]}"),
                "college": team_colleges.get(team_id, "N/A"),
                "members": team_members.get(team_id, []),
                "is_eliminated": sess_status == "eliminated",
                "challenges_completed": len(team_subs),
                "total_score": round(total_score, 1),
                "average_score": round(total_score / 5.0, 2),
                "completed_at": completed_at.isoformat() + "Z" if completed_at else None,
                "total_time_taken": total_time_taken,
                "average_lockin_time": average_lockin_time,
                "challenges": challenges,
            })

        # Sort: eliminated last, then by total_score DESC, then tie breakers
        eligible = [s for s in standings if not s["is_eliminated"]]
        eliminated = [s for s in standings if s["is_eliminated"]]
        eligible.sort(key=lambda x: (-x["total_score"], x["total_time_taken"], x["average_lockin_time"]))
        eliminated.sort(key=lambda x: -x["total_score"])

        from collections import Counter
        score_counts = Counter(x["total_score"] for x in eligible)

        for i, s in enumerate(eligible, 1):
            s["rank"] = i
            if score_counts[s["total_score"]] > 1:
                if s["total_time_taken"] < 9999999999.0:
                    s["tie_breaker_reason"] = f"Completed in {round(s['total_time_taken']/60, 1)}m"
                elif s["average_lockin_time"] < 9999999999.0:
                    s["tie_breaker_reason"] = f"Avg lockin {round(s['average_lockin_time']/60, 1)}m"
                else:
                    s["tie_breaker_reason"] = "Tie"
            else:
                s["tie_breaker_reason"] = None
                
        for s in eliminated:
            s["rank"] = None
            s["tie_breaker_reason"] = None

        all_standings = eligible + eliminated
        for s in all_standings:
            s.pop("completed_at_ts", None)

        return {
            "arena_id": arena_id,
            "total_teams": len(standings),
            "standings": all_standings,
        }

