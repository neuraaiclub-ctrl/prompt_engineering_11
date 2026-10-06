import re
import os

service_path = "backend/app/services/arena_service.py"
with open(service_path, "r", encoding="utf-8") as f:
    orig_content = f.read()

archive_logic = """
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
"""

new_content = orig_content.replace('db.query(ArenaTestResult).delete(synchronize_session=False)', archive_logic.strip())

with open(service_path, "w", encoding="utf-8") as f:
    f.write(new_content)
    
print("Successfully patched arena_service.py")
