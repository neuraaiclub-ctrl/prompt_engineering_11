# Prompt Engineering Hackathon Platform
## Software Requirements Specification (SRS)

**Version:** 1.0 (MVP-focused)
**Prepared for:** Development team implementing a digital platform for the "Prompt Engineering Hackathon" (Round 1 – Fix the Prompt, Round 2 – Constraint-Based Challenge)
**Status:** Draft for implementation

### Legend used throughout this document
| Tag | Meaning |
|---|---|
| **[PDF]** | Directly stated in the source hackathon-concept document |
| **[ASSUMPTION]** | Not stated in the PDF; assumed for a workable system |
| **[PROPOSED]** | Not stated in the PDF; recommended addition/extension |
| **[OPEN QUESTION]** | Ambiguous or undecided; a recommended default is given |

---

# 1. Executive Summary

This SRS specifies a web platform that runs the two-round "Prompt Engineering Hackathon" described in the source PDF, end to end: team formation, round delivery, iterative prompt editing with full version history, server-side prompt execution against an abstracted LLM provider, automated + human evaluation, a secure hidden-test system, a live leaderboard, and dashboards for participants, judges, and organizers.

Two rounds drive the whole product:
- **Round 1 – Fix the Prompt [PDF]:** teams are given a deliberately broken prompt and its bad output, then iteratively rewrite it (Original → v2 → v3 → Final), explaining each change. Judging blends automated checks with human review of diagnosis quality, iteration quality, and documentation clarity.
- **Round 2 – Constraint-Based Challenge [PDF]:** teams solve one fixed task under an artificial constraint (token limit, zero-shot, one-shot, no system prompt, generalization across unseen inputs, or valid-JSON-always), submit exactly **one final prompt**, and are scored primarily by automated execution against hidden test inputs.

**Recommended architecture:** a modular monolith (not microservices) — see Section 16 — built with a Python/FastAPI backend, a Next.js frontend, PostgreSQL, and Redis, with a provider-agnostic AI execution layer so the underlying LLM API can be swapped without touching business logic. This is chosen because the platform will typically be built and run by a small student/organizer team under time pressure, and a monolith is dramatically cheaper to build, deploy, and debug than a distributed system, while still being cleanly modular (Section 16) so it can be split apart later if needed.

The MVP (Section 25) intentionally excludes anything not required to run one live hackathon event: no multi-tenant white-labeling, no plugin marketplace for new round types, no advanced analytics — just enough to run Round 1 and Round 2 fairly, securely, and live.

---

# 2. Understanding of the PDF

## 2.1 What the source document actually says
The uploaded PDF is titled *"Prompt Engineering Hackathon – Round Concepts: 'Fix the Prompt' & Constraint-Based Challenge."* It describes **event design**, not software. It contains no mention of accounts, databases, APIs, or a platform — those requirements are derived/assumed per Section 41 of the instructions accompanying this task and are labeled accordingly throughout this SRS.

### Round 1 — "Fix the Prompt" **[PDF]**
- Teams receive a deliberately weak prompt plus the bad output it produced, and must iteratively improve it while documenting their reasoning at each step.
- Organizers prepare **3–5 broken-prompt cases**, easy to hard. Each case includes: the original bad prompt, the bad output (screenshot or text), and the underlying reason it's broken (ambiguous / missing context / no format spec / contradictory instructions / etc.).
- Teams pick one case (or rotate through 2–3 in a longer session).
- Teams rewrite the prompt across multiple iterations, not a single fix: **Original → v2 → v3 → Final**.
- For each iteration, teams write **one line** explaining what changed and why it helped (example given: *"Added output format spec — the model was returning prose instead of JSON."*).
- Example problem categories given: Vague, No format specified, Contradictory, No role/context, Missing edge cases — each with an example broken prompt and a fix direction.
- **Judging criteria [PDF]:** correct diagnosis of why the original prompt failed; each iteration being a meaningful, explainable improvement (not random tweaking); final output quality vs. the original; clarity of documentation (could a beginner follow the logic?).
- **Logistics [PDF]:** ~30–45 minutes per case including a 2-minute team readout; judges (or the guest lecturer) may read out 2–3 submissions live and comment on technique.

### Round 2 — Constraint-Based Challenge **[PDF]**
- All teams solve the **same fixed task** under the **same artificial constraint**, forcing specific techniques instead of long brute-force prompts.
- **Constraint types given:** prompt under 50 tokens; zero-shot only; one-shot only (exactly 1 example); no system prompt allowed; must work across 3 unseen test inputs without modification; output must be valid JSON every time.
- **Sample tasks given:** sentiment classification on tricky/sarcastic reviews; structured data extraction from messy text; one-sentence summarization; natural-language-to-SQL-like conversion; multi-step math/logic word problems.
- **Process [PDF]:** all teams get the same task, constraint, and 3–5 hidden test inputs; teams submit **one final prompt — no iteration during scoring** ("rewards getting it right rather than spamming variations"); prompts are run against hidden inputs live or via a shared script so results are transparent.
- **Judging criteria [PDF]:** percentage of test cases passed; constraint compliance (did they cheat the token limit or sneak in an example?); technique used (teams briefly explain their approach).
- **Logistics [PDF]:** ~20–30 minutes to write, followed by a shared live "run-off"; recommended to project it for the room since it's the most spectator-friendly part.

## 2.2 What is *not* in the PDF
The PDF defines **event rules**, not a system. Everything about accounts, roles, teams-as-software-objects, a prompt editor UI, an execution backend, hidden-test storage/security, scoring persistence, a leaderboard, and admin/judge dashboards is a natural translation of the event into software, and is marked **[PROPOSED]** or **[ASSUMPTION]** in the sections below rather than attributed to the PDF.

---

# 3. Product Vision

Build a web platform that lets an organizer run the Prompt Engineering Hackathon digitally, end-to-end, so that:

- Organizers/Admins create and manage hackathons, rounds, broken-prompt cases, and constraint challenges. **[PROPOSED]**
- Teams form, join, and work together on assigned challenges. **[PROPOSED]**
- Participants iteratively improve prompts in Round 1 with full version history and one-line change explanations per version. **[PDF]-derived**
- Participants submit a single locked final prompt in Round 2 under a configured constraint. **[PDF]-derived**
- The system executes submitted prompts against an abstracted AI provider and captures outputs, timing, and token usage. **[PROPOSED]**
- The system automatically evaluates what can be evaluated objectively (format compliance, JSON validity, hidden-test pass rate, constraint compliance) and routes subjective dimensions to human judges. **[PDF]-derived + PROPOSED]**
- Judges score submissions against a rubric derived directly from the PDF's judging criteria, without being able to see information that should stay hidden. **[PDF]-derived**
- A live, server-computed leaderboard aggregates round scores into rankings. **[PROPOSED]**
- Organizers can monitor the event live: submissions, timers, judging progress, system health. **[PROPOSED]**
- Hidden test inputs and expected answers are protected from participants at all times unless explicitly revealed post-round by an organizer. **[PDF]-derived, explicitly emphasized in the source instructions**

**MVP philosophy:** ship only what is required to run one live event fairly and reliably (Section 25). Everything else is Phase 2 or Future (Section 26).

---

# 4. Actors and Roles

| Role | Description | Source |
|---|---|---|
| **Admin/Organizer** | Creates hackathons/rounds/cases/challenges, manages teams and judges, controls timers, publishes results. Highest privilege. | [PROPOSED] |
| **Team Leader** | A participant with additional team-management permissions (invite/remove members, finalize submissions). | [PROPOSED] |
| **Team Member (Participant)** | Works on challenges as part of a team; the PDF's rounds are explicitly **team**-based ("Teams pick one case…", "Teams submit one final prompt"). | [PDF]-derived (team as the acting unit) |
| **Judge** | Reviews submissions and enters human-evaluation scores per the PDF's judging criteria; may also be the "guest lecturer" reading out submissions live. | [PDF]-derived |
| **Spectator/Viewer** *(read-only, optional)* | Views the live leaderboard/run-off on a projector, per the PDF's suggestion to project Round 2's run-off for the room. No login required. | [PROPOSED], MVP-optional |
| **AI Provider (system actor)** | External LLM API invoked by the Prompt Execution Service; not a human role but a first-class actor in execution flows. | [PROPOSED] |

**OPEN QUESTION:** Can one person hold both Judge and Organizer roles in a small event?
**RECOMMENDED DEFAULT:** Yes — roles are additive permissions on a user account, not mutually exclusive account types, so a single user can hold Admin + Judge simultaneously.

**OPEN QUESTION:** Does the PDF imply individual (non-team) participation is ever allowed?
**RECOMMENDED DEFAULT:** No — treat every submission as team-owned. A "team" may still have exactly one member if organizers allow solo entries; enforce via `Team.minSize` config (Section 12), default minSize = 1.


---

# 5. Functional Requirements

## 5.1 Conventions
- IDs are sequential: **FR-001…FR-115**, grouped by module (ranges below). Gaps are left intentionally for future insertions.
- **Priority:** P0 = Critical (MVP-blocking), P1 = High, P2 = Medium, P3 = Low (see Section 25 for the MVP cut line).
- **Scoping note:** to keep this document implementable rather than exhaustive, ~20 representative **P0** requirements across the whole system are written out in full flow format (Preconditions / Main Flow / Alt-Exception Flow / Expected Result / Acceptance Criteria). The remaining requirements use a compact index table (ID / Name / Actor / Priority / Description) — they follow the identical flow structure and should be expanded to full format before a sprint that implements them, using the detailed ones as the template.
- Module ranges: Auth FR-001–010 · Team FR-011–022 · Hackathon/Round Mgmt FR-023–032 · Round 1 FR-033–050 (Section 6) · Round 2 FR-051–068 (Section 7) · Automated Evaluation FR-069–076 (Section 8) · Human Judging FR-077–086 (Section 9) · Leaderboard FR-087–092 · Admin Dashboard FR-093–098 · Participant Dashboard FR-099–101 · Judge Dashboard FR-102–104 · Timer/Round Control FR-105–110 · Notifications FR-111–115.

## 5.2 Authentication & User Management (FR-001–FR-010)

### FR-001 — Register Account *(Detailed — P0)*
- **Description:** A person creates an account with email + password to participate as a Participant, Team Leader, or Judge (Admins are provisioned by existing Admins, not self-registered — see Open Question below).
- **Actor:** Unauthenticated user.
- **Preconditions:** Email not already registered; hackathon registration window is open **[OPEN QUESTION — see below]**.
- **Main Flow:** 1) User submits name, email, password, (optional) org/college affiliation. 2) System validates email format and password strength. 3) System hashes password (bcrypt/argon2) and creates a `User` record with status `active`. 4) System sends a confirmation notification (Section 20). 5) User is redirected to login.
- **Alt/Exception Flow:** Email already registered → 409 with "account already exists, log in or reset password." Weak password → 422 listing the failed rule.
- **Expected Result:** A `User` row exists with role `participant` by default; no role escalation happens at registration.
- **Priority:** P0.
- **Acceptance Criteria:** Given a unique, valid email and a password meeting policy, registering returns 201 and the user can immediately log in; given a duplicate email, registering returns 409 and no duplicate row is created.

**OPEN QUESTION:** Is registration self-service and open, or invite-only (e.g., pre-loaded participant list from event registration)?
**RECOMMENDED DEFAULT:** Self-service open registration for the MVP, with an Admin-controlled toggle to close registration once teams lock (FR-030). Invite-only import is Phase 2 (Section 26).

### FR-002 — Login *(Detailed — P0)*
- **Actor:** Registered user. **Preconditions:** Account status = active. **Main Flow:** 1) User submits email+password. 2) System verifies credentials. 3) System issues a session token (JWT, short-lived access + refresh token). 4) User is routed to their role's dashboard. **Alt Flow:** Wrong credentials → 401, generic "invalid email or password" (no user-enumeration hints). Account suspended → 403 "account disabled, contact an organizer." **Expected Result:** Valid session established; last-login timestamp updated. **Priority:** P0. **Acceptance Criteria:** 5 consecutive failed attempts within 10 minutes temporarily rate-limits further attempts for that account (FR-009).

### FR-003 — Logout — P0 — Invalidate/blacklist the current refresh token; client clears session.
### FR-004 — Password Reset — P1 — Time-limited, single-use reset token emailed on request; never reveals whether an email exists.
### FR-005 — Role-Based Access Control (RBAC) — P0 — Every API endpoint declares required role(s)/permission(s); unauthorized calls return 403, not a silent empty result (prevents information leakage about hidden data — critical for hidden tests, Section 11).
### FR-006 — Session Management — P0 — Access tokens expire in ≤ 30 minutes; refresh tokens ≤ 7 days and are revocable by Admin (e.g., to kick a cheating account mid-round).
### FR-007 — Account Status Management — P1 — Admin can suspend/reinstate an account; suspension immediately invalidates active sessions.
### FR-008 — Unauthorized Access Handling — P0 — All 401/403 responses are logged (Section 20) without leaking whether the *target resource* exists (avoids probing for hidden test IDs).
### FR-009 — Login Rate Limiting — P1 — Progressive lockout after repeated failures (see FR-002).
### FR-010 — Admin Provisioning — P1 — Only an existing Admin can grant the Admin or Judge role to an account; Participants/Team Leaders cannot self-elevate. **[PROPOSED, security-critical]**

## 5.3 Team Management (FR-011–FR-022)

