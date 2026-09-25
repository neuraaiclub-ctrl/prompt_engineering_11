import hashlib
import random
import uuid
from datetime import datetime
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

    @staticmethod
    def assign_unique_prompts_for_team(db: Session, team: Team) -> List[str]:
        all_prompts = db.query(PromptBankItem).order_by(PromptBankItem.code.asc()).all()
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

        seed_str = f"{team.id}_{team.name}_{team.invite_code}"
        salt_idx = 0
        while True:
            cur_seed_str = f"{seed_str}_{salt_idx}" if salt_idx > 0 else seed_str
            seed_val = int(hashlib.sha256(cur_seed_str.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed_val)
            sampled = rng.sample(all_prompts, 5)
            candidate = [p.id for p in sampled]
            if tuple(candidate) not in assigned_sets or salt_idx > 1000:
                return candidate
            salt_idx += 1

    @classmethod
    def get_status(cls, db: Session, current_user: Optional[User] = None) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        server_now = datetime.utcnow()

        response: Dict[str, Any] = {
            "status": conf.status,
            "server_time": server_now.isoformat(),
            "started_at": conf.started_at.isoformat() if conf.started_at else None,
            "ended_at": conf.ended_at.isoformat() if conf.ended_at else None,
            "results_released_at": conf.results_released_at.isoformat() if conf.results_released_at else None,
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
                        "status": "waiting",
                        "is_completed": False,
                        "completed_at": None
                    }

        return response

    @classmethod
    def start_competition(cls, db: Session, current_user: User) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)

        # Clear old arena data so only teams and prompt questions remain
        db.query(ArenaEvaluation).delete()
        db.query(ArenaSubmission).delete()
        db.query(ArenaSecurityEvent).delete()
        db.query(TeamArenaSession).delete()

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
            "message": "Competition marked as completed. Submissions are now closed.",
            "status": "completed",
            "ended_at": now.isoformat()
        }

    @classmethod
    def release_results(cls, db: Session, current_user: User) -> Dict[str, Any]:
        conf = cls.get_or_create_config(db)
        now = datetime.utcnow()
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

        if session.current_challenge_index > conf.challenges_count:
            return {
                "competition_status": conf.status,
                "is_completed": True,
                "message": "All 5 challenges completed.",
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "results_available": conf.status == "results_available"
            }

        if conf.status == "waiting":
            return {
                "competition_status": "waiting",
                "is_completed": False,
                "current_challenge_index": session.current_challenge_index,
                "total_challenges": conf.challenges_count,
                "challenge": None,
                "message": "Waiting for the Judge to start the competition."
            }

        prompt_ids = session.prompt_ids
        active_prompt_id = prompt_ids[session.current_challenge_index - 1]
        prompt_item = db.query(PromptBankItem).filter(PromptBankItem.id == active_prompt_id).first()
        if not prompt_item:
            raise HTTPException(status_code=404, detail="Assigned prompt item not found in bank.")

        return {
            "competition_status": conf.status,
            "is_completed": False,
            "current_challenge_index": session.current_challenge_index,
            "total_challenges": conf.challenges_count,
            "team_name": team.name,
            "college": team.college,
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

        prompt_id = session.prompt_ids[curr_idx - 1]
        server_now = datetime.utcnow()

        sub_id = str(uuid.uuid4())
        sub = ArenaSubmission(
            id=sub_id,
            team_id=team.id,
            prompt_bank_item_id=prompt_id,
            challenge_index=curr_idx,
            submitted_prompt=payload.prompt_text.strip(),
            server_timestamp=server_now,
            status="locked"
        )
        db.add(sub)
        db.flush()

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

        submissions = db.query(ArenaSubmission).order_by(ArenaSubmission.server_timestamp.desc()).all()
        sub_list = []
        for sub in submissions:
            t = sub.team
            p = sub.prompt_item
            eval_record = db.query(ArenaEvaluation).filter(
                ArenaEvaluation.submission_id == sub.id,
                ArenaEvaluation.judge_user_id == current_user.id
            ).first()

            sub_list.append({
                "id": sub.id,
                "team_id": sub.team_id,
                "team_name": t.name if t else "Unknown",
                "college": t.college if t else "N/A",
                "challenge_index": sub.challenge_index,
                "prompt_code": p.code if p else "P--",
                "prompt_title": p.title if p else "Flawed Prompt",
                "original_bad_prompt": p.original_bad_prompt if p else "",
                "bad_output_evidence": p.bad_output_evidence if p else "",
                "submitted_prompt": sub.submitted_prompt,
                "submitted_at": sub.server_timestamp.strftime("%H:%M:%S"),
                "has_evaluated": eval_record is not None,
                "evaluation": {
                    "clarity_score": eval_record.clarity_score,
                    "context_score": eval_record.context_score,
                    "specificity_score": eval_record.specificity_score,
                    "output_structure_score": eval_record.output_structure_score,
                    "relevance_score": eval_record.relevance_score,
                    "total_score": eval_record.total_score,
                    "judge_feedback": eval_record.judge_feedback
                } if eval_record else None
            })

        recent_events = db.query(ArenaSecurityEvent).order_by(ArenaSecurityEvent.created_at.desc()).limit(25).all()
        events_list = []
        for ev in recent_events:
            t = ev.team
            events_list.append({
                "id": ev.id,
                "team_name": t.name if t else "Unknown",
                "event_type": ev.event_type,
                "violation_count": ev.violation_count,
                "timestamp": ev.created_at.strftime("%H:%M:%S")
            })

        return {
            "status": conf.status,
            "is_results_released": getattr(conf, 'is_results_released', False),
            "started_at": conf.started_at.isoformat() if conf.started_at else None,
            "stats": {
                "total_teams": total_teams,
                "waiting_teams": max(waiting_count, 0),
                "active_teams": active_count,
                "completed_teams": completed_count,
                "flagged_teams": len(flagged_team_map)
            },
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
        evaluation.judge_feedback = payload.judge_feedback.strip() if payload.judge_feedback else ""

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
            "max_score": 50,
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

        teams = db.query(Team).all()
        eligible_standings = []
        eliminated_standings = []

        for t in teams:
            session = db.query(TeamArenaSession).filter(TeamArenaSession.team_id == t.id).first()
            submissions = db.query(ArenaSubmission).filter(ArenaSubmission.team_id == t.id).all()
            
            is_eliminated = (t.status == "eliminated" or (session and session.status == "eliminated"))

            total_score = 0.0
            for sub in submissions:
                evals = sub.evaluations
                if evals:
                    total_score += sum(e.total_score for e in evals) / len(evals)

            avg_score = round(total_score / 5.0, 2)
            completed_time = session.completed_at if session else None
            
            item = {
                "team_id": t.id,
                "team_name": t.name,
                "college": t.college or "N/A",
                "total_score": round(total_score, 1),
                "average_score": avg_score,
                "completed_challenges": len(submissions),
                "completed_at": completed_time.isoformat() if completed_time else None,
                "completed_at_sort": completed_time.timestamp() if completed_time else 9999999999,
                "is_eliminated": is_eliminated,
                "status": "eliminated" if is_eliminated else ("completed" if len(submissions) >= 5 else (t.status or "active"))
            }

            if is_eliminated:
                item["rank"] = None
                item["podium"] = None
                del item["completed_at_sort"]
                eliminated_standings.append(item)
            else:
                eligible_standings.append(item)

        # Authoritative Sorting: Average Score DESC, then Earliest Completion Timestamp ASC (tie-break)
        eligible_standings.sort(key=lambda x: (-x["total_score"], x["completed_at_sort"]))

        for idx, entry in enumerate(eligible_standings):
            entry["rank"] = idx + 1
            entry["podium"] = "winner" if idx == 0 else "runner_up" if idx == 1 else "second_runner_up" if idx == 2 else None
            del entry["completed_at_sort"]

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
            "results_released": conf.status == "results_available"
        }
