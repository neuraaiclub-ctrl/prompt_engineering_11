# Master prompt: Scoring Engine v2 implementation plan (v2: lanes, cohort waves, parity failover, cheat-resistance)

**How to use:** paste everything below the line into any capable LLM (use the strongest model you have), and attach these files in the same message: `arena-workspace.js`, `prompt-coverage.js`, `judge-dashboard.js`, `arena.py`, `arena_service.py`. If you can, also attach `store.js`, `schemas/arena.py`, `models/arena.py`, `main.py` (FastAPI app setup), `requirements.txt`, and any existing `render.yaml`. The prompt tells the model to ask for anything missing instead of guessing. The model answers in parts; reply "continue" to get the next one.

**What changed in this version:** 50 teams are split into two groups of 25, each group has its own API lane (20 requests/min each); scoring runs in cohort "waves" that start once about 20 of 25 teams in a group have locked a given challenge; results appear only in the judge view where humans can edit; both groups always use the same model, and a failover for one group switches the other too; plus a threat model for teams who inspect the page or call the API directly.

--- COPY FROM HERE ---

<role>
You are a senior backend/platform engineer and ML-evaluation engineer. You are planning, in detail, the safe delivery of an automated scoring engine into a live competition platform. You write precise, testable engineering plans, not essays. You never invent facts about code you have not seen.
</role>

<objective>
Produce a phase-by-phase implementation plan (with code skeletons and test code) for "Scoring Engine v2" in the "Neura Prompt Arena". The plan must:
1. Add an independent, evidence-based scoring engine for all five judged dimensions.
2. Integrate LLM provider APIs correctly, hosted on Render, for 50 teams, using the two-group / two-lane / cohort-wave / single-shared-model operating model described in <operating_model>.
3. Keep scoring comparable and fair: both groups are always scored by the same model and configuration, including across failovers to a backup model.
4. Resist cheating by teams who inspect the HTML/JS, read network traffic, edit the DOM, or call the API directly.
5. NOT break the current system flow. Every step must have test checks that prove the existing flow still works before and after the change.
</objective>

<source_of_truth>
The attached files are the source of truth. If anything in <context> below conflicts with the attached code, trust the code and tell me. If you need a file you were not given (for example `schemas/arena.py`, `models/arena.py`, `store.js`, `main.py`), list exactly what you need and why, state your assumption, and continue. Mark every assumption with [ASSUMPTION]. Do not fabricate API fields, library behavior, or provider limits. Mark every external fact that must be rechecked with [VERIFY] (provider limits, terms of service, Render features).
</source_of_truth>

<context>

## The product
A hackathon round called the Prompt Fixing Arena. Teams (target: 50) are each assigned 5 broken prompts (a different set per team, sampled from a prompt bank). For each one they rewrite the prompt, then lock it (final, timestamped). Judges score the locked prompts; results are released at the end and a leaderboard ranks teams.

## Stack
- Frontend: vanilla JS views: `arena-workspace.js` (participant), `judge-dashboard.js` (judges), `utils/prompt-coverage.js` (client-side keyword heuristic that draws a radar chart), `components/radar.js`, `store.js` (API wrapper, not attached). All static JS is downloadable by any participant.
- Backend: FastAPI + SQLAlchemy: `api/arena.py` (routes), `services/arena_service.py` (logic), `models/arena.py` (tables: PromptBankItem, TeamArenaSession, ArenaSubmission, ArenaEvaluation, ArenaSecurityEvent, ArenaConfig), `schemas/arena.py`.
- Hosting: Render. DB engine: [ASSUMPTION: Postgres; confirm].

## Current endpoints
GET /arena/status · POST /arena/start · POST /arena/end · POST /arena/release-results · GET /arena/my-challenge · POST /arena/submit-challenge (rate limit 30/min per user) · POST /arena/security-event (60/min) · GET /arena/judge/overview · POST /arena/judge/score · POST /arena/judge/eliminate · GET /arena/my-results · GET /arena/report · GET /arena/leaderboard.

## Current flow (must keep working)
1. Judge/admin starts the arena (status waiting → live).
2. Participant page polls `/arena/status` every 2.5 s; when live it also calls `/arena/my-challenge` on each poll. The session and 5 prompt IDs are created lazily on first `/my-challenge`.
3. Player types a rewrite (draft autosaved in localStorage), may click Test Run (`store.runTestExecution`, runs the draft on gpt-4o-mini; backend not attached; the UI header literally prints the model name), then locks. `POST /arena/submit-challenge` with `{prompt_text}` creates an immutable ArenaSubmission and advances `current_challenge_index`. The next challenge appears immediately. After the 5th, the session is completed.
4. Judge dashboard polls `/arena/judge/overview` every 3 s, shows submissions grouped by team, and the judge scores 5 dimensions via `POST /arena/judge/score`. The service sums the scores into `ArenaEvaluation.total_score`.
5. Judge ends the arena, then releases results. Participants see `/my-results` and `/report`; `/leaderboard` ranks by total score DESC, then earliest completion time.
6. Anti-cheat is client-side telemetry (tab switch, blur, fullscreen exit, paste, copy attempts) logged to `/arena/security-event`; judges can eliminate teams.