### FR-011 — Create Team *(Detailed — P0)*
- **Actor:** Any authenticated participant (becomes Team Leader). **Preconditions:** User is not already on a team for this hackathon **[ASSUMPTION: one team per hackathon per user — see Open Question]**. **Main Flow:** 1) User submits a team name (+ optional description). 2) System checks name uniqueness within the hackathon. 3) System creates `Team` (status `forming`) and a `TeamMember` row for the creator with role `leader`. **Alt Flow:** Duplicate name → 409. User already on a team → 409 "leave your current team first." **Expected Result:** New team visible in the hackathon lobby; creator is leader. **Priority:** P0. **Acceptance Criteria:** Creating a team with a unique name succeeds and the creator can immediately invite members; a duplicate name is rejected without creating a row.

### FR-012 — Join Team via Invite Code *(Detailed — P0)*
- **Actor:** Participant. **Preconditions:** Team not full (`TeamMember count < Hackathon.maxTeamSize`), team status `forming`, round not yet started (FR-018). **Main Flow:** 1) User enters a team invite code. 2) System validates code + capacity + team status. 3) `TeamMember` row created with role `member`. **Alt Flow:** Team full → 409. Round already locked → 423 "teams are locked, contact an organizer." **Expected Result:** User appears in team roster. **Priority:** P0.

### FR-013 — Team Invitation Generation — P1 — Leader generates/regenerates a shareable invite code or emails invites directly.
### FR-014 — Remove/Leave Team Member — P1 — Leader can remove a member (not themself); a member can voluntarily leave *before* team lock (FR-018). Leaving after lock is blocked (423) to protect fairness — see Edge Case in Section 21 ("team leader leaves").
### FR-015 — Transfer/Reassign Team Leader — P2 — If the leader leaves before lock, system prompts remaining members to elect a new leader; if none remain, team is auto-dissolved. **[PROPOSED — Edge Case handling]**
### FR-016 — Team Size Limits — P0 — Enforced server-side from `Hackathon.minTeamSize`/`maxTeamSize` (organizer-configured; **[OPEN QUESTION]** PDF gives no number — **RECOMMENDED DEFAULT:** min 1, max 4).
### FR-017 — Team Status Lifecycle — P1 — `forming → locked → active → completed` (locked triggers automatically at Round 1 start, or manually by Admin).
### FR-018 — Team Locking on Round Start *(Detailed — P0)*
- **Description:** Once any round is started, team rosters freeze, preventing mid-competition roster changes that could be used to smuggle in outside help.
- **Actor:** System (triggered by Admin starting a round, FR-105). **Preconditions:** Round.status transitions to `active`. **Main Flow:** 1) System sets `Team.status = locked` for all teams in the hackathon. 2) Join/leave/invite endpoints begin returning 423 for locked teams. **Alt/Exception Flow:** Admin can force-unlock a specific team for an exceptional case (e.g., correcting a data-entry error), which is audit-logged (Section 20). **Expected Result:** No roster changes are possible during active competition without an explicit, logged Admin override. **Priority:** P0. **Acceptance Criteria:** Attempting to join/leave a locked team returns 423 and no `TeamMember` row is changed; an Admin override is recorded in `AuditLog` with actor, reason, and timestamp.

### FR-019 — Team Deletion — P2 — Admin-only; blocked if the team has any Submission rows (must be reassigned/archived instead of hard-deleted, to preserve audit trail).
### FR-020 — Prevent Unauthorized Team Access — P0 — A user can only view/edit the internals (prompt versions, submissions) of teams they belong to, or any team if they are Admin/Judge (read-only for Judge, scoped to assigned submissions — Section 9).
### FR-021 — View My Team — P1 — Members/leader see roster, invite code, and lock status.
### FR-022 — Organizer Team Directory — P1 — Admin sees all teams, sizes, and lock status across the hackathon.

## 5.4 Hackathon & Round Management (FR-023–FR-032)

| ID | Name | Actor | Priority | Description |
|---|---|---|---|---|
| FR-023 | Create Hackathon | Admin | P0 | Title, description, start/end datetime, registration window. |
| FR-024 | Edit Hackathon | Admin | P1 | Edit metadata before it starts; restricted fields once active. |
| FR-025 | Activate/Deactivate Hackathon | Admin | P0 | Only one hackathon is `active` for public participant access at a time **[ASSUMPTION]**. |
| FR-026 | Create Round | Admin | P0 | A hackathon has an ordered list of rounds; MVP ships exactly Round 1 and Round 2 as defined by the PDF, but the model supports N rounds (Instruction #11: "modular... additional rounds can be added later"). |
| FR-027 | Configure Round Duration | Admin | P0 | Start time + duration (or explicit end time); feeds the server-side timer (FR-105). |
| FR-028 | Configure Round Status | Admin | P0 | `draft → published → active → ended`. |
| FR-029 | Publish/Unpublish Round | Admin | P0 | Only `published` rounds are visible to participants ahead of start. |
| FR-030 | Close Registration on Lock | Admin | P1 | Optional toggle to stop new signups once teams lock (ties to FR-001 Open Question). |
| FR-031 | View Participant/Team Statistics | Admin | P1 | Counts of teams, members, submissions per round, live. |
| FR-032 | Monitor Submissions Live | Admin | P0 | Real-time (poll or websocket) feed of incoming submissions per round. |

## 5.5 Judging System (FR-077–FR-086)
*(Full detail and rubric given in Section 9; index below for completeness of the master list.)*

| ID | Name | Actor | Priority | Description |
|---|---|---|---|---|
| FR-077 | View Assigned Submissions | Judge | P0 | Judge sees only submissions assigned to them (FR-102). |
| FR-078 | View Team/Participant Info | Judge | P1 | Team name, members; **not** individual scoring bias data. |
| FR-079 | View Prompt Version History | Judge | P0 | Full Original→v2→v3→Final chain with explanations (Round 1). |
| FR-080 | View Explanations | Judge | P0 | Per-iteration one-line explanations (Round 1). |
| FR-081 | View Captured Outputs | Judge | P0 | Model outputs captured at execution time, not re-run live by the judge. |
| FR-082 | Enter Scores | Judge | P0 | Per-rubric-dimension numeric scores within configured ranges (FR-018 validation, Section 18). |
| FR-083 | Add Comments | Judge | P1 | Free-text feedback, visible to Admin always, to participants only after results publish. |
| FR-084 | Submit Evaluation | Judge | P0 | Locks the evaluation; see FR-085 for edit window. |
| FR-085 | Edit Evaluation Before Locking | Judge | P1 | Editable until Admin locks judging for the round (FR-108). |
| FR-086 | View Scoring Rubric | Judge | P0 | Rubric text pulled from Section 9, always visible alongside the scoring form. |

## 5.6 Leaderboard (FR-087–FR-092)

| ID | Name | Actor | Priority | Description |
|---|---|---|---|---|
| FR-087 | Compute Team Ranking | System | P0 | Aggregates Round 1 + Round 2 scores per configured weights (FR-092). |
| FR-088 | Round-Wise Score Breakdown | Participant/Judge/Admin | P1 | Shows sub-scores per round, not just total. |
| FR-089 | Show Test Cases Passed (Round 2) | Participant | P1 | e.g., "Passed 4/5" without ever revealing which inputs or answers (Section 11). |
| FR-090 | Tie-Breaking | System | P1 | See Section 13 default below — **[OPEN QUESTION/PROPOSED]**, not defined in PDF. |
| FR-091 | Submission Status on Leaderboard | Participant/Admin | P2 | e.g., "not submitted," "submitted," "scored." |
| FR-092 | Configure Scoring Weights | Admin | P2 | Per-dimension weight config; **[PROPOSED extension]**, PDF does not define numeric weights. |

**OPEN QUESTION:** Tie-breaking rule (not specified in PDF).
**RECOMMENDED DEFAULT:** 1) higher Round 2 % test cases passed, 2) higher Round 1 human score, 3) earlier final-submission timestamp. Organizer-configurable order; documented before the event so it's never decided ad hoc.

## 5.7 Admin Dashboard (FR-093–FR-098)

| ID | Name | Priority | Description |
|---|---|---|---|
| FR-093 | Hackathon Overview Panel | P0 | Active rounds, team/participant counts, submission counts, live score/system health snapshot. |
| FR-094 | Round Control Panel | P0 | Create/Edit/Start/Pause/End/Publish/Lock a round (ties to FR-105–110). |
| FR-095 | Challenge Management Panel | P0 | CRUD for broken-prompt cases (Round 1) and constraint challenges + hidden tests (Round 2). |
| FR-096 | Judging Oversight Panel | P1 | Judge assignment, per-judge progress, score verification/outlier flags. |
| FR-097 | Results & Export Panel | P1 | Leaderboard view, CSV/JSON export of final rankings. |
| FR-098 | System Health Panel | P2 | AI provider latency/error rate, queue depth for execution jobs. |

## 5.8 Participant Dashboard (FR-099–FR-101)
| ID | Name | Priority | Description |
|---|---|---|---|
| FR-099 | Participant Home | P0 | Current hackathon, team, active round, countdown timer (server time, FR-105), assigned challenge link. |
| FR-100 | Prompt Workspace Entry | P0 | One-click into the Prompt Editor (Section 25) for the active round. |
| FR-101 | My Results | P1 | Shows score/result only once the organizer has published it (FR-097-adjacent gating). |

## 5.9 Judge Dashboard (FR-102–FR-104)
| ID | Name | Priority | Description |
|---|---|---|---|
| FR-102 | My Assignment Queue | P0 | Pending vs. completed evaluations for this judge only. |
| FR-103 | Submission Viewer | P0 | Read-only, judging-scoped view of a submission (version history, outputs, explanations). |
| FR-104 | Finalize Evaluation | P0 | Same action as FR-084, surfaced from this dashboard. |

## 5.10 Notifications (FR-111–FR-115)
| ID | Name | Priority | Description |
|---|---|---|---|
| FR-111 | Round Starting Notice | P2 | In-app (MVP) / email (Phase 2) a few minutes before start. |
| FR-112 | Round Ending Soon Notice | P1 | e.g., 5-minute warning, server-time driven. |
| FR-113 | Submission Confirmation | P1 | Immediate in-app toast + persisted "submitted" state. |
| FR-114 | Evaluation Completed Notice | P2 | Sent when a judge locks an evaluation, if results are set to auto-reveal. |
| FR-115 | Results Published Notice | P1 | Sent when Admin publishes final results (Section 20: "do not over-engineer notifications for MVP" — keep to in-app only for MVP; email/push is Phase 2). |

---

# 6. Round 1 Functional Requirements — "Fix the Prompt" (FR-033–FR-050)

## 6.1 Case Management (FR-033–FR-039)

### FR-033 — Create Broken-Prompt Case *(Detailed — P0)*
- **Description:** Admin authors a case exactly matching the PDF's structure: original bad prompt, bad output, and the underlying reason it's broken.
- **Actor:** Admin. **Preconditions:** Admin is authenticated; a `Round` of type Round 1 exists.
- **Main Flow:** 1) Admin enters original prompt text. 2) Admin enters the bad output (text, and/or uploads a screenshot — **[PDF]**: "screenshot or text"). 3) Admin selects/enters the broken-prompt reason from the PDF's taxonomy (FR-034). 4) Admin sets difficulty (easy/medium/hard — **[PDF]**: "ranging from easy to hard"). 5) Admin optionally defines "expected improvement characteristics" used later for automated format/keyword checks (FR-069). 6) Case is saved as `draft`.
- **Alt/Exception Flow:** Missing required field (prompt or output) → 422 listing missing fields.
- **Expected Result:** A `PromptCase` row exists, not yet visible to participants until published (FR-039).
- **Priority:** P0.
- **Acceptance Criteria:** A case with all required fields saves successfully and appears in the Admin's case list with status `draft`; publishing it (FR-039) makes it visible to assigned teams only.

### FR-034 — Broken-Prompt Reason Taxonomy — P0 — Fixed enum matching the PDF's categories: `vague`, `no_format_specified`, `contradictory`, `no_role_context`, `missing_edge_cases`, plus `other` (free text) for cases outside the PDF's five examples. **[PDF]-derived enum, `other` is [PROPOSED] for extensibility.**
### FR-035 — Attach Screenshot/Text Evidence — P1 — File upload (image) or plain text for the "bad output," per PDF wording.
### FR-036 — Set Difficulty — P0 — `easy` / `medium` / `hard` per PDF.
### FR-037 — Define Expected Improvement Characteristics — P1 — Structured hints used only by the *automated* evaluator (Section 8), e.g. "output must be valid JSON," "output must be under N words" — never shown to participants as answers.
### FR-038 — Case Rotation/Selection Config — P1 — Admin defines whether teams get one assigned case or may pick from a pool of 2–3 **[PDF]**: "Teams pick one case (or rotate through 2–3 in a longer session)."
### FR-039 — Publish/Unpublish Case — P0 — Only `published` cases are assignable/visible to teams; unpublishing after assignment is blocked once a team has started (423) to avoid disrupting an in-progress attempt.

## 6.2 Participant Workflow (FR-040–FR-045)

### FR-040 — Open Assigned Case *(Detailed — P0)*
- **Actor:** Team Leader or Member. **Preconditions:** Round 1 is `active`; team is assigned (or has selected, per FR-038) a case. **Main Flow:** 1) Participant opens the case page. 2) System displays original prompt, bad output, and a neutral case description — **never** the internal `brokenReason` enum or `expectedImprovementCharacteristics` (those are evaluator-only, FR-037). 3) Participant proceeds to the Prompt Editor (Section 25). **Alt Flow:** Round not yet active → 403 "round has not started." **Expected Result:** Team sees exactly what the PDF specifies a team should diagnose from — prompt + bad output — nothing more. **Priority:** P0. **Acceptance Criteria:** The API response for "open case" never includes `brokenReason` or `expectedImprovementCharacteristics` fields for a Participant-scoped request; it does for Admin/Judge-scoped requests.

