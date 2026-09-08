/* ==========================================================================
   NEURA JUDGE DASHBOARD - PROMPT FIXING ARENA OPERATIONS
   Lifecycle Control (Start, End, Release Results), 5-Criteria Rubric Scoring,
   Anti-Cheat Proctoring Audit, and Tie-Broken Podium Standings
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';

let activeJudgeTab = 'scoring'; // 'scoring' | 'security' | 'leaderboard'
let selectedArenaSubId = null;
let currentRubric = {
  clarity_score: 2,
  context_score: 2,
  specificity_score: 2,
  output_structure_score: 2,
  relevance_score: 2,
  feedback: ''
};
let judgeOverviewCache = null;

export async function renderJudgeDashboard() {
  const container = document.getElementById('page-judge-dashboard');
  if (!container) return;

  // Load fresh arena judge overview
  const res = await store.getArenaJudgeOverview();
  if (res.success) {
    judgeOverviewCache = res;
  }

  const arenaStatus = judgeOverviewCache?.arena_config?.status || 'waiting';
  const isResultsReleased = judgeOverviewCache?.arena_config?.is_results_released || false;
  const submissions = judgeOverviewCache?.submissions || [];
  const metrics = judgeOverviewCache?.metrics || {
    total_teams: 0,
    total_submissions: 0,
    evaluated_submissions: 0,
    pending_evaluations: 0,
    flagged_teams_count: 0
  };

  // Select first submission if none selected or invalid
  if ((!selectedArenaSubId || !submissions.some(s => s.id === selectedArenaSubId)) && submissions.length > 0) {
    selectedArenaSubId = submissions[0].id;
  }

  const selectedSub = submissions.find(s => s.id === selectedArenaSubId);
  if (selectedSub && selectedSub.evaluation) {
    currentRubric = {
      clarity_score: selectedSub.evaluation.clarity_score,
      context_score: selectedSub.evaluation.context_score,
      specificity_score: selectedSub.evaluation.specificity_score,
      output_structure_score: selectedSub.evaluation.output_structure_score,
      relevance_score: selectedSub.evaluation.relevance_score,
      feedback: selectedSub.evaluation.feedback || ''
    };
  }

  const statusBadge = arenaStatus === 'live' ? '<span class="chip chip-cyan" style="animation:pulse-glow 1.5s infinite;">● LIVE ARENA</span>'
                    : arenaStatus === 'completed' ? '<span class="chip chip-violet">■ ARENA COMPLETED</span>'
                    : arenaStatus === 'results_available' || isResultsReleased ? '<span class="chip chip-green">✓ RESULTS RELEASED</span>'
                    : '<span class="chip chip-amber">⏳ WAITING FOR START</span>';

  container.innerHTML = `
    <!-- Top Header & Lifecycle Operations Bar -->
    <div class="glass bracket-frame mb-4" style="padding:22px 28px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
        <div>
          <div class="eyebrow" style="margin-bottom:4px;">JUDGE & DIRECTOR CONTROL CONSOLE // PROMPT FIXING ARENA</div>
          <h1 class="heading-lg" style="margin:0; font-size:24px;">ARENA OPERATIONS & EVALUATION</h1>
        </div>

        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="mono-text" style="font-size:11px; color:var(--muted);">STATUS:</span>
            ${statusBadge}
          </div>

          <!-- Operation Action Buttons -->
          <div style="display:flex; gap:8px; align-items:center;">
            <button class="btn btn-sm btn-primary" id="btnJudgeStartArena" ${arenaStatus === 'live' ? 'disabled' : ''} style="padding:6px 14px; font-size:11px;">
              ▶ START ARENA
            </button>
            <button class="btn btn-sm btn-red" id="btnJudgeEndArena" ${arenaStatus !== 'live' ? 'disabled' : ''} style="padding:6px 14px; font-size:11px;">
              ■ END ARENA
            </button>
            <button class="btn btn-sm btn-violet" id="btnJudgeReleaseResults" ${isResultsReleased ? 'disabled' : ''} style="padding:6px 14px; font-size:11px;">
              📢 RELEASE RESULTS
            </button>
            <button class="btn btn-sm btn-red" id="btnJudgeLogout" style="padding:6px 14px; font-size:11px; font-weight:700; margin-left:4px;">
              ⎋ LOGOUT
            </button>
          </div>
        </div>
      </div>

      <!-- Quick Metrics Counters -->
      <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:12px; margin-top:20px; padding-top:16px; border-top:1px solid var(--line);">
        <div class="glass-card" style="padding:10px 14px; text-align:center;">
          <div class="mono-text" style="font-size:10.5px; color:var(--muted);">TEAMS</div>
          <div class="heading-md" style="color:var(--cyan); margin-top:2px;">${metrics.total_teams}</div>
        </div>
        <div class="glass-card" style="padding:10px 14px; text-align:center;">
          <div class="mono-text" style="font-size:10.5px; color:var(--muted);">TOTAL SUBMISSIONS</div>
          <div class="heading-md" style="color:var(--text); margin-top:2px;">${metrics.total_submissions}</div>
        </div>
        <div class="glass-card" style="padding:10px 14px; text-align:center;">
          <div class="mono-text" style="font-size:10.5px; color:var(--muted);">EVALUATED</div>
          <div class="heading-md" style="color:var(--green); margin-top:2px;">${metrics.evaluated_submissions}</div>
        </div>
        <div class="glass-card" style="padding:10px 14px; text-align:center;">
          <div class="mono-text" style="font-size:10.5px; color:var(--muted);">PENDING</div>
          <div class="heading-md" style="color:var(--amber); margin-top:2px;">${metrics.pending_evaluations}</div>
        </div>
        <div class="glass-card" style="padding:10px 14px; text-align:center;">
          <div class="mono-text" style="font-size:10.5px; color:var(--muted);">FLAGGED TEAMS</div>
          <div class="heading-md" style="color:${metrics.flagged_teams_count > 0 ? 'var(--red)' : 'var(--text)'}; margin-top:2px;">
            ${metrics.flagged_teams_count}
          </div>
        </div>
      </div>
    </div>

    <!-- Judge Navigation Tabs -->
    <div style="display:flex; gap:10px; margin-bottom:20px;">
      <button class="btn btn-sm ${activeJudgeTab === 'scoring' ? 'btn-primary' : ''}" id="tabBtnScoring" style="padding:8px 18px;">
        1. SUBMISSIONS & 5-CRITERIA RUBRIC
      </button>
      <button class="btn btn-sm ${activeJudgeTab === 'security' ? 'btn-primary' : ''}" id="tabBtnSecurity" style="padding:8px 18px;">
        2. SECURITY & PROCTORING AUDIT (${judgeOverviewCache?.security_events?.length || 0})
      </button>
      <button class="btn btn-sm ${activeJudgeTab === 'leaderboard' ? 'btn-primary' : ''}" id="tabBtnLeaderboard" style="padding:8px 18px;">
        3. OFFICIAL STANDINGS & PODIUM
      </button>
    </div>

    <!-- TAB 1: RUBRIC SCORING QUEUE -->
    <div id="judgeTabContentScoring" style="display:${activeJudgeTab === 'scoring' ? 'block' : 'none'};">
      <div style="display:grid; grid-template-columns: 0.95fr 1.45fr; gap:24px;">
        
        <!-- Left: Submissions Queue -->
        <div class="glass bracket-frame" style="padding:22px;">
          <span class="bl"></span><span class="br"></span>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <div class="queue-eyebrow">CHALLENGE SUBMISSIONS (${submissions.length})</div>
            <span class="mono-text" style="font-size:10px; color:var(--muted);">AUTO-SYNC</span>
          </div>

          <div class="judge-queue-container" style="max-height:640px; overflow-y:auto; display:flex; flex-direction:column; gap:10px;">
            ${submissions.length === 0 ? `
              <div style="color:var(--muted); font-size:12.5px; font-family:var(--mono); padding:20px; text-align:center;">
                No submissions received yet. When teams submit challenges, they will appear here in real time.
              </div>
            ` : ''}

            ${submissions.map(sub => {
              const isSelected = sub.id === selectedArenaSubId;
              const isEvaluated = !!sub.is_evaluated;
              const timeStr = sub.submitted_at ? new Date(sub.submitted_at).toLocaleTimeString() : 'N/A';

              return `
                <div class="judge-queue-card ${isSelected ? 'selected' : ''}" onclick="window.selectArenaSub('${sub.id}')" style="cursor:pointer; padding:14px; border:1px solid ${isSelected ? 'var(--cyan)' : 'var(--line)'}; border-radius:4px; background:${isSelected ? 'rgba(0,243,255,0.06)' : 'rgba(255,255,255,0.02)'};">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <strong style="font-family:var(--disp); font-size:14px; color:var(--text);">${escapeHtml(sub.team_name)}</strong>
                    <span class="chip chip-cyan" style="font-size:9.5px; padding:2px 6px;">CHALLENGE ${sub.challenge_index}</span>
                  </div>
                  <div class="mono-text" style="font-size:11px; color:var(--muted); margin-bottom:8px;">
                    ${escapeHtml(sub.challenge_title)} &bull; Submitted at ${timeStr}
                  </div>
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="chip chip-${isEvaluated ? 'green' : 'amber'}" style="font-size:9px; padding:2px 6px;">
                      ${isEvaluated ? `✓ SCORED (${sub.evaluation.total_score}/10)` : '⏳ PENDING'}
                    </span>
                    <span class="mono-text" style="font-size:10.5px; color:var(--cyan);">Inspect &rarr;</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <!-- Right: Submission Inspector & Rubric Evaluation Form -->
        ${selectedSub ? `
          <div style="display:flex; flex-direction:column; gap:20px;">
            
            <!-- Solution Inspection Panel -->
            <div class="glass bracket-frame" style="padding:24px;">
              <span class="bl"></span><span class="br"></span>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div>
                  <div class="eyebrow" style="margin-bottom:2px;">SUBMISSION INSPECTOR // ${escapeHtml(selectedSub.team_name)}</div>
                  <h3 class="heading-md" style="font-size:16px;">Challenge ${selectedSub.challenge_index}: ${escapeHtml(selectedSub.challenge_title)}</h3>
                </div>
                <span class="chip chip-${selectedSub.challenge_difficulty === 'hard' ? 'violet' : 'cyan'}">
                  ${selectedSub.challenge_difficulty ? selectedSub.challenge_difficulty.toUpperCase() : 'MEDIUM'}
                </span>
              </div>

              <!-- Original Flawed Prompt -->
              <div style="margin-bottom:14px;">
                <div class="eyebrow" style="margin-bottom:4px; color:var(--red);">Original Flawed Prompt</div>
                <div class="evidence-block" style="font-size:12px; max-height:85px; border-color:rgba(255,0,85,0.3); background:rgba(255,0,85,0.03);">
                  ${escapeHtml(selectedSub.flawed_prompt)}
                </div>
              </div>

              <!-- Team's Fixed Solution -->
              <div style="margin-bottom:14px;">
                <div class="eyebrow" style="margin-bottom:4px; color:var(--cyan);">Team's Refactored Solution</div>
                <div class="evidence-block" style="font-size:12.5px; max-height:160px; border-color:var(--cyan); background:rgba(0,243,255,0.04); color:var(--text); font-family:var(--mono);">
                  ${escapeHtml(selectedSub.fixed_prompt)}
                </div>
              </div>

              <!-- Diagnosis Rationale Notes (if provided) -->
              ${selectedSub.diagnosis_notes ? `
                <div style="margin-bottom:8px;">
                  <div class="eyebrow" style="margin-bottom:4px; color:var(--amber);">Team's Stated Rationale</div>
                  <div class="glass-card" style="padding:10px; font-size:12px; color:var(--text); font-style:italic;">
                    "${escapeHtml(selectedSub.diagnosis_notes)}"
                  </div>
                </div>
              ` : ''}
            </div>

            <!-- Official 5-Criteria Rubric Scoring Form (0–2 scale per criteria, 10 max) -->
            <div class="glass bracket-frame" style="padding:24px;">
              <span class="bl"></span><span class="br"></span>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div>
                  <div class="eyebrow" style="margin-bottom:2px;">OFFICIAL 5-CRITERIA RUBRIC FORM</div>
                  <div class="heading-md" style="font-size:15px;">EVALUATION SCORE SCALE (0, 1, 2 PER CRITERION)</div>
                </div>
                <div class="glass-card" style="padding:8px 16px; text-align:center; border-color:var(--cyan);">
                  <div class="eyebrow" style="margin-bottom:2px;">TOTAL SCORE</div>
                  <div class="heading-md" style="color:var(--cyan); font-size:22px;" id="rubricTotalReadout">
                    ${calculateCurrentRubricTotal()} / 10
                  </div>
                </div>
              </div>

              <!-- 5 Rubric Criteria Cards -->
              <div style="display:flex; flex-direction:column; gap:12px; margin-bottom:18px;">
                ${renderRubricCriterionRow('clarity_score', '1. Clarity & Objective Formulation', 'Did the team provide crystal-clear directives and unambiguous task framing?', currentRubric.clarity_score)}
                ${renderRubricCriterionRow('context_score', '2. Context & Framing', 'Did they specify realistic persona, relevant constraints, and operational context?', currentRubric.context_score)}
                ${renderRubricCriterionRow('specificity_score', '3. Specificity & Constraint Enforcement', 'Did they introduce robust guardrails against hallucinations and off-topic outputs?', currentRubric.specificity_score)}
                ${renderRubricCriterionRow('output_structure_score', '4. Output Structuring & Formatting', 'Is output specified with machine-parseable schema (e.g. JSON, exact bullet count)?', currentRubric.output_structure_score)}
                ${renderRubricCriterionRow('relevance_score', '5. Domain Relevance & Tone', 'Does the prompt maintain appropriate industry tone, domain terminology, and persona?', currentRubric.relevance_score)}
              </div>

              <!-- Constructive Judge Feedback -->
              <div class="field" style="margin-bottom:20px;">
                <label>Constructive Judge Feedback <span style="color:var(--muted); font-weight:normal;">(Included in participant's educational performance report)</span></label>
                <textarea id="judgeFeedbackInput" rows="3" placeholder="Highlight key strengths and specific improvement recommendations...">${escapeHtml(currentRubric.feedback)}</textarea>
              </div>

              <!-- Save Score Action -->
              <div style="display:flex; justify-content:flex-end;">
                <button class="btn btn-primary" id="btnSaveRubricScore" style="padding:10px 24px;">
                  ${selectedSub.is_evaluated ? 'UPDATE EVALUATION (LOCK)' : 'SUBMIT & LOCK EVALUATION →'}
                </button>
              </div>

            </div>

          </div>
        ` : `
          <div class="glass bracket-frame" style="padding:48px; text-align:center; color:var(--muted);">
            <span class="bl"></span><span class="br"></span>
            <div style="font-size:36px; margin-bottom:12px;">📋</div>
            <div class="heading-md" style="margin-bottom:6px;">NO SUBMISSION SELECTED</div>
            <p class="sub-text">Select a challenge submission from the queue on the left to inspect and evaluate.</p>
          </div>
        `}

      </div>
    </div>

    <!-- TAB 2: SECURITY & PROCTORING AUDIT -->
    <div id="judgeTabContentSecurity" style="display:${activeJudgeTab === 'security' ? 'block' : 'none'};">
      <div class="glass bracket-frame" style="padding:24px;">
        <span class="bl"></span><span class="br"></span>
        <div class="eyebrow" style="margin-bottom:4px;">ANTI-CHEAT TELEMETRY AUDIT</div>
        <h2 class="heading-md" style="margin-bottom:16px;">PROCTORING LOG & INTEGRITY FLAGS</h2>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-bottom:24px;">
          ${(judgeOverviewCache?.flagged_teams || []).map(ft => `
            <div class="glass-card" style="padding:16px; border-left:4px solid var(--red);">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <strong style="color:var(--red); font-size:14px;">⚠️ ${escapeHtml(ft.team_name)}</strong>
                <span class="chip chip-red">${ft.violation_count} VIOLATIONS</span>
              </div>
              <div class="mono-text" style="font-size:11px; color:var(--muted); line-height:1.5;">
                Flagged for suspicious tab switches or window blur events exceeding the proctoring threshold (&ge;3).
              </div>
            </div>
          `).join('')}

          ${(!judgeOverviewCache?.flagged_teams || judgeOverviewCache.flagged_teams.length === 0) ? `
            <div class="glass-card" style="padding:16px; border-left:4px solid var(--green); grid-column: 1 / -1;">
              <span class="chip chip-green" style="margin-bottom:4px;">✓ INTEGRITY CLEAN</span>
              <div style="font-size:13px; color:var(--text); margin-top:4px;">No participating teams have breached the proctoring violation threshold.</div>
            </div>
          ` : ''}
        </div>

        <!-- Security Event Timeline Table -->
        <table class="lb-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Team Name</th>
              <th>Event Type</th>
              <th>Proctoring Details</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            ${(judgeOverviewCache?.security_events || []).map(ev => {
              const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : 'N/A';
              const isCrit = ev.event_type === 'TAB_SWITCH' || ev.event_type === 'COPY_ATTEMPT';
              return `
                <tr>
                  <td class="mono-text" style="font-size:11.5px; color:var(--muted);">${timeStr}</td>
                  <td style="font-weight:600; color:var(--text);">${escapeHtml(ev.team_name)}</td>
                  <td><span class="chip chip-${isCrit ? 'red' : 'amber'}" style="font-size:10px;">${escapeHtml(ev.event_type)}</span></td>
                  <td class="mono-text" style="font-size:11px; color:var(--muted);">${escapeHtml(JSON.stringify(ev.metadata || {}))}</td>
                  <td><span style="color:${isCrit ? 'var(--red)' : 'var(--amber)'}; font-size:11px; font-weight:bold;">${isCrit ? 'FLAGGED' : 'AUDITED'}</span></td>
                </tr>
              `;
            }).join('')}
            ${(!judgeOverviewCache?.security_events || judgeOverviewCache.security_events.length === 0) ? `
              <tr><td colspan="5" style="text-align:center; color:var(--muted); padding:20px;">No proctoring telemetry events recorded yet.</td></tr>
            ` : ''}
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: OFFICIAL STANDINGS & PODIUM -->
    <div id="judgeTabContentLeaderboard" style="display:${activeJudgeTab === 'leaderboard' ? 'block' : 'none'};">
      <div id="judgeLeaderboardContainer">
        <!-- Loaded asynchronously -->
      </div>
    </div>
  `;

  // Attach Top Operations Handlers
  setupArenaOperationsHandlers(arenaStatus);

  // Attach Tab Switching Handlers
  document.getElementById('tabBtnScoring')?.addEventListener('click', () => {
    activeJudgeTab = 'scoring';
    renderJudgeDashboard();
  });
  document.getElementById('tabBtnSecurity')?.addEventListener('click', () => {
    activeJudgeTab = 'security';
    renderJudgeDashboard();
  });
  document.getElementById('tabBtnLeaderboard')?.addEventListener('click', () => {
    activeJudgeTab = 'leaderboard';
    renderJudgeDashboard();
    loadLeaderboardTab();
  });

  if (activeJudgeTab === 'leaderboard') {
    loadLeaderboardTab();
  }

  // Attach Rubric Scoring Handlers
  setupRubricScoringHandlers(selectedSub);
}

function calculateCurrentRubricTotal() {
  return (
    (currentRubric.clarity_score || 0) +
    (currentRubric.context_score || 0) +
    (currentRubric.specificity_score || 0) +
    (currentRubric.output_structure_score || 0) +
    (currentRubric.relevance_score || 0)
  );
}

function renderRubricCriterionRow(key, title, description, currentVal) {
  return `
    <div class="rubric-card" style="padding:14px; border:1px solid var(--line); border-radius:4px; background:rgba(255,255,255,0.015);">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div style="max-width:70%;">
          <div style="font-weight:600; font-size:13px; color:var(--text);">${escapeHtml(title)}</div>
          <div style="font-size:11.5px; color:var(--muted); margin-top:2px;">${escapeHtml(description)}</div>
        </div>
        <div class="rubric-score-pills" style="display:flex; gap:6px;">
          ${[0, 1, 2].map(score => `
            <button class="rubric-pill ${score === currentVal ? 'selected' : ''}" 
                    type="button"
                    onclick="window.selectRubricPill('${key}', ${score})"
                    style="min-width:42px; padding:6px 12px; font-family:var(--mono); font-size:12px; font-weight:bold; cursor:pointer;">
              ${score}
            </button>
          `).join('')}
        </div>
      </div>
    </div>
  `;
}

function setupRubricScoringHandlers(selectedSub) {
  window.selectArenaSub = (id) => {
    selectedArenaSubId = id;
    renderJudgeDashboard();
  };

  window.selectRubricPill = (key, val) => {
    currentRubric[key] = val;
    const fb = document.getElementById('judgeFeedbackInput');
    if (fb) currentRubric.feedback = fb.value;

    const totalReadout = document.getElementById('rubricTotalReadout');
    if (totalReadout) {
      totalReadout.textContent = `${calculateCurrentRubricTotal()} / 10`;
    }

    renderJudgeDashboard();
  };

  document.getElementById('btnSaveRubricScore')?.addEventListener('click', async (e) => {
    if (!selectedSub) return;
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = 'SAVING SCORE...';

    const feedback = document.getElementById('judgeFeedbackInput')?.value.trim() || null;
    currentRubric.feedback = feedback;

    const payload = {
      submission_id: selectedSub.id,
      clarity_score: currentRubric.clarity_score,
      context_score: currentRubric.context_score,
      specificity_score: currentRubric.specificity_score,
      output_structure_score: currentRubric.output_structure_score,
      relevance_score: currentRubric.relevance_score,
      feedback: feedback
    };

    const res = await store.scoreArenaSubmission(payload);
    if (res.success) {
      Router.showToast(`Challenge evaluation saved (${calculateCurrentRubricTotal()}/10)!`, 'green');
      await renderJudgeDashboard();
    } else {
      btn.disabled = false;
      btn.textContent = 'SUBMIT & LOCK EVALUATION →';
      Router.showToast(res.error || 'Failed to save evaluation', 'red');
    }
  });
}

function setupArenaOperationsHandlers(arenaStatus) {
  // 1. START ARENA
  document.getElementById('btnJudgeStartArena')?.addEventListener('click', () => {
    showSafetyConfirmModal(
      'START PROMPT FIXING ARENA?',
      'Are you sure you want to trigger the authoritative start? All registered teams will immediately receive their deterministic 5-challenge sequence, and proctoring telemetry will become active.',
      'START COMPETITION NOW ▶',
      async () => {
        const res = await store.startArena(60);
        if (res.success) {
          Router.showToast('Arena is now LIVE for all participants!', 'green');
          await renderJudgeDashboard();
        } else {
          Router.showToast(res.error || 'Failed to start arena', 'red');
        }
      }
    );
  });

  // 2. END ARENA
  document.getElementById('btnJudgeEndArena')?.addEventListener('click', () => {
    showSafetyConfirmModal(
      'END ARENA COMPETITION?',
      'Ending the arena will close submissions for all teams and lock current progress. Are you sure you want to end Round 1?',
      'END ARENA ■',
      async () => {
        const res = await store.endArena();
        if (res.success) {
          Router.showToast('Arena ended. Final evaluations can now be completed.', 'violet');
          await renderJudgeDashboard();
        } else {
          Router.showToast(res.error || 'Failed to end arena', 'red');
        }
      }
    );
  });

  // 3. RELEASE RESULTS
  document.getElementById('btnJudgeReleaseResults')?.addEventListener('click', () => {
    showSafetyConfirmModal(
      'RELEASE OFFICIAL RESULTS & REPORTS?',
      'Releasing results will immediately unlock educational performance reports and official podium standings for all participating teams. This action is irreversible.',
      'RELEASE RESULTS 📢',
      async () => {
        const res = await store.releaseArenaResults();
        if (res.success) {
          Router.showToast('Official arena results and reports have been released!', 'green');
          await renderJudgeDashboard();
        } else {
          Router.showToast(res.error || 'Failed to release results', 'red');
        }
      }
    );
  });

  // 4. LOGOUT
  document.getElementById('btnJudgeLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out as Evaluation Judge will end your scoring and evaluation session.');
  });
}

async function loadLeaderboardTab() {
  const container = document.getElementById('judgeLeaderboardContainer');
  if (!container) return;

  container.innerHTML = `<div style="padding:20px; text-align:center; color:var(--muted);" class="mono-text">Loading official standings...</div>`;

  const rows = await store.getArenaLeaderboard();
  const top3 = rows.slice(0, 3);

  container.innerHTML = `
    <!-- Top 3 Podium Cards -->
    ${top3.length > 0 ? `
      <div class="podium-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:20px; margin-bottom:28px;">
        ${top3.map((team, idx) => {
          const podiumClass = idx === 0 ? 'gold' : idx === 1 ? 'silver' : 'bronze';
          const medal = idx === 0 ? '🥇 1ST PLACE' : idx === 1 ? '🥈 2ND PLACE' : '🥉 3RD PLACE';
          return `
            <div class="podium-card ${podiumClass}">
              <div class="podium-rank ${podiumClass}">${medal}</div>
              <h3 style="font-family:var(--disp); font-size:18px; margin:8px 0 4px 0; color:var(--text);">${escapeHtml(team.team_name)}</h3>
              <div class="mono-text" style="font-size:11px; color:var(--muted); margin-bottom:12px;">${escapeHtml(team.college || 'Engineering Institute')}</div>
              <div style="font-size:26px; font-weight:800; font-family:var(--disp); color:var(--cyan);">
                ${team.total_score} <span style="font-size:14px; font-weight:normal; color:var(--muted);">/ 50</span>
              </div>
              <div class="mono-text" style="font-size:10.5px; color:var(--muted); margin-top:6px;">
                Solved: ${team.challenges_completed}/5 &bull; Completed: ${team.completed_at ? new Date(team.completed_at).toLocaleTimeString() : 'In Progress'}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    ` : ''}

    <!-- Complete Standings Table with Tie-Breaking Details -->
    <div class="glass bracket-frame" style="padding:24px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <div>
          <div class="eyebrow">OFFICIAL ARENA STANDINGS</div>
          <h2 class="heading-md" style="font-size:16px;">TIE-BROKEN LEADERBOARD (SCORE DESC &rarr; SUBMISSION TIME ASC)</h2>
        </div>
        <button class="btn btn-sm btn-primary" onclick="window.renderJudgeDashboard()">REFRESH STANDINGS ⟳</button>
      </div>

      <table class="lb-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Team Name</th>
            <th>College</th>
            <th>Solved</th>
            <th>Total Score</th>
            <th>Server Tie-Breaker (Completion Time)</th>
            <th>Security Status</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row, idx) => {
            const rankMedal = idx === 0 ? '🥇 01' : idx === 1 ? '🥈 02' : idx === 2 ? '🥉 03' : String(idx + 1).padStart(2, '0');
            const timeStr = row.completed_at ? new Date(row.completed_at).toLocaleTimeString() : 'In Progress';
            return `
              <tr class="${idx < 3 ? 'highlight-team' : ''}">
                <td class="lb-rank ${idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : ''}" style="font-weight:bold;">
                  ${rankMedal}
                </td>
                <td style="font-family:var(--disp); font-weight:700; font-size:15px; color:var(--text);">${escapeHtml(row.team_name)}</td>
                <td class="mono-text" style="font-size:12px; color:var(--muted);">${escapeHtml(row.college || 'Engineering')}</td>
                <td class="mono-text" style="color:var(--text);">${row.challenges_completed} / 5</td>
                <td style="font-family:var(--disp); font-size:18px; font-weight:800; color:var(--cyan);">${row.total_score} PTS</td>
                <td class="mono-text" style="font-size:11.5px; color:var(--muted);">${timeStr}</td>
                <td>
                  <span class="chip chip-${row.is_flagged ? 'red' : 'green'}" style="font-size:9.5px;">
                    ${row.is_flagged ? '⚠️ FLAGGED' : '✓ VERIFIED'}
                  </span>
                </td>
              </tr>
            `;
          }).join('')}
          ${rows.length === 0 ? `
            <tr><td colspan="7" style="text-align:center; color:var(--muted); padding:24px;">No team scores recorded yet.</td></tr>
          ` : ''}
        </tbody>
      </table>
    </div>
  `;
}

function showSafetyConfirmModal(title, message, confirmBtnText, onConfirm) {
  const modalWrap = document.getElementById('customModalContainer') || document.body;
  const modalDiv = document.createElement('div');
  modalDiv.className = 'neura-modal-overlay';
  modalDiv.style.display = 'flex';
  modalDiv.innerHTML = `
    <div class="neura-modal glass bracket-frame" style="max-width:460px; width:90%; padding:28px;">
      <span class="bl"></span><span class="br"></span>
      <div class="chip chip-amber" style="margin-bottom:12px;">AUTHORITATIVE ACTION REQUIRED</div>
      <h3 class="heading-md" style="margin-bottom:8px;">${escapeHtml(title)}</h3>
      <p class="sub-text" style="font-size:12.5px; line-height:1.5; margin-bottom:20px;">
        ${escapeHtml(message)}
      </p>
      <div style="display:flex; justify-content:flex-end; gap:12px;">
        <button class="btn btn-sm" id="btnCancelSafetyModal" style="padding:6px 14px;">CANCEL</button>
        <button class="btn btn-primary btn-sm" id="btnConfirmSafetyModal" style="padding:6px 16px;">${escapeHtml(confirmBtnText)}</button>
      </div>
    </div>
  `;

  modalWrap.appendChild(modalDiv);

  modalDiv.querySelector('#btnCancelSafetyModal')?.addEventListener('click', () => {
    modalDiv.remove();
  });
  modalDiv.querySelector('#btnConfirmSafetyModal')?.addEventListener('click', () => {
    modalDiv.remove();
    onConfirm();
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
