# Prompt Bank Dynamic Dataset Patch

## What Changes We Made
1. **Added Dataset Tagging Support**: We added the ability to tag question sets, allowing the platform to manage multiple distinct datasets instead of mixing all uploaded CSVs into one giant pool.
2. **Dynamic Active Dataset Selection**: We exposed an endpoint to change which dataset is actively being used for the current Arena session.
3. **Stratified Difficulty Assignment**: We updated the prompt assignment logic so that instead of picking 5 completely random prompts, it picks exactly 1 Easy, 3 Medium, and 1 Hard prompt per team.
4. **Preserved Existing Game Logic (Safe Upsert)**: We ensured that the CSV upload endpoint safely updates (upserts) existing questions rather than wiping the database.

## Why We Made Them
- **Preventing Workflow Breakages**: In the past, wiping or replacing the prompt bank caused active games to crash (throwing a 404 error) because ongoing team sessions lost references to their assigned prompt IDs, dropping them back to the "Standby" room. The safe upsert pattern and dataset tags prevent this.
- **Fairness in Competition**: Random sampling of 5 questions resulted in some teams receiving 5 hard questions while others received 5 easy ones. The new stratified assignment ensures every team faces the exact same difficulty profile.
- **Judge Panel Flexibility**: Judges needed the ability to upload a new CSV of questions for a specific round without polluting the default seeded bank. 

## How We Made Them (Modified Files)
1. `backend/app/models/arena.py`
   - Added `dataset_tag` column to `PromptBankItem` (default: "default").
   - Added `active_dataset_tag` column to `ArenaConfig` (default: "default").

2. `backend/app/schemas/arena.py`
   - Added `active_dataset_tag` to the `ArenaConfigUpdateRequest` schema.

3. `backend/app/api/prompt_bank.py`
   - Updated the `PromptBankItemSchema` and the `upload_csv` endpoint to parse and save the `dataset_tag` from the uploaded CSV.

4. `backend/app/api/arena.py`
   - Created a new `PUT /arena/config` endpoint to allow admins to dynamically update the active dataset tag.

5. `backend/app/services/arena_service.py`
   - Added the `update_config` method to handle saving the new config settings.
   - Refactored `assign_unique_prompts_for_team` to filter the prompt bank by the `active_dataset_tag` and explicitly sample 1 Easy, 3 Medium, and 1 Hard prompt.

6. `backend/migrate_db.py`
   - Created a migration script that successfully added the new columns to the live SQLite database without data loss.