### FR-041 — Create New Prompt Version *(Detailed — P0)*
- **Actor:** Team Leader or Member. **Preconditions:** Case opened (FR-040); round still active. **Main Flow:** 1) Participant edits prompt text in the editor. 2) Participant writes the required one-line "what changed / why it helped" explanation — **[PDF]**: "one line explaining what changed and why it helped." 3) Participant optionally triggers execution (FR-046) to see the new output before finalizing the version. 4) Participant saves the version. 5) System increments the version number and appends (never overwrites) to the `PromptVersion` history. **Alt/Exception Flow:** Explanation left blank → 422 "an explanation is required for each iteration" (enforces the PDF's documentation requirement, not just a nice-to-have). Round ends mid-edit → draft is retained but further saves are rejected with 423. **Expected Result:** A new immutable `PromptVersion` row (Original, v2, v3, … Final). **Priority:** P0. **Acceptance Criteria:** Saving a version with a non-empty prompt and explanation creates a new row and never modifies a prior version's row; the full chain is retrievable in order.

### FR-042 — View Version History — P0 — Read-only chronological list, Original→…→Final, with prompt text, explanation, timestamp, and (if executed) captured output for each version.
### FR-043 — Mark Final Version — P0 — Explicit action distinguishing "still iterating" from "this is my Final" (PDF's own vocabulary), used by evaluation/judging to know which version is scored as "final output quality."
### FR-044 — Submit Round 1 Case — P0 — Locks further version creation for that case/team (see Open Question on edit windows below); triggers automated evaluation (Section 8) and queues for judge assignment (Section 9).
### FR-045 — Team-Shared Editing — P1 — Any team member can add a version (not just the leader), since the PDF frames this as a **team** activity; last-write-wins conflict handling is acceptable for MVP (Section 20 in original prompt template: "Reliability" — full operational-transform co-editing is Future, Section 26).

**OPEN QUESTION:** Can a team edit/add versions after clicking "Submit"?
**RECOMMENDED DEFAULT:** No — submission locks the case for that team (consistent with Round 2's stricter "one final prompt" rule and with fair, comparable judging). Organizer can grant a one-time "reopen" override (audit-logged), mirroring the Team-lock override in FR-018.

## 6.3 Prompt Execution — Round 1 (FR-046–FR-050)

### FR-046 — Execute Prompt Against AI Provider *(Detailed — P0)*
- **Description:** Runs a draft or saved prompt version through the abstracted AI Provider (Section 15) so the team can see the resulting output before finalizing a version.
- **Actor:** Team Leader/Member (triggering), System (executing). **Preconditions:** Round active; team has not exceeded execution rate limit (FR-050).
- **Main Flow:** 1) Client sends prompt text (+ system prompt, if used) to `POST /executions`. 2) Prompt Execution Service selects the configured model, applies a request timeout, and calls the AI Provider Adapter. 3) Output, token usage, latency, and status (`success`) are captured into an `Execution` row linked to the `PromptVersion`. 4) Output is returned to the client for display.
- **Alt/Exception Flow:** Provider timeout → `Execution.status = timeout`, user sees "the model took too long — try again," retry is allowed (Section 19). Provider error/5xx → `status = error`, generic user-facing message, full error logged server-side (never expose raw provider error text/keys to the client). Rate limit exceeded → 429 with a clear "try again in Ns" message.
- **Expected Result:** Every execution attempt (success or failure) is persisted for audit and for judges to review actual behavior, not just self-reported claims.
- **Priority:** P0.
- **Acceptance Criteria:** A successful call persists an `Execution` row with non-null output, token counts, and latency; a timeout persists a row with `status=timeout` and null output, and never crashes the request thread.

### FR-047 — Model Selection — P1 — For MVP, the model is fixed per hackathon/round by the Admin (not chosen by participants), to keep Round 1/2 comparisons fair. **[ASSUMPTION]** — letting participants choose models is **[PROPOSED, Phase 2]** and would need to become a judged/constrained dimension itself.
### FR-048 — Variable/Placeholder Support — P3 — **[PROPOSED, Future]** templated variables in prompts (e.g., `{{input}}`) for reusability; not required by the PDF's Round 1 flow.
### FR-049 — Execution Status Tracking — P0 — `queued → running → success|error|timeout`, surfaced in the UI so users aren't staring at a blank screen.
### FR-050 — Execution Rate Limiting — P1 — Per-team cap (e.g., N executions/minute) to control AI provider cost and prevent one team from monopolizing capacity during a live event — **[PROPOSED, cost control]**.

---

# 7. Round 2 Functional Requirements — Constraint-Based Challenge (FR-051–FR-068)

## 7.1 Challenge & Constraint Configuration (FR-051–FR-057)

### FR-051 — Create Constraint Challenge *(Detailed — P0)*
- **Description:** Admin defines the single fixed task all teams solve, per the PDF's "same task, same constraint, same hidden inputs" model.
- **Actor:** Admin. **Main Flow:** 1) Admin writes the task description (from the PDF's sample-task categories, FR-052, or a custom task). 2) Admin selects one constraint type (FR-053). 3) Admin adds visible example(s) *if the constraint allows it* (zero-shot ⇒ none allowed; one-shot ⇒ exactly one; other constraints ⇒ organizer's choice). 4) Admin adds 3–5 hidden test inputs + expected outputs/evaluation rule (Section 11). 5) Admin sets a time limit (**[PDF]**: 20–30 minutes to write) and scoring rules (Section 13). 6) Challenge saved as `draft`, later published.
- **Alt/Exception Flow:** Constraint = one-shot but 0 or 2+ examples supplied → 422 "one-shot requires exactly one example." Fewer than 3 hidden tests supplied → 422 (PDF: "3 unseen test inputs" minimum / "3–5 hidden test inputs").
- **Expected Result:** A fully specified, publishable `ConstraintChallenge` with its `Constraint` and linked `TestCase` rows.
- **Priority:** P0.
- **Acceptance Criteria:** Attempting to publish a challenge with no hidden test cases, or with a constraint/example mismatch, is rejected with a specific validation message; a correctly configured challenge publishes successfully.

### FR-052 — Task Template Library — P2 — Preloaded templates for the PDF's five sample task types (sentiment classification on sarcastic text, structured extraction, one-sentence summarization, NL→SQL-like, math/logic word problems) to speed up Admin setup. **[PDF]-derived list, template feature itself is [PROPOSED].**
### FR-053 — Constraint Type Enum *(Detailed — P0)*
- **Description:** The six constraint types are first-class, machine-checkable configuration, not free text, because Round 2 scoring explicitly includes automated "constraint compliance" (Section 8).
- **Enum values [PDF]:** `max_tokens_50` (or configurable `max_tokens_n`), `zero_shot` (no examples), `one_shot` (exactly 1 example), `no_system_prompt`, `generalize_unseen_inputs` (works unmodified across N unseen inputs), `valid_json_always`.
- **Priority:** P0.
- **Acceptance Criteria:** Each enum value has an associated automated validator (Section 8.2) that runs at submission time; a challenge cannot publish without exactly one constraint selected. **[OPEN QUESTION: can multiple constraints combine? PDF presents them as a single-choice list. RECOMMENDED DEFAULT: MVP supports exactly one constraint per challenge; multi-constraint stacking is Phase 2.]**

### FR-054 — Token Counting Utility — P0 — Server-side tokenizer (not naive whitespace split) used consistently for `max_tokens_n` validation and for the live token counter in the editor (Section 25); must match whatever the AI provider actually counts against, or be documented as an approximation.
### FR-055 — Visible Example Management — P1 — Zero/one example enforcement, tied to the selected constraint (FR-053).
### FR-056 — Time Limit Configuration — P1 — Per-challenge write time limit (**[PDF]** 20–30 min), feeding the server-side timer (Section 19).
### FR-057 — Scoring Rule Configuration — P1 — Weights/rules for % tests passed vs. constraint compliance vs. technique explanation (Section 13/8/9).

## 7.2 Hidden Test Case System (FR-058–FR-064)
*(Security-critical — see Section 11 for the full threat model.)*

### FR-058 — Secure Hidden Test Storage *(Detailed — P0)*
- **Description:** Hidden test inputs and expected answers/eval-rules must never be retrievable by a Participant-scoped credential, at any stage, through any endpoint.
- **Actor:** System/Admin. **Preconditions:** N/A. **Main Flow:** 1) `TestCase` rows are stored with `visibility = hidden` by default. 2) All read paths (including generic "list challenge details" endpoints) explicitly strip hidden `TestCase` fields for non-Admin/Judge roles at the serialization layer, not just the route layer (defense in depth). **Alt/Exception Flow:** A bug or misconfigured endpoint that would leak hidden data is treated as a **P0 security incident**, not a normal bug (Instruction #7: "Security of hidden test cases is critical"). **Expected Result:** A Participant can never see raw hidden inputs/expected answers before or after the round unless an Admin explicitly reveals them (FR-064). **Priority:** P0. **Acceptance Criteria:** An authenticated Participant token, called against every endpoint that touches a `TestCase`, never receives `input`, `expectedOutput`, or internal `evalRule` fields — verified by an automated contract test (Section 22.9) run in CI on every deploy.

### FR-059 — Isolated Test Execution — P0 — Hidden-test runs happen server-side, inside the Prompt Execution Service, never by sending the hidden input to a client for "local" execution.
### FR-060 — Submission-Triggered Test Run — P0 — On Round 2 submission (FR-067), the system automatically runs the final prompt against all of that challenge's hidden `TestCase` rows.
### FR-061 — Result Calculation Without Disclosure *(Detailed — P0)*
- **Description:** Implements the PDF's own privacy example almost verbatim: report **"Passed: 4/5"** without revealing which input failed, the hidden input, the expected answer, or the internal evaluation logic.
- **Actor:** System. **Main Flow:** 1) After hidden-test execution (FR-060), system computes `passedCount/totalCount` and a compliance boolean for the constraint check. 2) Participant-facing response includes only the aggregate count/percentage + constraint-compliance boolean. 3) Per-test detail (which input, expected vs. actual) is stored but flagged `admin/judge only`.
- **Priority:** P0.
- **Acceptance Criteria:** The Participant-facing submission-result payload contains a pass count and a total count and nothing else about individual hidden tests; the same submission viewed by an Admin includes full per-test detail.

### FR-062 — Prevent API-Level Access to Hidden Data — P0 — No endpoint accepts a `testCaseId` parameter from a Participant-scoped token that would return hidden fields (object-level authorization check on every such route, not just role check).
### FR-063 — Prevent Test Case Tampering — P0 — Only Admin can create/edit/delete `TestCase` rows; write attempts from any other role return 403, and all writes are audit-logged (Section 20).
### FR-064 — Post-Round Reveal (Organizer-Controlled) — P1 — Admin can optionally flip challenge/test visibility to `revealed` after judging locks, so teams can review what they missed — explicitly opt-in, per the PDF's "unless the organizer chooses to reveal them after the round."

## 7.3 Round 2 Submission (FR-065–FR-068)

### FR-065 — Submit Final Prompt *(Detailed — P0)*
- **Description:** Implements the PDF's explicit rule that Round 2 uses **one final prompt** during scoring rather than allowing spammed variations.
- **Actor:** Team Leader/Member. **Preconditions:** Round 2 active; team has not already submitted for this challenge; time limit (FR-056) not exceeded.
- **Main Flow:** 1) Participant finalizes prompt text (+ example, if one-shot) in the editor. 2) Client-side validation shows constraint status (token count, JSON-mode indicator, etc.) as a convenience only. 3) On submit, server re-validates every constraint rule authoritatively (Section 25: "the actual scoring must use backend/server-side calculation rather than trusting the frontend"). 4) A `Submission` row is created and immediately locked (`status = locked`). 5) System triggers hidden-test execution (FR-060) and scoring (Section 8).
- **Alt/Exception Flow:** Second submission attempt for the same challenge → 409 "you have already submitted your final prompt for this round" (enforces "one final prompt," not resubmission). Constraint violated (e.g., 62 tokens when limit is 50) → 422 at submit time **[OPEN QUESTION: should an over-limit prompt be rejected outright, or accepted-but-penalized? PDF says "cheat the token limit" is itself a judged/penalized behavior, implying submission is allowed but *scored down*, not blocked. RECOMMENDED DEFAULT: allow submission, flag `constraintViolated=true`, and let the scoring engine (Section 8.2) zero out or heavily penalize the compliance sub-score, rather than blocking submission outright — this preserves the PDF's framing of compliance as a judged dimension.]**
- **Expected Result:** Exactly one immutable, scored `Submission` per team per Round 2 challenge.
- **Priority:** P0.
- **Acceptance Criteria:** A second submit call after a successful first submit returns 409 and creates no new row; a submit call with a constraint-violating prompt still creates exactly one `Submission` row, flagged as non-compliant, and is scored accordingly rather than silently dropped.

### FR-066 — Optional Explanation — P1 — Free-text "technique used" explanation field, per the PDF's judging criterion "technique used — ask teams to briefly explain their approach."
### FR-067 — Constraint Compliance Snapshot — P0 — At submission time, system persists the *evaluated* compliance result (not just the raw prompt) so later disputes can be resolved against what was actually checked, even if validator logic changes later.
### FR-068 — Submission Locking — P0 — Once locked (FR-065), no further edits; Admin-only override, audit-logged (mirrors FR-018/FR-041 pattern).

---

# 8. Automated Evaluation Requirements (FR-069–FR-076)

The PDF splits judging into criteria that are objectively checkable by a machine and criteria that require human judgment (Round 1: "clarity of documentation," "meaningful improvement"; Round 2: "technique used" explanation quality). This section covers what should be **automated**; Section 9 covers what stays **human**.

## 8.1 What is automated and why
| Dimension | Round | Automatable? | Rationale |
|---|---|---|---|
| Output format compliance (e.g., "must be JSON") | 1 & 2 | Yes | Deterministic parse/schema check |
| Required information present | 1 & 2 | Partially | Keyword/field presence check from `expectedImprovementCharacteristics` (FR-037) or `TestCase.evalRule` |
| Expected-answer matching | 2 | Yes | Exact/fuzzy match or schema validation against hidden `TestCase.expectedOutput` |
| Structured output validation | 1 & 2 | Yes | JSON Schema validation |
| Prompt constraint compliance (token count, zero/one-shot, no-system-prompt) | 2 | Yes | Deterministic, server-side (FR-053/054) |
| Test case pass % | 2 | Yes | Direct execution result (FR-060/061) |
| Correct diagnosis of the original problem | 1 | **No** | Requires reading the team's stated reasoning for genuine insight vs. a lucky guess — human (Section 9) |
| Meaningful, explainable improvement per iteration | 1 | **No** | Judgment call on whether a change is substantive |
| Final output quality (subjective) | 1 | **No** | Human, though automated format/keyword checks can feed into it as *evidence* |
| Documentation clarity | 1 | **No** | Inherently qualitative |
| Technique explanation quality | 2 | **No** | Qualitative |

## 8.2 Requirements

### FR-069 — Output Format Compliance Check *(Detailed — P0)*
- **Description:** Validates captured output against the challenge's declared format rule (e.g., valid JSON, matches a JSON Schema, is exactly one sentence).
- **Actor:** System, triggered on execution/submission. **Main Flow:** 1) System reads `Challenge.formatRule`. 2) Runs the appropriate validator (JSON parse + schema validation for `valid_json_always`; sentence-count heuristic for "one sentence," etc.). 3) Stores a boolean + detail message on the `Evaluation` row.
- **Priority:** P0. **Acceptance Criteria:** A malformed JSON output is flagged `formatCompliant=false` with a machine-readable reason; valid output is flagged `true`.