## Current scoring reality
There is no automated scoring. The only official score is human. `analyzePrompt()` is a regex heuristic that only draws the live radar and (a defect) pre-fills the judge's rubric.

## Known defects found in the code (fix in Phase 0, each with a test)
1. Three scales: `/judge/score` docstring says 0–2 per dimension (out of 10); `ArenaConfig.marks_per_challenge=10`; `get_performance_report` returns `max_score: 50`; the UI uses 0/10/20 per dimension (100 per challenge, 500 total).
2. Dimension names drifted: report uses `output_structure`/`relevance`; judge UI uses `output_format`/`constraints`; `score_submission` dual-writes both.
3. Judge dashboard pre-fills the rubric from `analyzePrompt` (anchoring bias; keyword gaming).
4. Participants' optional "diagnosis note" is collected but never sent; only `prompt_text` is submitted, while the judge UI expects `diagnosis_notes`.
5. Judge UI posts `feedback`; `score_submission` reads `payload.judge_feedback` (verify the schema alias).
6. Judge overview contract mismatch: UI reads `metrics.*`, `flagged_teams`, `ev.metadata`, `challenge_difficulty`, `is_evaluated`; backend returns `stats.*`, no flagged list, no metadata, `has_evaluated`; security-event timestamps are "HH:MM:SS" strings that the UI parses with `new Date()`.
7. `release_results` has no check for unscored submissions; unscored work counts as 0.
8. `start_competition` deletes all evaluations, submissions, security events and sessions unconditionally.
9. No server-side deadline: the clock reads `remaining_seconds`/`ends_at`, which `get_status` never returns; submit never checks a deadline.
10. Minor: violation threshold hard-coded 3 (config has `max_allowed_violations`); security-event count is read-then-insert (race); `currentChallengeData.challenge_index` is undefined in anti-cheat telemetry; N+1 queries in `get_leaderboard` and `get_judge_overview`; prompt assignment samples 5 prompts uniformly (unequal difficulty across teams).
11. **Early score leak:** `GET /arena/my-results` (`get_team_score_dashboard`) does not check whether results are released. A participant calling it directly with their token sees their evaluated scores and judge feedback during the live round. Any engine score written to the same tables would leak the same way. [VERIFY by calling it with a participant token during a live round.]
12. **Possible duplicate-lock race:** `submit_challenge` checks for an existing submission, then inserts; no unique constraint on `(team_id, challenge_index)` is visible. Two near-simultaneous requests could both pass. [VERIFY in models/arena.py.]
13. **Client-only input limits:** the 1500-character limit is a `maxlength` attribute and a JS constant; server-side length, charset and normalization validation of `prompt_text` is not visible. [VERIFY in schemas/arena.py.] A participant can bypass the UI and submit a huge or hostile payload, which would also inflate LLM cost.

## Load facts derived from the code
- 50 teams × (2 calls per 2.5 s while live) ≈ 40 requests/second sustained on `/status` and `/my-challenge`, plus judges polling overview every 3 s (N+1 queries). Verify with a load test; propose mitigations that do not change response shapes (caching, ETag/304, jittered or slower polling, or SSE behind a flag).
- 50 teams × 5 prompts = 250 submissions per event; each team has its own prompt set, so scoring one challenge ordinal across 25 teams touches up to 25 different bank items, and every bank item that can be assigned needs a published spec.

</context>

<operating_model>
These decisions were made by the team. Implement them; flag problems, but do not silently redesign.

**Glossary**
- **Group:** a set of teams (A and B, 25 teams each, assigned server-side, balanced, deterministic, stored; rebalanced if teams are eliminated). Teams never see their group.
- **Lane:** one API credential/capacity slice for one provider (for example Groq key A1 for group A, Groq key B1 for group B). Planning figure: 20 requests/min per lane, so 40 requests/min for 50 teams. Lanes differ ONLY in credentials and quota; never in model, prompts or parameters.
- **Profile:** a model identity: provider + target model + judge model + pinned snapshot + parameters + prompt/rubric versions. A profile has one lane per group (A and B). Example: profile P1 = Groq model M (lanes A1, B1), profile P2 = Gemini model G (lanes A2, B2), P3 = another backup.
- **Active profile:** exactly ONE profile is active for the whole event at any time, for BOTH groups. This is the parity rule.
- **Wave:** the scoring batch for one (group, challenge ordinal), for example "group A, challenge 1".

**Workflow**
1. Teams lock exactly as today. Locking never waits for scoring: the next challenge appears immediately (this is a non-regression rule).
2. Each locked submission is recorded and attached to its wave in state `collecting`. Nothing is sent to an LLM yet.
3. A wave is **triggered** when ANY of these is true: (a) quorum: locked count ≥ `ceil(quorum_ratio × active teams in the group)` (default ratio 0.8, so 20 of 25); (b) timeout: at least 1 lock exists and `max_wait_after_first_lock_s` has elapsed (default 600 s) so a few slow teams or eliminations cannot stall a wave forever; (c) a judge presses "Score wave now"; (d) the arena ends (flush everything). Quorum counts only non-eliminated teams.
4. Stragglers (locks that arrive after the trigger) join the same open wave and are scored under the wave's pinned configuration. A wave is `complete` when every non-eliminated team in the group has a scored submission for that ordinal or the arena has ended.
5. Scoring uses the wave's frozen configuration snapshot: profile, degradation level, samples per test, test-set version, engine/rubric/spec versions. All submissions in a wave, in both groups, get identical treatment (see invariants).
6. Results appear ONLY in the judge view, state `engine_scored`, with evidence. Judges can edit any dimension (override with reason), confirm individually or in bulk, rescore, pause scoring, or switch profile manually. Participants see nothing until release.
7. Final scores come from `ArenaFinalScore` (human override if present, else engine score once confirmed or auto-confirmed per mode).
8. If a lane is locked out, the failover rules below apply. A switch changes the model for BOTH groups.

