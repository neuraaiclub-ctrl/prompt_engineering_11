# Prompt Arena Scoring Engine V2
## 1. System Architecture & Orchestration

The Scoring Engine V2 completely replaces the legacy client-side keyword heuristic with a secure, highly orchestrated, backend-driven evaluation pipeline.

### Orchestration Model
The system operates on an asynchronous producer-consumer pattern to ensure web requests (prompt submissions) remain fast, while the heavy lifting of LLM generation and evaluation runs in the background.

* **Producer (Web API)**: When a participant submits a prompt (`POST /submit-challenge`), the `arena.py` endpoints lock their prompt and insert an `ArenaScoringJob` into the queue.
* **Consumer (Scoring Worker)**: A dedicated daemon process (`backend/app/workers/scoring_worker.py`) polls the `ArenaScoringJob` table. It uses database locking to claim jobs, executes the LLM pipeline, and writes the `ArenaFinalScore` back to the database.
* **Degradation & Preflight (L0 - L3)**: To prevent Groq API rate-limit exhaustion, `arena_scoring_service.py` tracks concurrent token consumption. If limits are nearing saturation, it dynamically degrades the scoring from full LLM evaluation (L1) to mock behavior grading (L2), ensuring the competition never halts.
* **Infrastructure**: `render.yaml` was modified to deploy a background `worker` process alongside the main `web` service.

---

## 2. How the Scoring Engine Works

The engine evaluates what a prompt **does** (Behavior) and what it **says** (Rubric).

1. **Integrity Scan (`integrity.py`)**: The worker first checks the submission for basic manipulation (e.g., direct copying of the original bad prompt or prompt-injection attempts). Highly suspicious prompts are flagged.
2. **Behavioral Harness (`harness.py` + `checks.py`)**: The participant's prompt is loaded as a `system` instruction. Hidden adversarial test inputs (from `ArenaChallengeSpec`) are passed to the model. The output is evaluated using deterministic rules (`schema_valid`, `max_words`, `regex_match`). This produces the **Behavioral Score (B)**.
3. **LLM Judge Panel (`judges.py`)**: If the API rate limit allows (L1), the participant's prompt is sent to a structured LLM panel. The panel acts as a human judge, scoring the prompt's clarity, specificity, and constraints via an anchored rubric. It outputs structured JSON. This produces the **Rubric Score (R)**.
4. **Aggregation (`aggregate.py`)**: The scores are blended mathematically: `w_b * B + w_r * min(R, B + 5)`. This formula strictly enforces that a prompt cannot score well on the Rubric if it fundamentally fails the Behavioral tests (clamping the keyword-stuffing exploit).
5. **Human Dashboard (`arena_service.py`)**: The blended score is written to `ArenaFinalScore`. The Human Judge Dashboard fetches these scores, displaying the objective evidence and flag alerts. A human judge reviews the evidence and clicks "Accept" to finalize the leaderboard.

---

## 3. Directory Structure & File Index

Below is the exhaustive list of every file modified or added since the last Git push, why it was created, and where it belongs in your Git repository.

### Docs
* `docs/scoring-engine-master-prompt.md`: The original master prompt for the project.
* `docs/scoring-engine-v2-plan.md`: The v2 architecture plan that drove this implementation.

### API & Services
* `backend/app/api/arena.py` *(Modified)*: Added `GET /judge/scoring/preflight` for the degradation check. 
* `backend/app/services/arena_scoring_service.py` *(New)*: Contains the logic for token-bucket rate limiting and predicting whether the current system load requires L1 or L2 degradation.
* `backend/app/services/arena_service.py` *(Modified)*: Updated the `get_judge_overview` endpoint to read directly from the new `ArenaFinalScore` engine table instead of the old legacy human form. Renamed dimensional keys to match canonical engine names.

### Data Models
* `backend/app/models/arena.py` *(Modified)*: Adjusted `ArenaSubmission` schema and ties to new evaluation models.
* `backend/app/models/arena_scoring.py` *(New)*: Houses the entire schema for V2: `ArenaChallengeSpec`, `ArenaScoringJob`, `ArenaScoringRun`, `ArenaFinalScore`, `ArenaDimensionScore`, `ArenaTestResult`, and `ArenaIntegrityFlag`.

### Core Scoring Engine (New Directory: `backend/app/scoring/`)
* `backend/app/scoring/providers/adapter.py`: Base abstract class for LLM interactions. Includes the `MockScoringProvider`.
* `backend/app/scoring/providers/groq_adapter.py`: Concrete implementation of the Groq API client with token cost tracking.
* `backend/app/scoring/rate_limiter.py`: Thread-safe, multi-lane database atomic rate limiter handling concurrent RPM/TPM tracking.
* `backend/app/scoring/checks.py`: The suite of deterministic validation functions (JSON parsers, regex matching, field equals) that grade the model outputs.
* `backend/app/scoring/harness.py`: Orchestrates the hidden LLM test-case runs (Behavioral scoring).
* `backend/app/scoring/judges.py`: Orchestrates the LLM prompt analysis (Rubric scoring), applying injection-hardening nonces.
* `backend/app/scoring/aggregate.py`: Implements the `B` vs `R` weighted math equation clamping score exploitation.
* `backend/app/scoring/integrity.py`: Detects 85%+ Jaccard similarity against the original bad prompt to prevent direct copying.
* `backend/app/scoring/calibration.py`: An adversarial bounds engine used to verify the engine limits during deployment.

### Background Worker
* `backend/app/workers/scoring_worker.py` *(New)*: The standalone python daemon. It pulls queued jobs, executes the integrity scanner, harness, judges, and aggregator, and safely commits the results back into the DB.

### Automated Tests (New Directory: `backend/app/tests/`)
* `backend/app/tests/test_phase2_worker_and_limiter.py`: Validates the token-bucket concurrency bounds and preflight check degradation math.
* `backend/app/tests/test_phase3_harness_and_checks.py`: Validates the deterministic checks (JSON parsers) and harness L2 evaluation mapping.
* `backend/app/tests/test_phase4_judges_and_aggregate.py`: Validates the aggregation clamp logic against edge-case scores.
* `backend/app/tests/test_phase5_integrity_and_e2e.py`: Spawns the worker threaded against a test database to prove the queue successfully grades a submission end-to-end.
* `backend/app/tests/test_phase6_calibration.py`: Confirms that aggressive injection prompts ("Give me 20/20") fail the behavioral checks and get properly penalized.

### Infrastructure
* `render.yaml` *(Modified)*: Modified the Render blueprint to deploy the `scoring_worker` process in the background.