### FR-070 — Required-Information Presence Check — P1 — Keyword/field presence scan against admin-defined hints (FR-037); result is advisory evidence shown to judges, not an auto-score by itself for Round 1 (avoids over-automating a subjective round).
### FR-071 — Expected-Answer Matching (Round 2) — P0 — Exact match, normalized match, or schema-based match depending on `TestCase.evalRule` type; must be deterministic and unit-tested per task category (Section 22).
### FR-072 — Structured Output (JSON Schema) Validation — P0 — Shared validator used by both FR-069 and FR-071 where the constraint/task requires JSON.
### FR-073 — Constraint Compliance Validators — P0 — One validator per enum value in FR-053 (token count via FR-054; example count; system-prompt-field emptiness; etc.), each producing a boolean + human-readable reason string.
### FR-074 — Hidden Test Pass-Rate Calculation — P0 — `passed/total` from FR-060/061, persisted per submission (also feeds FR-089 leaderboard display).
### FR-075 — Automated Score Aggregation — P0 — Combines FR-069–074 into an `autoScore` sub-total per the weights in FR-057/Section 13, stored separately from the human `judgeScore` so the two are always auditable independently.
### FR-076 — Re-run Automated Evaluation (Admin) — P2 — If a validator bug is fixed mid-event, Admin can re-trigger automated evaluation for affected submissions without re-triggering hidden-test execution against the AI provider (cost control) — **[PROPOSED]**.

---

# 9. Human Judging Requirements (FR-077–FR-086 — index in Section 5.5; rubric detailed here)

## 9.1 Round 1 Rubric *(directly from PDF judging criteria)*
| Dimension | PDF wording | Suggested scale |
|---|---|---|
| Diagnosis quality | "Did the team correctly diagnose why the original prompt failed?" | 0–5 |
| Improvement quality | "Is each iteration a meaningful, explainable improvement (not random tweaking)?" | 0–5 |
| Final output quality | "Final output quality compared to the original." | 0–5 |
| Documentation clarity | "Clarity of documentation — could a beginner follow their logic?" | 0–5 |

## 9.2 Round 2 Rubric *(directly from PDF judging criteria)*
| Dimension | PDF wording | Automated or Human |
|---|---|---|
| % test cases passed | "Percentage of test cases passed." | Automated (FR-074) |
| Constraint compliance | "did they cheat the token limit or sneak in an example?" | Automated (FR-073), **human spot-check advisory** for edge cases a validator might miss (e.g., a technically-under-50-token prompt that smuggles instructions via unusual tokenization) |
| Technique used | "ask teams to briefly explain their approach." | Human, 0–5 |

**[OPEN QUESTION]** The PDF does not give numeric weights or a 0–N scale for any dimension.
**RECOMMENDED DEFAULT:** 0–5 integer scale per dimension (FR-018 validation range), equal weighting within each round unless Admin overrides via FR-092/FR-057.

## 9.3 Requirements detail (supplementing the FR-077–086 index in Section 5.5)

### FR-082 — Enter Scores *(Detailed — P0)*
- **Actor:** Judge. **Preconditions:** Submission assigned to this judge (FR-102); round's judging window open. **Main Flow:** 1) Judge opens a submission via the Submission Viewer (FR-103). 2) Judge enters an integer 0–5 for each rubric dimension (9.1 or 9.2, depending on round) + optional comment (FR-083). 3) Judge clicks Submit Evaluation (FR-084), which locks the row.
- **Alt/Exception Flow:** Score outside 0–5 → 422 (server-side validated, never trust client range enforcement alone — Section 18). Two judges assigned to the same submission (Edge Case, Section 21) → both scores are stored independently; final score = average, per **[OPEN QUESTION/RECOMMENDED DEFAULT]** below.
- **Priority:** P0. **Acceptance Criteria:** Submitting a full rubric within range locks the evaluation and it appears in the Admin's "score verification" panel (FR-096); an out-of-range value is rejected before any partial write occurs (atomic).

**OPEN QUESTION:** How are multiple judges' scores for one submission combined?
**RECOMMENDED DEFAULT:** Simple average per dimension across all judges assigned to that submission; Admin dashboard flags dimensions where judges disagree by more than a configurable threshold (e.g., ≥2 points) for manual review — **[PROPOSED]**, not specified in PDF.

### Information-hiding requirement for judges
Per Instruction #14 ("judges should be prevented from accidentally seeing information that should remain hidden"): a Judge-scoped Submission Viewer must **never** display `TestCase.expectedOutput`/`input` fields for still-hidden tests unless Admin has flipped `visibility=revealed` (FR-064) — same enforcement mechanism as FR-058, just scoped to the Judge role instead of Participant.

---

# 10. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-001 | Performance | Dashboard pages respond in **< 2s** under normal load (p95), excluding any AI provider call. |
| NFR-002 | Performance | Prompt submission (save/version-create) API responds in **< 2s** (p95), excluding AI execution time. |
| NFR-003 | Performance | AI execution latency is tracked and surfaced separately from application latency — the app must clearly show "waiting on model" vs. "server error," never conflate the two in metrics or in the UI. |
| NFR-004 | Performance | Evaluation results (automated) appear within a defined SLA after submission — **[OPEN QUESTION: PDF gives no number] RECOMMENDED DEFAULT:** ≤ 30s after all hidden-test executions complete, assuming provider responses arrive within their own timeout (NFR-... see Section 15). |
| NFR-005 | Performance | Live leaderboard updates within **≤ 10s** of a new score being finalized (poll interval or push). |
| NFR-006 | Scalability | System supports at least **50 concurrent teams** and **10 concurrent judges** for the MVP event size — **[ASSUMPTION, organizer should confirm actual headcount]**. |
| NFR-007 | Scalability | Prompt execution jobs are queued (not directly blocking the request thread) so a burst of simultaneous "Run" clicks during Round 2's live run-off doesn't degrade the API for everyone. |
| NFR-008 | Scalability | Database and application layers can each scale horizontally (stateless app servers behind a load balancer; Postgres read replica as a future option) without architectural rework. |
| NFR-009 | Scalability | The design supports adding more rounds/hackathons without schema changes (Round is a first-class, ordered entity — Section 12). |
| NFR-010 | Availability | The platform prioritizes high availability **during active rounds** specifically — **[PDF-instruction-derived]**; brief maintenance windows are acceptable only between rounds, scheduled and announced in advance. |
| NFR-011 | Availability | **[OPEN QUESTION: numeric SLA not given.] RECOMMENDED DEFAULT:** 99.5% uptime target during the live event window (not a year-round SaaS SLA — this is an event platform). |
| NFR-012 | Availability | Graceful degradation: if the AI provider is down, the rest of the platform (team mgmt, leaderboard, judging of already-executed submissions) remains usable. |
| NFR-013 | Reliability | No lost submissions: submission writes are transactional; a client-side network failure after the server commit must not be reported to the user as "failed" without the client re-checking submission status first (Section 19). |
| NFR-014 | Reliability | No duplicate submissions: enforced by a DB-level unique constraint on `(teamId, challengeId)` for `Submission`, not just application logic (belt-and-suspenders against race conditions — Edge Case, Section 21). |
| NFR-015 | Reliability | No incorrect scores: score writes are atomic; an evaluation is either fully recorded or not recorded at all, never partially. |
| NFR-016 | Reliability | Timer consistency: all round-timing decisions use server time exclusively (Section 19); client clocks are never trusted for lock/deadline enforcement. |
| NFR-017 | Reliability | No data corruption: use DB transactions for any multi-table write (e.g., submission + evaluation-trigger + audit log entry happen in one transaction or with reliable compensating logic). |
| NFR-018 | Security | All authentication uses hashed+salted passwords (bcrypt/argon2); tokens are short-lived JWTs (FR-006). |
| NFR-019 | Security | Authorization (RBAC + object-level checks) enforced server-side on every endpoint — never rely on the frontend hiding a button (Section 11, FR-005/FR-020/FR-058). |
| NFR-020 | Security | All inputs are validated and parameterized queries used throughout — no string-concatenated SQL (prevents SQL injection). |
| NFR-021 | Security | All user-generated content rendered in the UI (prompts, explanations, comments) is escaped/sanitized to prevent stored XSS. |
| NFR-022 | Security | CSRF protection on state-changing endpoints if cookie-based sessions are used; not required if using bearer-token auth exclusively — **[decide per Section 17 stack choice]**. |
| NFR-023 | Security | Rate limiting on auth endpoints (FR-009) and on AI execution endpoints (FR-050). |
| NFR-024 | Security | Secrets (AI provider API keys, DB credentials, JWT signing keys) are stored in a secrets manager/environment variables, never in source control or client bundles. |
| NFR-025 | Security | **AI provider API keys are never sent to or accessible from the frontend, under any circumstance** — explicitly emphasized in the source instructions; all AI calls are proxied through the backend's Prompt Execution Service (Section 15). |
| NFR-026 | Security | Hidden test case protection per Section 11's full threat model (FR-058–064). |
| NFR-027 | Security | Audit logs (Section 20) are append-only and admin-readable, not editable by any role including Admin (or editable only via a separately audited superuser path if absolutely required). |
| NFR-028 | Privacy | Personal data (name, email, affiliation) is used only for event operation, not shared with third parties beyond the AI provider (which only receives prompt text, not user PII, unless a prompt itself contains PII the user typed). |
| NFR-029 | Privacy | Submission content is visible only to the owning team, assigned judges, and Admins — never to other teams. |
| NFR-030 | Privacy | Judges' individual scores/comments are not visible to other judges before both have submitted, to avoid anchoring bias — **[PROPOSED]**. |
| NFR-031 | Privacy | Hidden test confidentiality per NFR-026. |
| NFR-032 | Privacy | Data retention: event data is retained for a defined period post-event (e.g., 90 days) then anonymized/purged unless the organizer opts to keep it — **[OPEN QUESTION, no retention policy in PDF; RECOMMENDED DEFAULT above]**. |
| NFR-033 | Maintainability | Backend organized into clear modules (Auth, Team, Hackathon, Round1, Round2, Execution, Evaluation, Judging, Leaderboard, Admin) with explicit interfaces between them (Section 16). |
| NFR-034 | Maintainability | Public APIs documented (OpenAPI/Swagger auto-generated from the framework, Section 13). |
| NFR-035 | Maintainability | Automated test suite (Section 22) required for all P0 requirements before merge. |
| NFR-036 | Observability | Structured application logs, error logs, AI-execution logs, submission logs, and audit logs are distinguishable streams (Section 20), with correlation IDs tying a user action to its downstream execution/evaluation records. |
| NFR-037 | Observability | Metrics/monitoring for AI provider error rate, execution queue depth, and API latency, with basic alerting for the live-event window — **[PROPOSED]**. |
| NFR-038 | Observability | Sensitive prompt/test content is not written to general-purpose application logs (Section 20) — only to access-controlled data stores. |

---

# 11. Security Requirements

This section consolidates the platform's security posture; individual controls are also referenced inline throughout Sections 5–10.

## 11.1 Threat model for hidden test cases (Instruction #7 — critical)
The single highest-risk area in this system is **participants discovering Round 2 hidden test inputs or expected answers**, since that would invalidate the entire "generalization vs. overfitting" pedagogical point of the round.