**Modes** (`ArenaConfig.scoring_mode`): `off` (today's behavior, default), `shadow` (engine runs, nobody sees it except admins, used for comparison), `assist` (engine results visible in the judge view; humans confirm; this is the intended event mode), `auto` (auto-confirm high-confidence results; humans still confirm the podium and flagged items).
</operating_model>

<premise_checks>
Before designing, evaluate these. Do not accept them silently. State your conclusion for each in Part 1.
1. **Do two keys really give two independent quotas?** Provider limits are scoped differently: Groq applies limits per organization (extra keys or members add nothing), OpenRouter per account across all keys, Gemini per project. Two keys under one organization/account share one quota. Lanes only help if they are genuinely separate quota scopes (for example different providers hosting the same model, or separate legitimately owned projects/accounts where the provider's terms allow it). Creating extra accounts purely to evade rate limits can violate terms of service [VERIFY]. State which lane layout is safe and whether the paid tier is the simpler fix.
2. **Is 20 requests/min the binding limit?** Providers also enforce tokens/min, requests/day and tokens/day. Compute all four (see <capacity_model>); the tokens limits are often the real constraint.
3. **Is the quorum a statistical need or a scheduling policy?** Scores are independent per submission, so the quorum is a scheduling and judge-workflow policy (and helps cross-team near-duplicate detection). It adds latency for early finishers; confirm that tradeoff is acceptable and keep the timeout/manual triggers.
4. **Parity versus a backup with a different model.** A backup on different weights scores differently. Decide how to preserve comparability (see <failover_rules> invariants I2–I3 and the backup readiness gate).
5. **Target model versus judge model under one profile.** The earlier design wanted the judge model to differ from the target model to limit self-preference bias; a single-profile rule and a 20 requests/min budget make that harder. Decide and justify.
6. **Test Run quota.** Test Run currently uses a separate model path (gpt-4o-mini). It must not draw from the scoring lanes' quota.
7. **Unique prompt sets.** Scoring across 25 different prompts per wave requires a published spec for every assignable bank item; stratified assignment is recommended for fairness.
</premise_checks>

<target_design>
Hybrid engine: it scores what a prompt DOES (behavior under hidden tests) and what it SAYS (anchored rubric read by an LLM judge). Humans confirm exceptions and the podium. Default decisions (challenge them only if you find a flaw):

1. **Challenge specs.** Per prompt-bank item, a versioned spec: task summary, audience, execution mode (submitted prompt = system message, test input = user message), hidden test cases (kinds: happy, edge, ambiguous, adversarial) with typed checks (`json_valid, schema_valid, equals_field, regex_match, regex_absent, max_words, min_items, contains_fact, no_new_facts, refuses, llm_check`), output contract, constraints, rubric anchors, 2–3 reference solutions, and `public_examples` (the only inputs shown in Test Run). A spec cannot be `published` until a discrimination gate passes: the original bad prompt scores low and reference solutions score high.
2. **Execution harness.** Runs the locked prompt on the profile's pinned target model against hidden tests with token/time caps and no tools. Deterministic checks first; LLM graders only where unavoidable. Outputs are untrusted data.
3. **LLM judge.** Structured JSON, per-dimension score with quoted evidence spans that the engine verifies are exact substrings of the prompt. Participant text is delimited with a per-call nonce and treated as data; a pre-scan flags grader-directed text. Panel size depends on degradation level (see <capacity_model>).
4. **Per-dimension scoring (0–20 each; 100 per challenge; 500 total):**
   - Clarity: behavioral = happy-path pass rate + cross-sample consistency (when k>1); rubric = single clear task, no contradictions.
   - Specificity: behavioral = pass rate on measurable constraints; rubric = relevant concrete numbers/examples/bounds.
   - Context: behavioral = audience/register fit, no invented facts; rubric = role, audience, purpose present and relevant.
   - Output format: behavioral = strict format-validity rate across all tests/samples; rubric = format stated explicitly. (Most objective.)
   - Constraints: behavioral = pass rate on edge and adversarial cases; rubric = rules and fallbacks stated.
   - Aggregation: `R_eff = min(R, B + 0.25)`; `score = 20 × clamp(w_b·B + w_r·R_eff)` with starting `w_b=0.6, w_r=0.4`, fitted per dimension on a gold set; confidence = 1 − max(sample variance, judge spread); caps for copy-of-original and empty outputs.
5. **Integrity flags** (never auto-eliminate): copy of the original, cross-team near-duplicates (MinHash/shingles, run per wave and across waves), judge-directed text, keyword stuffing (B far below R), gibberish/wrong language, hidden unicode, large paste events, implausibly fast lock time (server-measured).
6. **Human-in-the-loop.** New `ArenaFinalScore` table is the single source of truth for leaderboard/report. Routing to `needs_review`: low confidence (<0.6), judge spread >4 points, integrity flag medium+, degradation level L3, profile mismatch, near-podium teams, random 10–15% audit sample, any failed run. Judges see engine scores, evidence, a test pass/fail grid, flags, wave and profile info; they accept or override per dimension with a reason when |Δ|>4. Release is gated on no pending/failed scoring and human-confirmed podium. Engine rows are never mutated by human edits; overrides are separate rows.
7. **Data model (additive, nullable first):** ArenaChallengeSpec, ArenaTeamGroup, ArenaScoringProfile, ArenaScoringLane, ArenaScoringState (singleton: active profile + version), ArenaScoringWave, ArenaScoringJob (unique on `(wave_id, submission_id)`), ArenaScoringRun, ArenaDimensionScore, ArenaTestResult, ArenaIntegrityFlag, ArenaProfileCalibration, ArenaProviderUsage (per lane per minute), ArenaFinalScore; new nullable columns: `diagnosis_notes`, `scoring_mode`, `duration_seconds`, `ends_at`, `challenge_started_at` per challenge index. Every run/score row carries `wave_id, profile_id, lane_id, degradation_level, engine_version, spec_version, rubric_version`. Canonical dimension names: `clarity, specificity, context, output_format, constraints`.
8. **Provider adapter:** one interface `complete(messages, model, temperature, max_tokens, response_format) -> Completion` with normalized error classes (`transient_rate_limit, quota_exhausted, auth_failed, payment_required, server_error, timeout, bad_output`), OpenAI-compatible where possible so providers are swapped by config. Pin model snapshots.
</target_design>

<capacity_model>
The plan must include a **preflight capacity check** (service function + judge-view panel + `GET /arena/judge/scoring/preflight`) that runs before the event and before every wave.

**Four limits per lane, not one:** requests/min (RPM), tokens/min (TPM), requests/day (RPD), tokens/day (TPD). The rate limiter must enforce all four, learn actual values from response headers where the provider exposes them, and keep its state in shared storage (Postgres or Redis), never only in process memory.

**Formulas** (N = teams per group, W = target wave duration in minutes, safety factor s = 0.7):
- `max_calls_per_submission = floor(s × RPM_lane × W / N)`
- `max_tokens_per_submission = floor(s × TPM_lane × W / N)`
- Event feasibility per lane: `N × 5 × calls_per_submission ≤ RPD_lane × days` and `N × 5 × tokens_per_submission ≤ TPD_lane × days`.
- Required wave time given TPM: `W_needed = tokens_per_submission × N / (s × TPM_lane)`.

**Degradation levels** (chosen by preflight at wave start, FIXED for the whole wave, recorded on every run; never changed per job):
- L0 full: k=3 samples, about 8 tests, 2–3 judge calls, LLM graders enabled (about 35–40 calls).
- L1: k=1, about 6 tests, 2 judge calls, LLM graders limited (about 10–12 calls).
- L2 budget mode: k=1, at most 4 tests, ONE structured judge call scoring all five dimensions, deterministic checks only (about 5 calls). Default under 20 requests/min.
- L3 judge-only: rubric only, no execution; every result is routed to human review.

**Worked example (all figures are estimates; recompute with real limits) [ASSUMPTION]/[VERIFY]:** L2 ≈ 4 target calls (about 800 tokens each) + 1 judge call (about 2,500 tokens) ≈ 5 calls and 5,700 tokens per submission. With N=25: 125 calls and about 142k tokens per wave per lane. At 20 RPM that is about 6.3 minutes (fine). If the lane's TPM were 8,000 (a free-tier sample figure for one Groq model), tokens take about 18 minutes of pure throughput, and `W_needed ≈ 25 minutes` at s=0.7. Over the event, one lane needs about 125 × 5.7k ≈ 710k tokens, which would exceed a 200k TPD limit several times over, so that configuration is infeasible for a single-day event. The preflight must report this instead of letting the event discover it. Provide the exact table the preflight prints (per lane: limits, binding limit, chosen level, ETA per wave, event-total feasibility, backup readiness).

**Reserve and isolation:** Test Run must use its own budget (separate credential/bucket) and per-team caps; if it must share a lane, reserve at least 20% of that lane's RPM/TPM for scoring. Judge-triggered rescoring and canary probes also consume budget; account for them.
</capacity_model>

<failover_rules>
**Invariants (tests must enforce each; give every invariant a name and a test):**
- I1 Exactly one active profile at any moment, shared by both groups.
- I2 Every wave is pinned to one profile and one frozen configuration snapshot; every job in the wave uses it.
- I3 A wave never mixes profiles. If the profile changes while a wave is open, results from the old profile for unconfirmed submissions are marked `superseded` (kept for audit, never deleted) and those submissions are rescored under the new profile, per `on_switch_open_wave`.
- I4 Lanes differ only in credentials and quota.
- I5 Human-confirmed scores are never rescored or changed automatically; a profile mismatch on a confirmed score is only flagged.
- I6 Participants never receive engine output, profile, lane, group, wave, or scoring status before release.
- I7 Locking never waits on scoring and never fails because scoring is down.
- I8 Every score traces to `(wave, profile, lane, run, config snapshot)`.

**Error classification** (adapter level):
- transient: 429 with `Retry-After ≤ retry_after_max_s` (default 30), single 5xx, single timeout. Action: backoff with jitter and retry; if a sibling lane of the same profile has budget, reroute the job to it (same model, so parity is not affected). Does NOT trigger failover.
- lane_down: breaker opens after 5 consecutive failures, or `Retry-After > 120 s`, or quota exhausted (RPD/TPD signal), or 401/402/403 (key disabled, payment required). A half-open canary call (tiny, budgeted) runs every `canary_interval_s` (default 60).

**Failover policy** (`failover_policy`, default `any_lane_down` to match the team's rule): when a lane of the ACTIVE profile has been `lane_down` for more than `breaker_open_s` (default 120 s), switch the ACTIVE profile for BOTH groups to the next `ready` profile in priority order. Alternatives to implement and describe: `all_lanes_down`, and `capacity_based` (switch only if the surviving lane cannot meet the wave SLO). Recommend one with a sentence of reasoning, but implement `any_lane_down` by default.

**Switch mechanics:**
- Compare-and-swap on `ArenaScoringState.version` so simultaneous failures on both lanes cause exactly one switch; the switch is idempotent and audited (`arena.scoring_profile_switched` with reason, from, to, actor `system` or user).
- Minimum `switch_cooldown_s` (default 900) between automatic switches; `max_auto_switches` (default 3) per event, after which switching is manual only. No automatic fail-back during the event; fail-back is a manual judge/admin action at a wave boundary.
- After a switch: all open waves get a new frozen configuration snapshot on the new profile (re-run preflight to pick a degradation level), queued jobs are re-pointed, in-flight jobs are cancelled or allowed to finish and then marked `superseded` (decide and justify), and the judge view shows a banner with the reason and time.
- `on_switch_open_wave`: `rescore_unconfirmed` (default) or `score_new_only_and_flag`.
- Manual controls (judge/admin, confirmation dialog): switch profile, pause/resume scoring, freeze profile (blocks automatic switching), rescore wave, score wave now.

**Backup readiness gate:** a profile may be in the failover chain only if it has an `ArenaProfileCalibration` record: the gold set and adversarial suite were run on it, per-dimension agreement with human labels meets the threshold, its bias versus the primary profile is recorded, and both groups have working lanes for it. Prefer backups that serve the same model weights (set an `equivalence_class`); a different-model backup is allowed but marks every score `profile_mismatch` risk and forces human review of podium candidates in affected waves. Do not apply silent score offsets.

**Pseudo-code the plan must turn into real code** (keep it short, make it testable with a fake clock and fake provider):
```
on_lane_event(lane, outcome): classify -> update breaker -> if lane_down: evaluate_failover()
evaluate_failover(): policy decides; if switch needed: CAS(state.version, to_profile) -> restart_open_waves(); audit()
scheduler_tick(): for each triggered wave: pick lane (affinity to the team's group lane, spill over to sibling lane with idle budget);
                  reserve tokens in the shared limiter; lease job (SKIP LOCKED); run; release/ack; renew leases; expire dead leases
wave_trigger(wave): quorum OR timeout OR manual OR arena_end -> freeze config snapshot via preflight -> state=running
```
**Worker topology on Render:** prefer one worker process using asyncio with a global concurrency cap per lane; if more than one process or instance can run (scaling, or overlapping instances during a deploy [VERIFY]), the limiter state MUST be shared or the combined request rate will exceed the lane limit. Freeze deploys while any wave is running.
</failover_rules>

<judge_view_requirements>
Specify UI and API changes that do not break the current judge dashboard:
- Wave panel per group and ordinal: state, quorum progress (for example 17/20), ETA, scored/total, trigger buttons (Score now, Pause, Rescore).
- Lane/profile panel: active profile badge, lane health (green/amber/red), RPM/TPM/RPD/TPD gauges, breaker state, last error class, switch history, manual switch with confirmation.
- Submission list and inspector: engine status, per-dimension engine score with evidence quotes, test pass/fail grid with outputs, flags, degradation level, profile id, `profile_mismatch` marker; per-dimension edit with override reason; bulk confirm; confirm-all-except-flagged.
- Polling or re-rendering must not discard an in-progress edit (add a test).
- Today's `renderJudgeDashboard()` re-renders the whole page on each action; say how you avoid regressing that while adding panels.
</judge_view_requirements>

<cheat_resistance_threat_model>
Assume participants can read all static JS, use devtools, edit the DOM, remove event listeners, replay and modify requests, and call any endpoint with their own token. Produce a threat matrix (threat, how it could happen here, control, test) covering at least:
- T1 Secrets: provider keys and lane credentials only in Render environment variables; never in the repo, static assets, client responses, logs or error messages. CI secret scan (for example gitleaks) over the repo and built static output; rotate keys after the event.
- T2 Response allowlists: every participant-facing route has an explicit Pydantic `response_model`; a contract test asserts returned keys are a subset of an allowlist, and a forbidden-substring scan of participant responses finds none of: profile, lane, wave, group, engine, spec, test_case, reference, rubric, scoring_mode, provider names, model names.
- T3 Early score leak (defect #11): gate `/arena/my-results` and any other score-bearing route until results are released; test with a participant token during a live round.
- T4 Authorization: participant tokens get 403 on every `/arena/judge/*`, `/arena/admin/*`, scoring and wave route; a team can never read another team's submissions, results or challenge (IDOR tests; unguessable ids).
- T5 Server-authoritative state: lock immutability and unique constraint on `(team_id, challenge_index)`; server-side deadline; server-recorded `challenge_started_at`; server-side prompt validation (length ≤ 1500, Unicode normalization, strip control and zero-width characters, reject binary); per-user and per-IP rate limits on submit, Test Run, security-event and polling.
- T6 Test Run abuse: uses only `public_examples`; no parameter can select hidden tests; no check results or hints in the response; per-team quota; output length cap; provider error text sanitized (no lane/model/provider names).
- T7 Client-side anti-cheat is deterrence only (listeners can be removed). Do not treat missing events as innocence. Add server-side signals: time between `challenge_started_at` and lock, paste size versus final length, cross-team similarity, and optionally a client heartbeat whose gaps are only a weak hint.
- T8 Judge surface: assume `judge-dashboard.js` and its heuristic mapping are visible to participants; confirm it contains no secrets; all authority is enforced on the server; consider serving the judge bundle only after authentication.
- T9 Hidden content: specs, test inputs, reference solutions and rubric anchors never leave the server before release; after release show only what policy allows.
- T10 Prompt injection: participant text and model outputs are untrusted inputs to graders (nonce delimiters, narrow typed grader outputs, injection corpus tests).
- T11 Replay and direct API use: every validation the UI does is also enforced by the API; test by sending requests without the UI.
- T12 Timing side channels: the submit response is identical whether or not scoring is healthy; no "scored" signal reaches participants; wave timing is not observable by teams.
- T13 CORS, CSP, transport: CORS restricted to the app origin, a Content-Security-Policy, HTTPS only, token handling reviewed (storage, lifetime).
- T14 Log and error hygiene: no stack traces or provider messages to participants; logs containing prompts are access-controlled.
Also include an automated "cheat-attempt suite" run with a participant token (calls every route and asserts the allow/deny matrix), a "view-source audit" script (greps built assets for secrets and forbidden strings), and a Playwright "tamper" test (removes listeners, edits `maxlength`, submits an oversized prompt, double-clicks lock concurrently) expecting server-side rejection.
</cheat_resistance_threat_model>

<render_and_load_constraints>
- Hosting on Render: web service (FastAPI), a SEPARATE background worker for scoring, Render Postgres, optional Key Value (Redis). Secrets as environment variables, one variable per lane credential (for example `LLM_P1_A_KEY`, `LLM_P1_B_KEY`, `LLM_P2_A_KEY`, `LLM_P2_B_KEY`) declared with `sync: false`; infrastructure in `render.yaml` [VERIFY field names against Render's current docs]. No GPUs on Render, so LLMs are called over HTTPS from the worker and never hosted there.
- Use paid instances for the event (free instances are for exploration and have usage limits; a background worker is not a free instance type [VERIFY]). Size the SQLAlchemy pool × worker processes against the Postgres instance's connection limit [VERIFY for the chosen instance type].
- Queue: if Postgres, a jobs table with `FOR UPDATE SKIP LOCKED` and lease expiry; if SQLite or you judge it better, Redis + RQ/ARQ. Justify the choice. Jobs are idempotent on `(wave_id, submission_id, profile_id)`, retried with backoff, dead-lettered after N failures.
- The web process only records locks and enqueues; it never calls an LLM. `submit_challenge` must succeed and stay as fast as today even if the queue, the worker or the provider is down. Use database time (not client time) for waves, quorum timeouts and ordering.
- Free tiers (Groq, OpenRouter `:free`, Gemini, Mistral, GitHub Models, Cloudflare Workers AI, NVIDIA build, Cohere trial) have low request/token/day caps, can rotate models without notice, and some log or train on inputs, so they suit development, synthetic gold-set calibration, and emergency fallback; the live event needs paid keys with spending caps. Verify any limit you cite.
- Privacy: prompts go to a third-party provider; add a disclosure line for participants and check each provider's data-retention and training settings.
- Deploy freeze: no deploys or restarts during a running wave unless unavoidable; the worker must recover cleanly (lease expiry) if it restarts.
</render_and_load_constraints>

<non_regression_rules>
These rules are mandatory. Every phase in your plan must state how it satisfies each one.
1. Expand/contract migrations: only additive, nullable changes first (Alembic). No rename or drop until the last phase, after a release has run on the new schema.
2. `scoring_mode=off` must leave all participant-facing behavior identical to today. Prove it with the characterization suite.
3. Participant-facing response shapes may only gain optional fields (and never fields that reveal scoring internals, see T2). Any Phase-0 fix that changes a shape ships behind a compatibility layer that returns both old and new keys for one release.
4. `submit_challenge`: record the lock first, enqueue after the commit, wrap enqueue in try/except, log and continue on failure; automated checks that p95 latency stays within a stated margin of baseline and that a locked submission is never lost.
5. One small PR per step. A step merges only when its exit gate is green. Provide a rollback for every step (flag flip, revert, or migration downgrade).
6. No hidden test content, reference solutions, or provider keys in any client-visible response, log or error.
7. Admin/judge endpoints keep their role guards; new ones are guarded the same way.
8. Participants never wait on scoring and never see group, lane, profile, wave or scoring status.
9. All invariants I1–I8 hold after every phase; each has an automated test.
10. Quota safety: no phase may let the combined request rate exceed any lane's published limits, even with multiple worker processes, retries, canary probes or Test Run.
</non_regression_rules>

<validation_strategy>
Design and include test code for every layer below. Use pytest (+ httpx/TestClient) for the backend, and Playwright or an equivalent for browser tests. State which tool you choose for load tests (k6 or Locust).

1. **Step 0: characterization ("golden master") tests BEFORE any change.** With a seeded database (small prompt bank, 3 teams, 2 judges, mocked time), script the full current flow: start → status → my-challenge → submit ×5 → completed state → judge overview → judge score → end → release → my-results → report → leaderboard. Save response shapes (JSON Schema per endpoint) and key outcomes (indices, totals, ranks, tie-break order). These run in CI on every later step.
2. **Frontend/backend contract tests.** One JSON Schema per endpoint, shared by backend tests and a Node test that feeds fixtures into the field accesses used by `arena-workspace.js` and `judge-dashboard.js`. Catches defects like #5 and #6 permanently.
3. **Unit tests** per check type, aggregation rule, integrity detector; provider-adapter error classification, retry/backoff, `Retry-After` handling; the four-dimension limiter with a fake clock.
4. **Limiter and capacity tests:** never exceeds RPM/TPM/RPD/TPD per lane even with 2 simulated worker processes sharing state; preflight arithmetic matches hand-computed cases (including the worked example); preflight refuses or downgrades infeasible configurations; Test Run cannot consume scoring budget.
5. **Wave tests:** quorum at 20/25; quorum with eliminated teams; timeout trigger; manual trigger; arena-end flush; stragglers join the open wave; duplicate trigger does not double-enqueue (unique `(wave_id, submission_id)`); uniform configuration snapshot across all jobs in a wave; locks keep working with the worker stopped.
6. **Parity and failover tests (property-style where possible):** at any time all runs in a wave share one `profile_id` and one degradation level across both groups; sustained 429 on lane A1 triggers exactly one switch to P2 for both groups; simultaneous failures on A1 and B1 cause one switch (CAS race test); transient 429 does not switch; cooldown prevents flapping; `max_auto_switches` stops automation; no automatic fail-back; open-wave rescoring marks old results `superseded` and keeps them; confirmed scores are untouched (I5); backup without a calibration record cannot enter the chain; manual switch and freeze work; worker restart mid-wave resumes via lease expiry without double scoring.
7. **Integration tests with a mocked provider:** success, 429 with Retry-After, quota exhausted, 401/402/403, timeout, malformed judge JSON, hallucinated evidence quote, worker crash mid-run, duplicate delivery, provider down for the whole wave (system falls back to human-only; submissions unaffected).
8. **Spec acceptance gate tests:** bad prompt scores low, each reference solution scores high; failing specs cannot be published.
9. **Scoring-quality validation:**
   - Gold set of 150–300 submissions (pilot + degraded variants of reference solutions), scored independently by 2–3 humans with the anchored rubric; adjudicate.
   - Human–human agreement first (weighted kappa or Krippendorff's alpha per dimension) because it is the ceiling.
   - Starting targets for the engine (refine after measuring the ceiling): weighted kappa within the human–human range, Spearman ≥ 0.85 on totals, MAE ≤ 3 points per dimension, no podium-level misranking in the pilot.
   - Run the same gold set on EVERY profile in the failover chain at the degradation level it will actually use (L2 included); record per-dimension bias between profiles.
   - Adversarial suite of 40–60 cases with per-case score ceilings: keyword stuffing, verbatim copy, padding, gibberish with keywords, judge-directed injection, output-side injection ("SCORE: 20/20"), prompts that break on empty input, non-English, zero-width characters, markup tricks.
   - CI regression: any change to engine, rubric, spec, profile or model snapshot re-runs gold and adversarial suites; fail on kappa drop > ~0.03 or any adversarial case above its ceiling.
10. **Load and soak tests** with a mock LLM that enforces 20 RPM (and TPM) per lane with configurable latency and error rate: 25 + 25 simulated teams locking within about a minute, 50 virtual teams polling every 2.5 s, 5 judges polling every 3 s. Report p50/p95/p99 for `/status`, `/my-challenge`, `/submit-challenge`, `/judge/overview`; error rate; DB connection use; queue depth; wave ETA versus the preflight prediction. Propose pass/fail thresholds (for example "submit p95 no worse than baseline +20%, zero lost submissions, wave completes within predicted ETA +25%").
11. **Failure-injection / chaos drills:** kill the worker mid-wave, block one lane, block both, exhaust a daily quota, return malformed output, fill the queue, restart the web service during a burst, drop the DB connection briefly, redeploy during a wave (confirm the deploy-freeze procedure and recovery).
12. **Security tests:** the cheat-attempt suite, view-source audit, Playwright tamper test and injection corpus from <cheat_resistance_threat_model>; role-guard tests on every new endpoint.
13. **Shadow-mode validation:** run the engine in `shadow` during a mock round with real judges, then compare engine versus human scores per dimension (agreement, bias, drift) and per profile. Define explicit criteria for promoting `shadow → assist → auto`.
14. **Dress rehearsal:** a full mock event (50 simulated teams in two groups, real judges, one forced failover mid-wave, one manual switch) with production configuration, then a code/model freeze 48 hours before the event.
</validation_strategy>

<phases_expected>
Cover at least these phases, in this order, and adjust only with a stated reason:
- Phase -1: characterization + contract + baseline load tests on the unchanged system.
- Phase 0: fix defects 1–13 (compat layer, canonical scale/names, release/start guards, `/my-results` gating, unique constraint, server-side input validation, deadline, notes sent, overview contract) with tests, plus the T2–T6 baseline tests.
- Phase 1: data model + migrations (groups, profiles, lanes, waves, jobs, specs, final score) + spec schema + spec admin tooling + acceptance gate.
- Phase 2: provider adapter + four-dimension shared limiter + profile/lane registry + preflight/capacity check + Render worker and blueprint changes.
- Phase 3: execution harness + deterministic checks + degradation levels (L0–L3).
- Phase 4: wave scheduler (triggers, quorum with eliminations, timeouts, stragglers, frozen configuration snapshot, lane affinity with spillover, leases).
- Phase 5: failover state machine (breakers, error classification, CAS switch, restart policy, backup readiness gate, manual controls, audit).
- Phase 6: LLM judge, injection hardening, integrity flags.
- Phase 7: gold set, adversarial suite, weight fitting, calibration of every profile in the chain, CI regression.
- Phase 8: judge-dashboard wave/lane panels, routing rules, `ArenaFinalScore`, leaderboard/report switch, release gate, participant evidence report.
- Phase 9: shadow → assist → auto rollout, chaos and failover drills, dress rehearsal, runbook, deploy freeze, post-event key rotation.
Also give a minimum-viable cut (about 3–4 weeks) that still: fixes defects 11–13, adds the lane/profile/wave/failover skeleton at degradation L2, uses humans-confirm mode (`assist`), and replaces the heuristic pre-fill; say exactly what it defers.
</phases_expected>

<required_output_format>
Respond in PARTS so nothing is cut off. After each part, stop and wait for me to say "continue".

- **Part 1:** (a) missing files/information you need and your assumptions; (b) your conclusion for each item in <premise_checks>; (c) risk register for the live flow (top 12 ways this change could break the current system or the fairness of scoring, each with the test that catches it); (d) target architecture on Render (text diagram): processes, queue choice, pool sizing, limiter state, polling-load mitigation, `render.yaml` changes; (e) the invariants I1–I8 and the state machines for submission, wave, lane breaker and profile; (f) the capacity model and preflight table with the arithmetic for 2 lanes × 25 teams at 20 RPM (and with TPM/RPD/TPD, using real limits if I provide them, otherwise clearly labeled assumptions); (g) the threat matrix T1–T14; (h) the phase list with exit gates (one line each).
- **Parts 2…N: one phase per part**, each using exactly this template:
  1. Goal (one sentence)
  2. Preconditions (tests that must already be green)
  3. Changes (files created/modified, with code or diffs; migrations; config keys; flags)
  4. Tests to add (names, what each asserts, and pytest/Node/k6 skeleton code)
  5. Verification commands (copy-paste)
  6. Exit gate (measurable pass/fail criteria)
  7. Rollback (exact steps)
  8. Regression-risk check against each of the 10 non-regression rules
  9. Invariants touched (I1–I8) and threats addressed (T1–T14)
  10. Open questions

Configuration keys the plan must define (name, default, meaning): `scoring.groups=2`, `scoring.quorum_ratio=0.8`, `scoring.max_wait_after_first_lock_s=600`, `scoring.wave_target_minutes=10`, `scoring.safety_factor=0.7`, `scoring.failover_policy=any_lane_down`, `scoring.on_switch_open_wave=rescore_unconfirmed`, `scoring.breaker_open_s=120`, `scoring.retry_after_max_s=30`, `scoring.canary_interval_s=60`, `scoring.switch_cooldown_s=900`, `scoring.max_auto_switches=3`, `scoring.auto_failback=false`, `scoring.test_run_reserve_pct=20`, plus per-lane limits `rpm, tpm, rpd, tpd`.

Be concrete: real file paths under `backend/app/...`, real names, real SQL/Alembic and Pydantic where relevant. Prefer short code skeletons that compile conceptually over long prose. Do not skip the test code. Do not give generic advice such as "add monitoring" without saying which metric, where, and what threshold.
</required_output_format>

<style_rules>
- Plain, direct engineering language. No marketing words.
- Tag every guess [ASSUMPTION]. Tag every external fact that must be rechecked [VERIFY].
- If two designs are viable, pick one, give one-sentence reasoning, and mention the alternative in one line.
- Never propose weakening the non-regression rules or the invariants to save time. If a rule makes something hard, say so and propose how to satisfy it.
- If a team decision in <operating_model> looks unsafe or infeasible, say so plainly in Part 1 with numbers, propose the smallest change that fixes it, and implement the team's version unless I approve the change.
- Start Part 1 now.
</style_rules>