**Controls:**
1. **Storage isolation** — `TestCase.input`/`expectedOutput`/`evalRule` fields are only ever serialized into API responses for `Admin`/`Judge` (post-reveal or scoped) roles, enforced at the serializer layer (FR-058) so a future new endpoint can't accidentally leak them by omission.
2. **Execution isolation** — hidden inputs are sent to the AI provider by the *backend* only; they are never transmitted to, or executable from, the client (FR-059).
3. **Object-level authorization** — even an authenticated Participant token cannot fetch a `TestCase` by ID belonging to their own challenge (FR-062); IDs being guessable/enumerable must not matter.
4. **No timing/error side-channels** — error messages and response timing for "test not found" vs. "test hidden" must be indistinguishable, or an attacker could infer test existence/count via probing.
5. **No client-side "practice mode" that echoes hidden inputs** — any sandbox/practice execution feature (Future, Section 26) must use separate, clearly-non-scoring sample inputs, never real hidden `TestCase` rows.
6. **Audit everything** — every read attempt against hidden-test-adjacent endpoints by a non-privileged role is logged (even the denials), so any exploitation attempt is forensically visible after the fact.

## 11.2 General controls
- **RBAC** (FR-005) with object-level checks layered on top (a role check alone is insufficient — Section 11.1 point 3).
- **API security**: HTTPS everywhere, JWT bearer auth, input validation on every endpoint (Section 18), rate limiting (NFR-023).
- **Injection prevention**: parameterized queries (NFR-020), output-encoding to prevent XSS (NFR-021).
- **CSRF**: N/A if pure bearer-token auth with no cookies; required if session cookies are used (NFR-022) — decision deferred to Section 17.
- **Secrets management**: environment-injected secrets, rotated periodically; AI keys never exposed client-side (NFR-025).
- **Encryption**: TLS in transit; at-rest encryption for the database (managed-DB default) and for uploaded screenshots (object storage default encryption).
- **Prompt-injection awareness [PROPOSED]:** since participants' prompt text is fed to a real LLM, the Prompt Execution Service should not itself follow instructions embedded in a stored/executed prompt (e.g., a malicious prompt shouldn't be able to make the *platform's own* backend behave differently) — this is naturally satisfied as long as the backend only ever sends the prompt as a **data payload** to the AI Provider API and never interpolates it into anything the backend itself parses/executes (e.g., never `eval()`s model output).

---

# 12. Database / Data Model

## 12.1 Entity summary
All primary keys are UUIDs unless noted. Timestamps (`createdAt`, `updatedAt`) are implied on every table and omitted below for brevity.

### User
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| name | string | ✓ | |
| email | string | ✓ | unique |
| passwordHash | string | ✓ | never returned in any API response |
| status | enum(active,suspended) | ✓ | default active |
| affiliation | string | – | e.g., college/org |

### Role
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| userId | UUID | ✓ | FK → User |
| name | enum(participant,team_leader,judge,admin) | ✓ | a User can hold multiple Role rows (Section 4) |
| hackathonId | UUID | – | FK → Hackathon; null = global role (e.g., site Admin) |

### Team
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| hackathonId | UUID | ✓ | FK → Hackathon |
| name | string | ✓ | unique within hackathon |
| inviteCode | string | ✓ | unique |
| status | enum(forming,locked,active,completed) | ✓ | FR-017 |

### TeamMember
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| teamId | UUID | ✓ | FK → Team |
| userId | UUID | ✓ | FK → User |
| role | enum(leader,member) | ✓ | |
| Unique constraint | | | `(teamId, userId)`; also enforce "one active team per hackathon per user" at the app layer (Open Question, Section 5.3) |

### Hackathon
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| title | string | ✓ | |
| description | text | – | |
| startAt / endAt | datetime | ✓ | |
| registrationOpen | boolean | ✓ | FR-030 |
| status | enum(draft,active,ended) | ✓ | |
| minTeamSize / maxTeamSize | int | ✓ | defaults 1 / 4 |

### Round
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| hackathonId | UUID | ✓ | FK → Hackathon |
| type | enum(round1_fix_the_prompt, round2_constraint_challenge) | ✓ | extensible for future round types (Instruction #11) |
| order | int | ✓ | sequencing |
| startAt / durationSeconds | datetime/int | ✓ | server-authoritative timing (Section 19) |
| status | enum(draft,published,active,ended) | ✓ | FR-028 |

### Challenge *(shared parent concept)*
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| roundId | UUID | ✓ | FK → Round |
| type | enum(prompt_case, constraint_challenge) | ✓ | discriminator |
| status | enum(draft,published) | ✓ | |

### PromptCase *(Round 1 — extends Challenge 1:1)*
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK, FK → Challenge | |
| originalPrompt | text | ✓ | |
| badOutput | text | ✓ | |
| badOutputScreenshotUrl | string | – | FR-035 |
| brokenReason | enum (FR-034) | ✓ | evaluator/judge-only, never sent to Participant scope |
| difficulty | enum(easy,medium,hard) | ✓ | |
| expectedImprovementCharacteristics | jsonb | – | evaluator-only hints (FR-037) |

### Constraint *(Round 2)*
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| challengeId | UUID | ✓ | FK → Challenge (constraint_challenge) |
| type | enum (FR-053) | ✓ | max_tokens_n / zero_shot / one_shot / no_system_prompt / generalize_unseen_inputs / valid_json_always |
| maxTokens | int | – | used when type=max_tokens_n |
| taskDescription | text | ✓ | |
| formatRule | jsonb | – | JSON Schema or rule spec for FR-069/072 |

### TestCase
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| challengeId | UUID | ✓ | FK → Challenge |
| input | text | ✓ | **hidden by default** |
| expectedOutput | text/jsonb | – | **hidden**; may be null if `evalRule` is used instead (e.g., "valid JSON" rather than exact match) |
| evalRule | jsonb | – | e.g., `{type:"exact"}`, `{type:"schema", schema:{...}}` |
| visibility | enum(hidden,revealed) | ✓ | default hidden; FR-064 |

### PromptVersion
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| challengeId | UUID | ✓ | FK → Challenge |
| teamId | UUID | ✓ | FK → Team |
| versionNumber | int | ✓ | monotonically increasing per (challengeId, teamId) |
| promptText | text | ✓ | |
| systemPromptText | text | – | null where constraint forbids it (Round 2 `no_system_prompt`) |
| explanation | text | ✓ (Round 1) | FR-041's required "what changed / why" |
| isFinal | boolean | ✓ | FR-043 |
| createdByUserId | UUID | ✓ | FK → User |
| Unique | | | `(challengeId, teamId, versionNumber)` |

### Execution
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| promptVersionId | UUID | – | FK → PromptVersion (null if execution is ad hoc / not tied to a saved version) |
| submissionId | UUID | – | FK → Submission (set for hidden-test executions, FR-060) |
| testCaseId | UUID | – | FK → TestCase (set for hidden-test executions) |
| model | string | ✓ | which model/provider config was used |
| outputText | text | – | null on failure |
| status | enum(queued,running,success,error,timeout) | ✓ | |
| tokenCountPrompt / tokenCountOutput | int | – | |
| latencyMs | int | – | |

### Submission
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| challengeId | UUID | ✓ | FK → Challenge |
| teamId | UUID | ✓ | FK → Team |
| finalPromptVersionId | UUID | ✓ | FK → PromptVersion (Round 1) or the single submitted version (Round 2) |
| status | enum(submitted,locked) | ✓ | |
| constraintViolated | boolean | – | Round 2 only, FR-065 |
| submittedAt | datetime | ✓ | |
| Unique | | | `(challengeId, teamId)` — enforces "one submission" (NFR-014) |

### Evaluation
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| submissionId | UUID | ✓ | FK → Submission |
| type | enum(automated,human) | ✓ | |
| judgeUserId | UUID | – | FK → User; null for automated |
| status | enum(in_progress,submitted) | ✓ | FR-084/085 |

### Score
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| evaluationId | UUID | ✓ | FK → Evaluation |
| dimension | string | ✓ | e.g., `diagnosis_quality`, `test_pass_rate`, `constraint_compliance` (Section 9.1/9.2) |
| value | numeric | ✓ | 0–5 for human dims (FR-018 validated); 0–1 or 0–100 for automated ratio dims |
| comment | text | – | FR-083 |

### Leaderboard *(computed, not necessarily a physical table — see note)*
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| hackathonId | UUID | ✓ | FK → Hackathon |
| teamId | UUID | ✓ | FK → Team |
| round1Score / round2Score / totalScore | numeric | – | denormalized cache, recomputed on score change |
| rank | int | – | after tie-break rule (Section 5.6) |

**[ASSUMPTION]** `Leaderboard` is implemented as a materialized/cached view refreshed on score events, not a manually-written table, to avoid drift — modeled here as an entity per the requested data-model format, but the implementation is a derived cache.

### AuditLog
| Field | Type | Req | Notes |
|---|---|---|---|
| id | UUID | PK | |
| actorUserId | UUID | – | null for system-initiated events |
| action | string | ✓ | e.g., `team.lock_override`, `testcase.write`, `score.enter` |
| targetType / targetId | string / UUID | ✓ | polymorphic reference |
| metadata | jsonb | – | never includes hidden test content or raw passwords/keys (Section 20) |
| createdAt | datetime | ✓ | append-only |

## 12.2 Relationship overview
`Hackathon 1—N Round 1—N Challenge`. `Challenge` is specialized 1:1 into either `PromptCase` (Round 1) or paired with one `Constraint` + N `TestCase` (Round 2). `Team N—N User` via `TeamMember`. `Team 1—N PromptVersion` per `Challenge` (the Original→Final chain). `Submission` points to exactly one `PromptVersion` (the final one) and fans out to N `Execution` rows (one per hidden `TestCase` for Round 2, or the ad hoc preview executions for Round 1) and N `Evaluation` rows (one automated + one per assigned Judge), each `Evaluation` fanning out to N `Score` rows (one per rubric dimension). `Leaderboard` rows are derived from aggregated `Score` rows per team per hackathon.

---

# 13. API Specification

All endpoints are prefixed `/api/v1`. Auth: `Bearer <JWT>` unless marked public. Standard error envelope: `{ "error": { "code": string, "message": string } }`. Common status codes (401 unauthenticated, 403 unauthorized, 404 not found, 409 conflict, 422 validation, 423 locked, 429 rate-limited, 500 server error) apply platform-wide per Section 19 and are not repeated per row below unless the case is endpoint-specific.

### Authentication APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /auth/register | Public | FR-001 |
| POST | /auth/login | Public | FR-002 |
| POST | /auth/logout | Bearer | FR-003 |
| POST | /auth/refresh | Refresh token | rotate access token |
| POST | /auth/password-reset/request | Public | FR-004 |
| POST | /auth/password-reset/confirm | Public (reset token) | FR-004 |

### User APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | /users/me | Bearer | current profile + roles |
| PATCH | /users/me | Bearer | update profile |
| PATCH | /users/{id}/status | Admin | FR-007 suspend/reinstate |
| POST | /users/{id}/roles | Admin | FR-010 grant role |

### Team APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /teams | Bearer | FR-011 |
| POST | /teams/join | Bearer | FR-012 (body: inviteCode) |
| GET | /teams/{id} | Bearer (member/Admin) | FR-021 |
| POST | /teams/{id}/invite-code/regenerate | Team Leader | FR-013 |
| DELETE | /teams/{id}/members/{userId} | Team Leader/Admin | FR-014 |
| DELETE | /teams/{id}/members/me | Bearer (member) | leave team, FR-014 |
| PATCH | /teams/{id}/leader | System/Admin | FR-015 |
| GET | /hackathons/{id}/teams | Admin | FR-022 |
| DELETE | /teams/{id} | Admin | FR-019 |

### Hackathon APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /hackathons | Admin | FR-023 |
| PATCH | /hackathons/{id} | Admin | FR-024 |
| POST | /hackathons/{id}/activate | Admin | FR-025 |
| GET | /hackathons/{id} | Bearer | public-safe hackathon detail |
| GET | /hackathons/{id}/stats | Admin | FR-031 |

### Round APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /hackathons/{id}/rounds | Admin | FR-026 |
| PATCH | /rounds/{id} | Admin | FR-027/028 |
| POST | /rounds/{id}/publish | Admin | FR-029 |
| POST | /rounds/{id}/start | Admin | FR-105 |
| POST | /rounds/{id}/pause | Admin | FR-106 |
| POST | /rounds/{id}/end | Admin | FR-107 |
| GET | /rounds/{id}/timer | Bearer | server-authoritative remaining time (Section 19) |

### Challenge APIs (Round 1 & 2)
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /rounds/{id}/prompt-cases | Admin | FR-033 |
| PATCH | /prompt-cases/{id} | Admin | edit case |
| POST | /prompt-cases/{id}/publish | Admin | FR-039 |
| GET | /prompt-cases/{id} | Bearer (role-filtered per FR-040) | field set differs by role |
| POST | /rounds/{id}/constraint-challenges | Admin | FR-051 |
| PATCH | /constraint-challenges/{id} | Admin | edit |
| POST | /constraint-challenges/{id}/test-cases | Admin | FR-063 (Admin-only write) |
| POST | /constraint-challenges/{id}/publish | Admin | publish |
| GET | /constraint-challenges/{id} | Bearer (role-filtered — hidden fields stripped per FR-058) | |

### Prompt Version APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /challenges/{id}/prompt-versions | Team member | FR-041 |
| GET | /challenges/{id}/prompt-versions | Team member/Judge/Admin | FR-042 |
| PATCH | /prompt-versions/{id}/mark-final | Team member | FR-043 |

### Submission APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /challenges/{id}/submissions | Team member | FR-044 (Round 1) / FR-065 (Round 2) |
| GET | /submissions/{id} | Team member (own)/Judge (assigned)/Admin | role-scoped detail |
| GET | /challenges/{id}/submissions | Admin | FR-032 monitoring |

### Execution APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /prompt-versions/{id}/execute | Team member | FR-046 preview run |
| GET | /executions/{id} | owner/Admin/Judge | poll execution status/result (FR-049) |

### Evaluation APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | /judges/me/assignments | Judge | FR-102 |
| POST | /evaluations/{submissionId}/scores | Judge | FR-082 |
| POST | /evaluations/{id}/submit | Judge | FR-084 |
| PATCH | /evaluations/{id}/scores | Judge (pre-lock) | FR-085 |
| POST | /submissions/{id}/assign-judge | Admin | judge assignment (FR-096) |
| GET | /rounds/{id}/evaluations/progress | Admin | FR-096 progress panel |

### Leaderboard APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | /hackathons/{id}/leaderboard | Bearer/Public (Admin toggle) | FR-087–091 |
| POST | /hackathons/{id}/results/publish | Admin | gates FR-101/FR-115 |
| GET | /hackathons/{id}/results/export | Admin | FR-097 CSV/JSON |

### Admin APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | /admin/health | Admin | FR-098 |
| GET | /admin/audit-log | Admin | Section 20 |
| POST | /admin/teams/{id}/unlock-override | Admin | FR-018 override, audit-logged |

---

# 14. Frontend Requirements

| # | Page | Purpose | Key Components | User Actions | API Deps | Validation | Error States |
|---|---|---|---|---|---|---|---|
| 1 | Login | Authenticate | Email/password form | Submit login | POST /auth/login | Required fields | "Invalid credentials," lockout notice |
| 2 | Registration | Create account | Name/email/password/affiliation form | Submit registration | POST /auth/register | Email format, password strength | "Email already registered" |
| 3 | Dashboard (role-routed) | Landing hub | Current hackathon card, team card, active-round card, timer | Navigate to round/team | GET /users/me, /hackathons/{id} | – | "No active hackathon" empty state |
| 4 | Team Management | Form/join/manage team | Create-team form, invite code, roster list | Create, join, invite, remove, leave | Team APIs | Name uniqueness, size limits | "Team full," "already on a team," "teams locked" |
| 5 | Hackathon Lobby | Overview before rounds start | Hackathon info, countdown to Round 1, team status | View only | GET /hackathons/{id}, /rounds/{id}/timer | – | "Registration closed" |
| 6 | Round 1 Challenge | View assigned case | Original prompt panel, bad output panel, case description | Proceed to editor | GET /prompt-cases/{id} | Round-active gate | "Round not started/ended" |
| 7 | Prompt Editor | Core editing surface (Section 25) | Text areas, token counter, constraint indicator, Run button, output panel, explanation field, Save/Submit | Edit, run, save version, submit | PromptVersion + Execution APIs | Non-empty prompt/explanation (Round 1), constraint checks (Round 2, client-side convenience only) | "Explanation required," "constraint violated (will still submit, flagged)," execution timeout/error |
| 8 | Version History | Review iteration chain | Timeline list: version, prompt, explanation, output, timestamp | View diffs | GET /prompt-versions | – | Empty state before first version |
| 9 | Round 2 Challenge | View task+constraint | Task description, constraint badge, visible example(s) if any | Proceed to editor | GET /constraint-challenges/{id} | – | "Round not started/ended" |
| 10 | Submission Page | Finalize Round 2 prompt | Final prompt readonly-preview, explanation field, Submit (irreversible) confirmation | Confirm submit | POST /submissions | Confirm dialog ("cannot be changed") | 409 already submitted |
| 11 | Results | Personal/team result view | Score summary (post-publish), Round 1/2 breakdown, judge comments (post-publish) | View only | GET /submissions/{id}, /leaderboard | – | "Results not yet published" |
| 12 | Leaderboard | Live rankings | Ranked table, round-wise columns, tie-break note | Filter/sort | GET /leaderboard | – | Empty state pre-Round-1 |
| 13 | Judge Dashboard | Assignment queue | Pending/completed lists, submission viewer, rubric, score form | Score, comment, finalize | Evaluation APIs | Score range 0–5 | "Already evaluated," out-of-range value |
| 14 | Admin Dashboard | Central control | Overview cards, round control, challenge mgmt, judging oversight, results panel | All Admin actions | Admin/Hackathon/Round/Challenge APIs | Role-gated UI + server-enforced | 403 for non-admin, config validation errors |
| 15 | Challenge Management | Author cases/challenges | Case form, constraint config form, hidden test-case table | CRUD cases/challenges/tests | Challenge/TestCase APIs | One-shot/zero-shot example-count rule, ≥3 hidden tests | 422 validation messages (FR-051) |
| 16 | Evaluation Screen (Admin view) | Oversight of judging | Per-judge progress, score-disagreement flags, verification | Review, flag, override | /rounds/{id}/evaluations/progress | – | – |

**Cross-cutting rule (Section 25):** all constraint/format/permission checks shown in the frontend are UX conveniences only; every one of them is re-validated authoritatively server-side before anything is persisted or scored (NFR-019, FR-065 alt flow).

---

# 15. AI Execution Architecture

## 15.1 Flow
```
Frontend (Prompt Editor)
      |  (prompt text only — no API key ever present client-side, NFR-025)
      v
Backend API  (auth + RBAC + input validation, Section 11)
      v
Prompt Execution Service
      |  - selects model/config per Round/Hackathon setting (FR-047)
      |  - applies timeout + retry policy
      |  - enqueues job (async worker/queue, NFR-007) for anything not needed synchronously
      v
AI Provider Adapter  (interface: execute(systemPrompt, userPrompt, model, params) -> {output, tokens, latency, error})
      v
LLM API (OpenAI / Anthropic / other — pluggable, not hardcoded)
      v
Evaluation Engine  (Section 8: format/constraint/expected-answer checks run on the returned output)
      v
Database  (Execution + Evaluation rows persisted)
```

## 15.2 Provider abstraction
A single interface is implemented per provider so the platform is never hard-wired to one vendor:
```
interface AIProviderAdapter {
  execute(input: {
    systemPrompt?: string,
    userPrompt: string,
    model: string,
    maxTokens?: number
  }): Promise<{
    outputText: string,
    tokenCountPrompt: number,
    tokenCountOutput: number,
    latencyMs: number,
    status: "success" | "error" | "timeout"
  }>
}
```
Swapping providers (or supporting several simultaneously, e.g., different models per challenge) means adding a new adapter implementation, with zero changes to Prompt Execution Service, Evaluation Engine, or any API/route code above it. **[PROPOSED architecture pattern — PDF does not specify a provider, and the accompanying instructions explicitly require this abstraction.]**

## 15.3 Cross-cutting concerns
- **API key management:** stored server-side only (env/secrets manager), injected into the adapter at call time; never logged, never returned in any API response (NFR-025).
- **Timeout:** a hard per-call timeout (e.g., 20–30s **[OPEN QUESTION: exact value not specified; RECOMMENDED DEFAULT 25s]**) so a hung provider call can't hold a job/worker indefinitely.
- **Retry:** limited automatic retry (e.g., 1 retry) only on transient/network errors, never on the provider's own content/safety rejections (retrying those wastes cost and won't change the outcome).
- **Rate limiting:** both an outbound cap (protect the platform's own provider quota/cost, FR-050) and respecting the provider's own rate-limit responses with backoff.
- **Token tracking:** every `Execution` row records prompt/output token counts (used for FR-054's constraint validation and for cost monitoring).
- **Error handling:** provider errors are translated into the platform's generic `Execution.status` enum; raw provider error text is logged server-side only, never surfaced verbatim to end users (avoids leaking provider-specific implementation details and matches Section 19's "user-friendly" requirement).
- **Logging:** execution attempts are logged with correlation IDs (NFR-036), excluding full hidden-test input/output content from general logs where that content is sensitive (Section 20).
- **Cost control:** per-team execution rate limits (FR-050), a fixed model per round (FR-047) to avoid unpredictable per-call cost variance, and Admin visibility into aggregate token usage (Phase 2 dashboard widget — **[PROPOSED]**).

---

# 16. System Architecture

## 16.1 Option A — Modular Monolith
Single deployable backend service, internally organized into the modules from NFR-033, sharing one database, with a background worker process (or in-process async queue for MVP scale) for AI execution jobs.
**Pros:** one deployment pipeline, one place to reason about transactions (critical for NFR-013–017's "no lost/duplicate/incorrect" guarantees), far less operational overhead, easy for a small team to build and debug under a hackathon-prep timeline.
**Cons:** all modules scale together (acceptable at NFR-006's target scale); a bug in one module can theoretically affect the whole process (mitigated by good module boundaries and tests).

## 16.2 Option B — Microservices
Separate services per module (Auth service, Team service, Execution service, Evaluation service, etc.) communicating over a network/message bus.
**Pros:** independent scaling and deployment; matches very large, multi-team organizations.
**Cons:** dramatically higher operational complexity (service discovery, distributed transactions/sagas for things like "submission → trigger execution → trigger evaluation," network failure handling everywhere), far more infrastructure to run correctly during a live, time-boxed event — the worst time to be debugging a distributed-systems issue.

## 16.3 Recommendation
**Modular Monolith**, per Instruction #5 ("architecture that a small student/hackathon development team can actually implement") and the master prompt's own explicit steer ("Do NOT unnecessarily recommend microservices if a modular monolith is sufficient"). The system's actual scale (NFR-006: ~50 teams, one live event at a time) does not need independent service scaling, and the correctness guarantees the PDF cares most about (no lost submissions, accurate scores, protected hidden tests) are *easier* to guarantee inside one transactional boundary than across a distributed system. Clean module boundaries (NFR-033) keep the door open to extracting a service later (e.g., the Prompt Execution Service, since it's the most naturally async/scalable piece) without a full rewrite.

## 16.4 Component layout
- **Frontend:** Next.js SPA/SSR app, calling the backend over REST.
- **Backend:** single modular-monolith API service (Section 17 for language/framework choice).
- **Database:** PostgreSQL (relational integrity matters a lot here — unique constraints for NFR-014, foreign keys throughout Section 12).
- **AI Service layer:** in-process Prompt Execution Service + Provider Adapter (Section 15), backed by a lightweight job queue (Redis-backed, e.g., RQ/BullMQ/Celery depending on stack) for async execution so API requests aren't blocked on LLM latency.
- **Evaluation Engine:** in-process module (Section 8), triggered synchronously after automated-checkable executions complete.
- **Authentication:** JWT-based, in-process (Section 4/11), no separate identity provider needed at MVP scale — **[OPEN QUESTION: SSO via college/org login? RECOMMENDED DEFAULT: out of scope for MVP, Phase 2 if requested.]**
- **Deployment:** containerized (Docker) app + worker, managed Postgres, managed Redis; any mainstream PaaS/cloud works (Section 17).
- **Storage:** object storage (S3-compatible) for uploaded bad-output screenshots (FR-035).
- **Monitoring:** centralized structured logs + a basic metrics/alerting layer (NFR-037), scoped to be "enough for a live event," not enterprise-grade observability.

---

# 17. Recommended Tech Stack

| Layer | Recommendation | Alternatives | Why |
|---|---|---|---|
| Frontend | **Next.js (React, TypeScript)** | Vue/Nuxt, plain React+Vite | Component reuse across 16 pages (Section 14), strong ecosystem for forms/tables/real-time updates, easy to deploy, large talent pool for a student team. |
| Backend | **FastAPI (Python)** | Node.js/NestJS, Spring Boot | Async-first (fits Section 15's non-blocking AI calls well), Pydantic gives free request/response validation (directly supports Section 18), auto-generated OpenAPI docs (NFR-034), and Python's ecosystem is the path of least resistance for anything AI/LLM-SDK related. Node/NestJS is an equally valid alternative if the team is stronger in TypeScript end-to-end; Spring Boot is heavier than this project needs. |
| Database | **PostgreSQL** | MySQL | Strong relational integrity (foreign keys, unique constraints) directly needed for NFR-014/015/017; JSONB support fits flexible fields like `expectedImprovementCharacteristics`/`evalRule`/`formatRule`. |
| Cache / Queue | **Redis** | RabbitMQ, SQS | Doubles as job queue (execution jobs, Section 15) and cache (leaderboard, Section 5.6) with one piece of infrastructure — minimizes ops overhead per Instruction #5. |
| AI Provider(s) | **Provider-agnostic adapter (Section 15)**, e.g., supporting Anthropic and/or OpenAI APIs | Any LLM vendor | Explicitly required by the accompanying instructions ("do not assume a specific AI provider unless necessary"); exact provider(s) is an **[OPEN QUESTION]** for the organizer to decide based on budget/access. |
| Containerization | **Docker** (+ docker-compose for local dev) | – | Standard, matches Section 16's deployment layout. |
| Deployment | **Any cloud-ready PaaS** (e.g., Render/Railway/Fly.io for speed, or AWS/GCP if the org already has infra) | – | **[OPEN QUESTION: organizer's existing infra/budget not known.] RECOMMENDED DEFAULT:** a PaaS for the MVP to minimize DevOps burden; migrate to raw cloud only if scale/cost demands it. |
| Auth | JWT via backend framework's built-in auth (e.g., FastAPI + `python-jose`/`fastapi-users`) | Auth0/Clerk (managed) | In-house JWT is sufficient and free at this scale (NFR-006); a managed auth provider is a reasonable **[PROPOSED, Phase 2]** swap if SSO becomes a requirement. |

**Prioritization rationale (per Instruction #5/#28 constraints — easy development, fast implementation, reliability, maintainability, low ops complexity):** every choice above favors "boring, well-documented, one-service" technology over anything requiring specialized ops knowledge, consistent with a modular monolith built by a small team on an event deadline.

---

# 18. Validation Rules

| Rule | Applies To | Enforcement |
|---|---|---|
| Prompt length (non-empty, reasonable max e.g. 10,000 chars) | Prompt text fields | Server-side, on save |
| Token count vs. constraint (FR-054) | Round 2 submissions | Server-side, authoritative; client shown as convenience only |
| Required fields (explanation on Round 1 versions, task description on challenges, etc.) | Multiple forms | Server-side 422 with field-level messages |
| Submission deadline | Round 1/2 submit endpoints | Server time only (Section 19); reject with 423 past deadline |
| User permissions (RBAC) | Every endpoint | Middleware/decorator per role, plus object-level checks (Section 11) |
| Team membership | Team-scoped actions | Verify `TeamMember` row exists before allowing access |
| JSON output validity | `valid_json_always` constraint challenges | JSON.parse + optional schema validation (FR-072) |
| Constraint compliance | Round 2 submissions | Per-type validator (FR-073); non-blocking per FR-065's Open Question default (flag + penalize, don't hard-reject) |
| Duplicate submission | Submission endpoint | DB unique constraint `(challengeId, teamId)` (NFR-014) + app-level 409 |
| Hidden test access | Any TestCase-adjacent read | Role + object-level check (FR-058/062), fails closed |
| Judge score ranges | Score entry | 0–5 integer, server-validated (FR-082), never trust client range enforcement |

---

# 19. Error Handling

| Scenario | User Sees | Backend Does |
|---|---|---|
| AI API failure | "The model couldn't generate a response — you can try again." | Logs full provider error server-side; `Execution.status=error`; does not retry content/safety rejections. |
| Timeout | "The model took too long to respond — try again." | `Execution.status=timeout`; releases the request/worker slot; allows retry (subject to rate limit, FR-050). |
| Invalid prompt (empty/oversize) | Inline field error, "prompt cannot be empty / exceeds max length." | 422, no DB write. |
| Invalid JSON output (constraint check) | "Output did not meet the required JSON format" (shown as evaluation feedback, not a hard block on saving a version) | `formatCompliant=false` stored; participant may keep iterating (Round 1) — for Round 2 this is scored, not blocking. |
| Token limit exceeded | Live counter turns red + warning banner; submission still allowed (per FR-065 default) but flagged | `constraintViolated=true` persisted; scoring engine penalizes accordingly. |
| Submission after deadline | "This round has ended — submissions are closed." | 423; server time check; no row created. |
| Unauthorized access | "You don't have permission to view this." (generic — no resource-existence hint for hidden data, Section 11) | 403/404 as appropriate; logged (FR-008). |
| Server failure (5xx) | Generic "something went wrong, please try again" + support/contact note | Full stack trace logged server-side with correlation ID; never exposed to client. |
| Database failure | Same generic 5xx message | Transaction rolled back cleanly; no partial writes (NFR-017). |
| Duplicate request (e.g., double-click submit) | Second click either no-ops or shows "already submitted" | Idempotency via unique constraint (NFR-014) + idempotency key on the client request where feasible. |
| Network failure mid-submit | Client shows "connection lost — checking submission status…" and re-queries before telling the user it failed | Client re-fetches submission status rather than assuming failure and re-submitting blindly (prevents false "it didn't work" duplicate attempts). |

---

# 20. Audit & Logging

## 20.1 What is logged
| Event | Logged Fields |
|---|---|
| Login (success/failure) | userId (if known), timestamp, IP, result |
| Team creation/join/leave/removal | actorUserId, teamId, targetUserId, action |
| Challenge assignment | teamId, challengeId, timestamp |
| Prompt version creation | teamId, challengeId, versionNumber, createdByUserId (not full prompt text in the *audit* log — see 20.2) |
| Prompt execution | executionId, model, status, latency, tokens (not full output text in the audit log) |
| Submission | submissionId, teamId, challengeId, timestamp |
| Judge evaluation (score entry, submit, edit) | evaluationId, judgeUserId, submissionId, action |
| Score changes | evaluationId, dimension, old value → new value (edits only) |
| Round start/end/pause | roundId, actorUserId (Admin) or `system` |
| Admin configuration changes | entity, field, old→new, actorUserId |
| Denied access to hidden-test-adjacent endpoints | actorUserId, endpoint, targetId, timestamp — **especially important per Section 11.1** |
| Lock overrides (team unlock, submission unlock) | actorUserId, targetId, reason, timestamp |

## 20.2 What is NOT logged (or is access-controlled separately)
- Full prompt/output text and hidden `TestCase` content are **not** written into the general-purpose audit/application log stream (NFR-038); they live only in their proper access-controlled tables (`PromptVersion`, `Execution`, `TestCase`), queried through normal RBAC-checked endpoints.
- AI provider API keys, password hashes, and JWT signing secrets are never logged anywhere, under any circumstance (NFR-024/025).
- Judges' private disagreement/deliberation is not logged as a cross-judge-visible event (NFR-030).

---

# 21. Edge Cases

| # | Scenario | Expected Behavior |
|---|---|---|
| 1 | User joins multiple teams | Blocked at the app layer (Open Question, Section 5.3 default: one active team per hackathon); joining a second team while already on one returns 409. |
| 2 | Team leader leaves | If before lock: remaining members are prompted to elect a new leader (FR-015); if none remain, team auto-dissolves (status → a terminal "abandoned" state, submissions if any are preserved for audit). If after lock: leaving is blocked entirely (FR-018) — the leader can be reassigned by Admin only. |
| 3 | User submits at exact deadline | Server compares the request's arrival timestamp (not the client's claimed time) against `Round.endAt`; a request that reaches the server before the deadline succeeds even if processing finishes a moment after — the *request time*, not the *response time*, is authoritative. |
| 4 | AI API times out | Handled per Section 19's timeout row; user can retry within rate limits. |
| 5 | Prompt contains malicious instructions (e.g., an attempted prompt injection against the platform itself) | The backend never executes or interprets model output as code/instructions to itself (Section 11.2) — it is only ever displayed as text and evaluated as data, so this has no privileged effect regardless of content. |
| 6 | Prompt exceeds token limit | Per FR-065 default: submission is still accepted, flagged `constraintViolated=true`, and penalized by the scoring engine rather than silently blocked. |
| 7 | Participant attempts to access a hidden test case (via UI or direct API call) | 403/404 (indistinguishable, Section 11.1) at every layer; attempt is audit-logged. |
| 8 | Judge submits an invalid score (e.g., out of 0–5 range) | 422, no partial write; the whole evaluation submission is atomic (FR-082). |
| 9 | Two judges score the same submission | Both `Evaluation` rows persist independently; final dimension score = average, with a disagreement flag above a configurable threshold surfaced to Admin (Section 9.3 Open Question default). |
| 10 | Duplicate API request (e.g., retry after a slow network) | Unique constraints (NFR-014) + idempotent handling prevent a second row; the duplicate call returns the existing resource's status (409 or 200-with-existing-id, implementation's choice) rather than erroring destructively. |
| 11 | Browser refresh during submission | Client re-checks submission status on reload rather than assuming loss (Section 19); if the server already committed it, the UI shows "already submitted." |
| 12 | Network disconnect during submission | Same as #11 — client reconciles against server state before prompting the user to retry, to avoid an accidental duplicate. |
| 13 | Round ends while an AI execution is still running | The execution is allowed to complete and is still recorded (for audit/judge review), but it does **not** extend the round or count toward a late submission — the submission itself must have been received before `Round.endAt` (see #3) independent of when its triggered execution finishes. |
| 14 | Server clock differs from client clock | Irrelevant to correctness by design — every timing decision (round lock, deadline, timer display) is computed server-side and pushed to the client (Section 19); the client clock is used only for smooth local countdown animation between server syncs, never for enforcement. |

---

# 22. Testing Strategy

| # | Type | Focus | Key Scenarios |
|---|---|---|---|
| 22.1 | Unit Testing | Individual functions/validators | Token counter accuracy; each constraint validator (FR-073); JSON schema validator; tie-break comparator. |
| 22.2 | Integration Testing | Module-to-module interaction within the monolith | Submission → triggers hidden-test execution → triggers automated evaluation → updates leaderboard cache, all within one flow. |
| 22.3 | API Testing | Endpoint contracts | Every RBAC/object-level rule (Section 11) has a negative test (wrong-role call returns 403, not 200-with-empty-data); every validation rule (Section 18) has a boundary test. |
| 22.4 | Frontend Testing | UI logic | Prompt editor's live token counter matches backend calculation on a sample set; constraint-violation banner renders correctly; submit-confirmation dialog blocks accidental double-submit. |
| 22.5 | AI Execution Testing | Provider adapter behavior | Adapter correctly handles success, timeout, and error responses from a mocked provider; retry logic fires exactly once for transient errors and never for content-rejection errors. |
| 22.6 | Security Testing | Auth/RBAC/injection | Attempt SQL injection via prompt/explanation fields (must fail); attempt XSS via stored comment fields (must be escaped on render); brute-force login lockout (FR-009). |
| 22.7 | Load Testing | Concurrency at NFR-006 scale | Simulate the Round 2 live "run-off" — many teams submitting near-simultaneously; confirm no duplicate submissions and execution queue drains within SLA (NFR-004). |
| 22.8 | End-to-End Testing | Full user journeys | A full Round 1 journey (register → team → open case → iterate 3 versions → submit → judge scores → leaderboard updates) and a full Round 2 journey (submit → hidden execution → auto-score → leaderboard) run against a staging environment. |
| 22.9 | Hidden Test Security | Section 11 threat model | Automated contract test, run in CI on every deploy, asserting that **no** Participant-scoped API response anywhere in the system contains a hidden `TestCase.input`/`expectedOutput` field (FR-058's acceptance criterion, elevated to a standing CI gate rather than a one-time manual check). |
| 22.10 | Competition Timing Testing | Server-authoritative timers | Verify round lock/end fires based on server time even when a test client's system clock is deliberately skewed; verify a submission arriving 1ms before `endAt` succeeds and 1ms after is rejected (Edge Case #3). |

---

# 23. User Stories

*(Selected stories carry explicit acceptance criteria; the rest are included for completeness of coverage across all five roles.)*

## Participant
1. **As a Participant**, I want to see the original broken prompt and its bad output clearly, so that I can diagnose what's wrong before I start editing. *(AC: opening a case shows prompt + output + neutral description, and never the internal broken-reason tag — FR-040.)*
2. **As a Participant**, I want to write a one-line explanation with every prompt version, so that my reasoning is preserved for judging. *(AC: saving a version without an explanation is rejected — FR-041.)*
3. **As a Participant**, I want to run my draft prompt and see the output before finalizing a version, so that I can validate my fix works.
4. **As a Participant**, I want a live token counter in Round 2, so that I know if I'm within the 50-token limit before I submit. *(AC: counter matches the server's authoritative count within a defined tolerance — FR-054.)*
5. **As a Participant**, I want to see only my hidden-test pass count ("4/5"), not the actual hidden inputs, so that the competition stays fair for everyone including me. *(AC: FR-061.)*

## Team Leader
6. **As a Team Leader**, I want to invite teammates with a code, so that we can compete together. *(AC: FR-012/013.)*
7. **As a Team Leader**, I want the roster to lock once the round starts, so that no one can add outside help mid-competition. *(AC: FR-018.)*
8. **As a Team Leader**, I want to see our full version history across the team, so I can review teammates' contributions before submitting.

## Judge
9. **As a Judge**, I want to see only the submissions assigned to me, so I'm not overwhelmed and stay within my scope. *(AC: FR-077/102.)*
10. **As a Judge**, I want the rubric visible next to the scoring form, so I score consistently with the stated criteria. *(AC: FR-086.)*
11. **As a Judge**, I want to be prevented from seeing hidden test answers for tests not yet revealed, so that I can't accidentally bias future judging or leak them. *(AC: same enforcement as FR-058, scoped to Judge role, Section 9.3.)*

## Organizer
12. **As an Organizer**, I want to configure a round's start time and duration once and trust the platform to enforce it, so I don't have to manually track timing across many teams. *(AC: FR-105–107, Section 19.)*
13. **As an Organizer**, I want a live view of submission counts and judging progress, so I know whether the event is on schedule. *(AC: FR-032/096.)*
14. **As an Organizer**, I want to reveal hidden test cases after the round ends, so teams can learn from what they missed. *(AC: FR-064, opt-in only.)*

## Admin
15. **As an Admin**, I want to author broken-prompt cases with a bad output and a broken-reason tag, so Round 1 matches the format the guest lecture used. *(AC: FR-033/034.)*
16. **As an Admin**, I want the system to reject publishing a Round 2 challenge with fewer than 3 hidden test cases, so I can't accidentally under-configure a live challenge. *(AC: FR-051.)*
17. **As an Admin**, I want an audit log of every score change and every lock override, so any dispute after the event can be resolved from evidence, not memory. *(AC: Section 20.)*

---

# 24. Use Cases

*(Compact format: Actor / Precondition / Main Flow / Postcondition. Full BDD-style detail for the underlying FRs is in Sections 5–9.)*

1. **Participant Registration** — Actor: visitor. Precondition: hackathon registration open. Flow: submit form → validate → create User → confirm. Postcondition: User exists, can log in. (FR-001)
2. **Team Creation** — Actor: Participant. Precondition: not already on a team. Flow: submit name → create Team+leader TeamMember → return invite code. Postcondition: Team exists in `forming` status. (FR-011)
3. **Joining Hackathon (via Team)** — Actor: Participant. Precondition: has an invite code. Flow: enter code → validate capacity/status → create TeamMember. Postcondition: user appears in roster. (FR-012)
4. **Starting Round 1** — Actor: Admin (trigger), System (effect). Precondition: Round 1 published. Flow: Admin clicks Start → Round.status=active → Team.status=locked for all teams → timer begins. Postcondition: participants can open their assigned case. (FR-105/FR-018)
5. **Improving a Prompt** — Actor: Team member. Precondition: case opened. Flow: edit prompt → optionally run it → write explanation → save. Postcondition: new PromptVersion row appended. (FR-041)
6. **Creating Prompt Versions** — same as #5, repeated N times, each producing an immutable, ordered version. (FR-041/042)
7. **Executing a Prompt** — Actor: Team member (trigger), System (effect). Precondition: rate limit not exceeded. Flow: send prompt → Prompt Execution Service calls AI Provider Adapter → capture output/tokens/latency. Postcondition: Execution row persisted, output shown to user. (FR-046)
8. **Submitting Round 1** — Actor: Team member. Precondition: at least one version marked Final. Flow: click submit → Submission row created (locked) → automated evaluation queued (Section 8) → judge assignment queued (Section 9). Postcondition: no further versions can be added for that case/team. (FR-044)
9. **Starting Round 2** — same pattern as #4, for the Round 2 challenge. (FR-105)
10. **Submitting Final Prompt (Round 2)** — Actor: Team member. Precondition: no prior submission for this challenge. Flow: confirm final prompt → server validates constraint → Submission row created and locked → hidden-test execution triggered. Postcondition: exactly one immutable Submission exists. (FR-065)
11. **Hidden Test Execution** — Actor: System. Precondition: Submission created. Flow: for each hidden TestCase, execute the submitted prompt server-side, capture output, compare to `expectedOutput`/`evalRule`. Postcondition: N Execution rows + pass/fail per test, aggregated into `passedCount`. (FR-060)
12. **Automated Scoring** — Actor: System. Precondition: hidden-test execution complete (Round 2) or submission received (Round 1 format checks). Flow: run format/constraint/expected-answer validators → write automated `Evaluation`/`Score` rows. Postcondition: `autoScore` available to feed the leaderboard and to inform judges. (FR-069–076)
13. **Judge Evaluation** — Actor: Judge. Precondition: submission assigned to this judge. Flow: open Submission Viewer (hidden-safe) → enter rubric scores + comments → submit evaluation (locks it). Postcondition: human `Evaluation`/`Score` rows recorded; feeds leaderboard. (FR-082/084)
14. **Leaderboard Generation** — Actor: System. Precondition: at least one finalized Evaluation exists. Flow: aggregate automated + human `Score` rows per team per round → apply weights (Section 13/Section 5.6) → apply tie-break rule → cache/update `Leaderboard` rows. Postcondition: ranked leaderboard available via API. (FR-087)
15. **Ending the Hackathon** — Actor: Admin. Precondition: all rounds ended, judging locked. Flow: Admin publishes results (`POST /results/publish`) → Results/Published notification fires (FR-115) → participant Results pages unlock (FR-101). Postcondition: `Hackathon.status=ended`, final leaderboard is the permanent record.

---

# 25. MVP Scope

## MVP (required to run one live event)
Auth (register/login/logout, RBAC — FR-001–008, 010) · Team create/join/lock (FR-011,012,016–018,020) · Hackathon+Round CRUD/publish/start/end (FR-023–029,105–110) · Round 1 case authoring + full participant iteration workflow + execution (FR-033–050) · Round 2 challenge/constraint/hidden-test authoring + one-shot locked submission + hidden-test execution (FR-051–068) · Automated evaluation for format/constraint/expected-answer (FR-069–075) · Human judging with rubric (FR-077–086) · Leaderboard with round breakdown + tie-break (FR-087–090) · Participant/Judge/Admin dashboards (core panels only) · Server-authoritative timer (Section 19) · Core security/audit controls (Section 11, Section 20) · In-app submission-confirmation notification only (FR-113).

## Phase 2
Email/push notifications (FR-111,112,114,115 beyond in-app) · Score-weight configuration UI (FR-092/057) · Post-round hidden-test reveal UI polish (FR-064 exists in MVP as a toggle; richer reveal UI is Phase 2) · Judge disagreement-flagging dashboard (Section 9.3) · Admin re-run-automated-evaluation tool (FR-076) · CSV/JSON export polish (FR-097) · Invite-only/pre-loaded registration (FR-001 Open Question) · Aggregate token-usage/cost dashboard (Section 15.3).

## Future
Additional round types beyond Round 1/2 (architecture supports it — NFR-009) · Multiple simultaneous hackathons/multi-tenant orgs · Practice/sandbox mode with non-scoring sample inputs (must never reuse real hidden TestCase rows — Section 11.1) · Prompt-version diff/comparison UI · Participant-selectable models (FR-047) · SSO login · Real-time collaborative co-editing (beyond last-write-wins, FR-045) · Advanced analytics/insights for organizers.

---

# 26. Future Enhancements
*(Consolidated from "Phase 2"/"Future" above and from `[PROPOSED, Phase 2/Future]` tags throughout this document — not repeated verbatim here; see Section 25 for the authoritative list.)*

---

# 27. Requirement Traceability Matrix

| PDF Concept | Requirement ID(s) | Feature | MVP? |
|---|---|---|---|
| 3–5 broken-prompt cases, easy→hard | FR-033, FR-036 | Case authoring + difficulty | Yes |
| Original bad prompt + bad output (screenshot/text) | FR-033, FR-035 | Case content fields | Yes |
| Underlying reason the prompt is broken | FR-034 | Broken-reason taxonomy | Yes |
| Teams pick one case / rotate through 2–3 | FR-038 | Case selection config | Yes |
| Iterative rewriting: Original → v2 → v3 → Final | FR-041–043 | Prompt version history | Yes |
| One-line "what changed / why it helped" per iteration | FR-041 (explanation field, required) | Explanation enforcement | Yes |
| Judging: correct diagnosis | Section 9.1 rubric, FR-082 | Diagnosis-quality score | Yes |
| Judging: meaningful, explainable improvement per iteration | Section 9.1 rubric | Improvement-quality score | Yes |
| Judging: final output quality vs. original | Section 9.1 rubric, FR-043 (mark final) | Final-output-quality score | Yes |
| Judging: documentation clarity | Section 9.1 rubric | Documentation-clarity score | Yes |
| Judges/lecturer read out submissions live | Spectator role (Section 4), FR-081 output viewer | Live readout support | Phase 2 (dedicated projector view) |
| Same fixed task + same constraint for all teams | FR-051 | Constraint challenge creation | Yes |
| Six constraint types (tokens, zero/one-shot, no system prompt, unseen-input generalization, valid JSON) | FR-053, FR-073 | Constraint enum + validators | Yes |
| 3–5 hidden test inputs, same for all teams | FR-051, FR-058–064 | Hidden TestCase system | Yes |
| One final prompt — no iteration during scoring | FR-065 (unique constraint, immediate lock) | Single-submission enforcement | Yes |
| Live "run-off" — transparent shared execution | FR-060, Admin submission-monitoring (FR-032) | Live hidden-test execution + monitoring | Yes (live view is MVP; polished spectator display is Phase 2) |
| Judging: % test cases passed | FR-074, Section 9.2 | Automated pass-rate scoring | Yes |
| Judging: constraint compliance ("did they cheat?") | FR-073, Section 9.2 | Automated constraint validators | Yes |
| Judging: technique used, briefly explained | FR-066, Section 9.2 human dimension | Explanation field + human score | Yes |
| "Passed: 4/5" without revealing hidden details | FR-061 | Disclosure-limited result payload | Yes |
| Reveal hidden tests only if organizer chooses, after the round | FR-064 | Post-round reveal toggle | Yes |
| Tie-breaking rule | *(not in PDF)* | FR-090 + Section 5.6 default | Yes — **[ASSUMPTION]** |
| Numeric scoring scale/weights | *(not in PDF)* | Section 9 default (0–5, equal weight) | Yes — **[ASSUMPTION]** |
| Team size limits | *(not in PDF)* | FR-016 default (min 1, max 4) | Yes — **[ASSUMPTION]** |
| Accounts/roles/teams-as-software | *(not in PDF — event logistics only)* | Sections 4–5 in full | Yes — **[PROPOSED]** |

---

# 28. Development Roadmap

| Phase | Tasks | Dependencies | Expected Output | Definition of Done |
|---|---|---|---|---|
| 1. Project Setup | Repo scaffold, CI pipeline, Docker Compose (app+db+redis), base FastAPI/Next.js skeletons | None | Runnable local dev environment | `docker compose up` boots all services; CI runs lint+test on push |
| 2. Auth & Roles | FR-001–010 | Phase 1 | Register/login/logout/RBAC middleware | 22.3/22.6 auth+security tests pass |
| 3. Team Management | FR-011–022 | Phase 2 | Team CRUD, invite, lock | 22.2/22.3 tests pass; Edge Cases #1,#2 covered |
| 4. Hackathon/Round Management | FR-023–032, FR-105–110 | Phase 2 | Hackathon/Round CRUD, server-authoritative timer | 22.10 timing tests pass |
| 5. Round 1 | FR-033–050 (case authoring, iteration workflow, execution) | Phases 2–4, Section 15 (Execution Service) | Full Round 1 flow, end to end | 22.8 Round 1 E2E passes |
| 6. Round 2 | FR-051–068 (constraint config, hidden tests, submission) | Phase 5 (shares Execution Service) | Full Round 2 flow, end to end | 22.8 Round 2 E2E passes; 22.9 hidden-test-security CI gate green |
| 7. AI Execution | Section 15 (Provider Adapter, queue-backed Execution Service) | Phase 1 | Provider-agnostic execution layer used by Phases 5–6 | 22.5 adapter tests pass with a mocked provider |
| 8. Evaluation & Scoring | FR-069–086 (Sections 8–9) | Phases 5–7 | Automated + human evaluation, rubric-driven scoring | Score correctness tests (22.1–22.3) pass |
| 9. Leaderboard | FR-087–092 | Phase 8 | Live, tie-break-aware leaderboard | NFR-005 update-latency verified under 22.7 load test |
| 10. Testing | Full Section 22 suite | All prior phases | Complete automated test suite in CI | All P0 requirements have passing tests; 22.9 gate enforced on every deploy |
| 11. Deployment | Containerize, provision managed Postgres/Redis, configure secrets (NFR-024/025), deploy | Phase 10 | Live staging + production environment | NFR-010/011 availability checks pass; a full dry-run event executes cleanly end to end |

---

# 29. Definition of Done

A requirement/feature is "done" only when **all** of the following hold:
1. Server-side validation implemented for every rule in Section 18 relevant to it (never frontend-only).
2. RBAC + object-level authorization enforced and covered by a negative test (Section 22.3).
3. Automated tests exist per Section 22 for the relevant layer(s) and pass in CI.
4. For anything touching hidden test data: the Section 22.9 CI gate passes.
5. For anything touching timing/deadlines: the Section 22.10 server-authoritative timing test passes.
6. Error handling matches Section 19 (correct user-facing message + correct backend/logging behavior).
7. Relevant audit events are emitted per Section 20.
8. API contract documented (auto-generated OpenAPI, NFR-034).
9. No secrets, hidden-test content, or raw provider errors are exposed to the client (NFR-024/025/038 verified).
10. Acceptance criteria stated for the requirement (Sections 5–9) are demonstrably met in a staging environment, not just unit-tested in isolation.

---

# 30. Open Questions & Assumptions

## Open Questions (with recommended defaults — all need organizer confirmation before launch)
1. Is registration self-service or invite-only? → Default: self-service, closeable via toggle. (Section 5.2)
2. Team size limits? → Default: min 1, max 4. (FR-016)
3. Can a team edit/add Round 1 versions after submitting? → Default: no, Admin-override only. (Section 6.2)
4. Should an over-limit Round 2 prompt be rejected outright or accepted-and-penalized? → Default: accepted, flagged, scored down. (FR-065)
5. Can multiple Round 2 constraints combine on one challenge? → Default: no, one constraint per challenge for MVP. (FR-053)
6. How are multiple judges' scores combined? → Default: average per dimension, with a disagreement flag. (Section 9.3)
7. Tie-breaking order? → Default: Round 2 % passed → Round 1 human score → earlier final-submission timestamp. (Section 5.6)
8. Numeric scoring scale? → Default: 0–5 integer per dimension, equal weighting. (Section 9)
9. Automated evaluation SLA? → Default: ≤30s after hidden-test executions complete. (NFR-004)
10. Uptime SLA during the event? → Default: 99.5% during active-round windows only. (NFR-011)
11. Data retention period post-event? → Default: 90 days, then anonymize/purge unless organizer opts to retain. (NFR-032)
12. AI provider timeout value? → Default: 25 seconds per call. (Section 15.3)
13. Concurrent scale (teams/judges) to design for? → Default: 50 teams / 10 judges. (NFR-006) — **organizer should confirm actual expected headcount.**
14. Which LLM provider(s) will actually be used, and who bears the API cost? → Not specified in the PDF; architecture is provider-agnostic so this can be decided independently (Section 15).
15. Is SSO (college/org login) required? → Default: out of scope for MVP. (Section 16.4)

## Assumptions (stated as such throughout, consolidated here)
- Every round activity is team-based, even if a team can have exactly one member (Section 4).
- One active team per user per hackathon (Section 5.3).
- Exactly one hackathon is "publicly active" at a time (FR-025).
- `Leaderboard` is implemented as a derived/cached view, not a hand-maintained table (Section 12.1).
- The platform runs a single live event at a time at MVP scale, not a multi-tenant SaaS (Sections 16–17).
- Anything about accounts, roles, database, APIs, and dashboards in this document is a software translation of the PDF's event design, not a requirement stated in the PDF itself (Section 2.2) — flagged as **[PROPOSED]** throughout rather than attributed to the source.
