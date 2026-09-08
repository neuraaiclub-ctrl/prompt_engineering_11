/* ==========================================================================
   NEURA PROMPT FIXING ARENA WORKSPACE
   5 Sequential Prompt-Fixing Challenges, Anti-Cheat Proctoring,
   Live Hourglass Synchronization & Educational Performance Report
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';

let arenaPollInterval = null;
let currentChallengeData = null;
let securityViolationCount = 0;
let isAntiCheatInitialized = false;

export function renderArenaWorkspace() {
  const container = document.getElementById('page-arena-workspace');
  if (!container) return;

  // Initialize view and begin reactive polling
  initWorkspace(container);
}

async function initWorkspace(container) {
  // Mobile / Small Screen Check
  if (window.innerWidth < 800) {
    renderDesktopRequired(container);
    return;
  }

  // Check auth
  if (!store.isAuthenticated()) {
    renderUnauthenticated(container);
    return;
  }

  // Setup client anti-cheat proctoring listeners (once per session)
  if (!isAntiCheatInitialized) {
    setupAntiCheatListeners();
    isAntiCheatInitialized = true;
  }

  // Start polling
  await refreshArenaView(container);
  
  if (arenaPollInterval) clearInterval(arenaPollInterval);
  arenaPollInterval = setInterval(() => {
    // Only poll if workspace is active
    if (container.classList.contains('active')) {
      refreshArenaView(container, true);
    }
  }, 2500);
}

function renderDesktopRequired(container) {
  container.innerHTML = `
    <div style="max-width:560px; margin:80px auto; padding:36px; text-align:center;" class="glass bracket-frame">
      <span class="bl"></span><span class="br"></span>
      <div style="font-size:42px; margin-bottom:16px;">💻</div>
      <div class="chip chip-amber" style="margin-bottom:12px;">DESKTOP ENVIRONMENT REQUIRED</div>
      <h2 class="heading-md" style="margin-bottom:12px;">FULL-WIDTH SCREEN REQUIRED</h2>
      <p class="sub-text" style="font-size:13px; line-height:1.6; margin-bottom:24px;">
        The NEURA Prompt Fixing Arena requires a desktop or laptop environment with a minimum screen resolution of 1024x768 to support side-by-side prompt debugging, formatting validation, and security telemetry.
      </p>
      <button class="btn btn-primary" onclick="window.location.reload()">RECHECK DISPLAY RESOLUTION</button>
    </div>
  `;
}

function renderUnauthenticated(container) {
  container.innerHTML = `
    <div style="max-width:540px; margin:80px auto; padding:36px; text-align:center;" class="glass bracket-frame">
      <span class="bl"></span><span class="br"></span>
      <div class="chip chip-cyan" style="margin-bottom:12px;">AUTHENTICATION REQUIRED</div>
      <h2 class="heading-md" style="margin-bottom:12px;">ARENA ACCESS RESTRICTED</h2>
      <p class="sub-text" style="font-size:13px; line-height:1.6; margin-bottom:24px;">
        Please sign in with your team credentials or enter your team invite code to access your unique 5-challenge prompt fixing sequence.
      </p>
      <button class="btn btn-primary" id="btnGoToLogin">SIGN IN TO PARTICIPATE &rarr;</button>
    </div>
  `;
  document.getElementById('btnGoToLogin')?.addEventListener('click', () => {
    Router.navigate('team-lobby');
  });
}

async function refreshArenaView(container, isBackgroundPoll = false) {
  try {
    const statusData = await store.getArenaStatus();
    const status = statusData.status || 'waiting';

    // If eliminated by administration
    if (status === 'eliminated') {
      renderEliminatedScreen(container, statusData);
      return;
    }

    // If results are released, display official score dashboard / report
    if (statusData.is_results_released || status === 'results_available') {
      await renderResultsReport(container);
      return;
    }

    // If status is waiting
    if (status === 'waiting') {
      renderWaitingLobby(container, statusData);
      return;
    }

    // If status is live or completed
    const challengeRes = await store.getMyArenaChallenge();
    if (!challengeRes.success) {
      if (challengeRes.status === 'eliminated' || (challengeRes.error && challengeRes.error.toLowerCase().includes('eliminated'))) {
        renderEliminatedScreen(container, challengeRes);
        return;
      }
      if (!isBackgroundPoll) {
        container.innerHTML = `
          <div style="max-width:500px; margin:80px auto; padding:32px; text-align:center;" class="glass bracket-frame">
            <span class="bl"></span><span class="br"></span>
            <div class="chip chip-red" style="margin-bottom:12px;">COMMUNICATION ERROR</div>
            <p class="sub-text">${escapeHtml(challengeRes.error || 'Failed to retrieve challenge')}</p>
            <button class="btn btn-primary" style="margin-top:16px;" onclick="window.location.reload()">RETRY</button>
          </div>
        `;
      }
      return;
    }

    if (challengeRes.status === 'eliminated') {
      renderEliminatedScreen(container, challengeRes);
      return;
    }

    // Check if team has completed all challenges
    if (challengeRes.is_arena_completed || status === 'completed') {
      renderCompletedScreen(container, challengeRes);
      return;
    }

    // If challenge index changed or not background poll, render challenge view
    if (!isBackgroundPoll || !currentChallengeData || currentChallengeData.challenge_index !== challengeRes.challenge_index) {
      currentChallengeData = challengeRes;
      renderActiveChallenge(container, challengeRes);
    }
  } catch (err) {
    console.error('Error refreshing arena view:', err);
  }
}

/* ==========================================================================
   STATE 0: ELIMINATED SCREEN (AUTHORITATIVE COMPETITION DISQUALIFICATION)
   ========================================================================== */
function renderEliminatedScreen(container, data) {
  const reason = data.elimination_reason || data.reason || data.error || 'Team has been disqualified by Competition Administration for rule or integrity violation.';
  container.innerHTML = `
    <div style="max-width:680px; margin:60px auto; padding:40px; text-align:center;" class="glass bracket-frame">
      <span class="bl" style="border-color:var(--red);"></span><span class="br" style="border-color:var(--red);"></span>
      <div style="font-size:54px; margin-bottom:14px;">🛑</div>
      <div class="chip chip-red" style="margin-bottom:14px; font-weight:800; letter-spacing:1.5px;">COMPETITION STATUS // ELIMINATED</div>
      <h1 class="heading-lg" style="color:var(--red); margin-bottom:12px;">TEAM DISQUALIFIED FROM ARENA</h1>
      <p class="sub-text" style="font-size:13.5px; line-height:1.6; max-width:540px; margin:0 auto 20px auto;">
        Your team has been officially eliminated from live competition by the judging and administration panel. Challenge submission privileges have been permanently frozen.
      </p>

      <div class="glass-card" style="padding:16px 20px; max-width:500px; margin:0 auto 24px auto; border-left:4px solid var(--red); text-align:left;">
        <div class="eyebrow" style="color:var(--red); margin-bottom:6px;">OFFICIAL AUDIT NOTICE</div>
        <div style="font-size:13px; color:var(--text); font-family:var(--mono); line-height:1.5;">
          ${escapeHtml(reason)}
        </div>
      </div>

      <div style="display:flex; justify-content:center; gap:16px;">
        <button class="btn btn-sm btn-red" id="btnEliminatedLogout" style="padding:10px 24px; font-size:12px; font-weight:700;">
          ⎋ LOGOUT SESSION
        </button>
      </div>
    </div>
  `;

  document.getElementById('btnEliminatedLogout')?.addEventListener('click', () => {
    Router.confirmLogout();
  });
}

/* ==========================================================================
   STATE 1: WAITING SCREEN (ANIMATED HOURGLASS + SYNC POLLING)
   ========================================================================== */
function renderWaitingLobby(container, statusData) {
  // Avoid re-rendering DOM every 2.5s if already on waiting screen
  if (document.getElementById('arenaHourglassWrap')) return;

  const user = store.data.currentUser || {};
  container.innerHTML = `
    <div style="max-width:800px; margin:40px auto; padding:40px;" class="glass bracket-frame">
      <span class="bl"></span><span class="br"></span>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <div class="chip chip-cyan">ARENA LOBBY // STAND BY</div>
        <button class="btn btn-sm btn-red" id="btnWaitingLogout" style="padding:6px 14px; font-size:11px; font-weight:700; cursor:pointer;">
          ⎋ LOGOUT
        </button>
      </div>

      <div style="text-align:center; margin-bottom:32px;">
        <h1 class="heading-lg" style="margin-bottom:8px;">SYNCHRONIZED ARENA START</h1>
        <p class="sub-text" style="font-size:13px; max-width:620px; margin:0 auto;">
          Team <strong>${escapeHtml(user.name || 'Participant')}</strong> is registered. When the Hackathon Director starts the arena, all participants will simultaneously unlock their unique 5-challenge prompt sequence.
        </p>
      </div>

      <!-- Animated SVG Hourglass with flowing sand particles -->
      <div id="arenaHourglassWrap" class="arena-hourglass-wrap" style="text-align:center; margin:32px 0;">
        <div class="arena-hourglass">
          <svg width="84" height="110" viewBox="0 0 100 130" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Glass Frame Contour -->
            <path d="M 20 15 L 80 15 L 80 30 C 80 50, 58 60, 52 65 C 58 70, 80 80, 80 100 L 80 115 L 20 115 L 20 100 C 20 80, 42 70, 48 65 C 42 60, 20 50, 20 30 Z" 
                  stroke="rgba(0, 243, 255, 0.7)" stroke-width="3" fill="rgba(6, 11, 24, 0.7)"/>
            <!-- Top Sand Reservoir -->
            <path d="M 28 32 C 35 32, 65 32, 72 32 C 72 45, 56 56, 50 64 C 44 56, 28 45, 28 32 Z" 
                  fill="url(#sandGrad)" class="sand-top"/>
            <!-- Flowing Sand Stream -->
            <line x1="50" y1="65" x2="50" y2="105" stroke="#00f3ff" stroke-width="2.5" stroke-dasharray="3 3" class="sand-stream"/>
            <!-- Bottom Sand Pile -->
            <path d="M 30 112 C 40 102, 60 102, 70 112 Z" fill="url(#sandGrad)" class="sand-bottom"/>
            <defs>
              <linearGradient id="sandGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#00f3ff" stop-opacity="0.9"/>
                <stop offset="100%" stop-color="#9d4edd" stop-opacity="0.7"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="mono-text" style="color:var(--cyan); font-size:12px; margin-top:12px; letter-spacing:1px; animation:pulse-glow 2s infinite;">
          [ WAITING FOR OFFICIAL START COMMAND // POLLING EVERY 2.5s ]
        </div>
      </div>

      <!-- Competition Rules & Rubric Briefing Matrix -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:32px;">
        <div class="glass-card" style="padding:18px;">
          <div class="eyebrow" style="margin-bottom:8px; color:var(--cyan);">ARENA FORMAT</div>
          <ul style="padding-left:18px; font-size:12.5px; color:var(--text); line-height:1.7; margin:0;">
            <li><strong>5 Challenges:</strong> Strictly unique, non-overlapping set of 5 questions per team.</li>
            <li><strong>Sequential Flow:</strong> Challenges must be solved and locked sequentially (1 through 5).</li>
            <li><strong>Permanent Submissions:</strong> Single immutable submission per challenge with server timestamp.</li>
          </ul>
        </div>
        <div class="glass-card" style="padding:18px;">
          <div class="eyebrow" style="margin-bottom:8px; color:var(--violet);">500-MARK EVALUATION RUBRIC</div>
          <ul style="padding-left:18px; font-size:12.5px; color:var(--text); line-height:1.7; margin:0;">
            <li><strong>Max 100 / question</strong> across 5 criteria (0 / 10 / 20 each):</li>
            <li>1. Clarity & Objective Formulation</li>
            <li>2. Specificity & Detail Enforcement</li>
            <li>3. Operational Context & Framing</li>
            <li>4. Output Structuring & Formatting</li>
            <li>5. Constraints & Edge Guardrails</li>
            <li><strong style="color:var(--cyan);">Total: /500 &bull; Average Score: Total / 5</strong></li>
          </ul>
        </div>
      </div>

      <!-- Proctoring & Integrity Notice -->
      <div class="glass-card" style="margin-top:20px; padding:14px 18px; display:flex; align-items:center; gap:14px; border-left:3px solid var(--amber);">
        <div style="font-size:22px;">🛡️</div>
        <div style="font-size:12px; line-height:1.5; color:var(--muted);">
          <strong style="color:var(--amber);">Active Anti-Cheat Telemetry:</strong> Fullscreen enforcement, tab switches, copy/paste, and blur events are continuously audited on the server. Please maintain fullscreen focus during live competition.
        </div>
      </div>
    </div>
  `;

  document.getElementById('btnWaitingLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out will exit the arena waiting lobby.');
  });
}

/* ==========================================================================
   STATE 2: LIVE CHALLENGE SCREEN (SEQUENTIAL 1-5, TEXTAREA, CHAR COUNTER)
   ========================================================================== */
function renderActiveChallenge(container, challengeRes) {
  const challenge = challengeRes.challenge;
  const currIndex = challengeRes.challenge_index;
  const user = store.data.currentUser || {};
  const teamId = user.teamId || user.id || 'team';
  const draftKey = `ARENA_DRAFT_${teamId}_${currIndex}`;
  const savedDraft = localStorage.getItem(draftKey) || '';

  container.innerHTML = `
    <!-- On-screen Security Warning Banner (Hidden by default, unhides on violation) -->
    <div id="arenaSecurityBanner" class="security-banner" style="display:${securityViolationCount > 0 ? 'flex' : 'none'};">
      <span>⚠️ <strong>PROCTORING WARNING:</strong> Window / tab switch detected. This event has been logged to your immutable audit log. (${securityViolationCount} violation${securityViolationCount > 1 ? 's' : ''} recorded).</span>
      <button class="btn btn-sm" onclick="document.getElementById('arenaSecurityBanner').style.display='none'" style="padding:2px 8px; font-size:10px;">DISMISS</button>
    </div>

    <!-- Arena Header & 5-Step Progress Indicators -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; flex-wrap:wrap; gap:16px;">
      <div>
        <div class="eyebrow">PROMPT FIXING ARENA // ROUND 1</div>
        <h1 class="heading-lg" style="margin-top:4px;">CHALLENGE ${currIndex} OF 5</h1>
      </div>

      <!-- 5 Sequential Progress Step Dots, Fullscreen & Logout Action -->
      <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
        <div style="display:flex; align-items:center; gap:12px;">
          <span class="mono-text" style="font-size:11.5px; color:var(--muted); margin-right:4px;">SEQUENCE PROGRESS:</span>
          <div class="step-progress-wrap" style="display:flex; gap:8px;">
            ${[1, 2, 3, 4, 5].map(step => {
              const isPassed = step < currIndex;
              const isCurrent = step === currIndex;
              return `
                <div class="step-dot ${isPassed ? 'completed' : isCurrent ? 'active' : 'locked'}" title="Challenge ${step}">
                  ${isPassed ? '✓' : step}
                </div>
              `;
            }).join('')}
          </div>
        </div>
        <button class="btn btn-sm btn-primary" id="btnToggleFullscreen" style="padding:6px 12px; font-size:11px; font-weight:700;">
          ⛶ FULLSCREEN
        </button>
        <button class="btn btn-sm btn-red" id="btnChallengeLogout" style="padding:6px 14px; font-size:11px; font-weight:700; cursor:pointer;">
          ⎋ LOGOUT
        </button>
      </div>
    </div>

    <!-- Main Workspace Split Grid: Flawed Prompt Briefing (Left) & Refactored Solution Editor (Right) -->
    <div style="display:grid; grid-template-columns:1fr 1.15fr; gap:24px;">
      
      <!-- LEFT PANEL: FLAWED PROMPT & DIAGNOSIS BRIEFING -->
      <div class="glass bracket-frame" style="padding:24px;">
        <span class="bl"></span><span class="br"></span>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div class="chip chip-red">❌ FLAWED PROMPT</div>
          <span class="chip chip-${challenge.difficulty === 'hard' ? 'violet' : 'cyan'}">${challenge.difficulty.toUpperCase()}</span>
        </div>

        <h2 class="heading-md" style="margin-bottom:8px; font-size:17px;">${escapeHtml(challenge.title)}</h2>
        <div class="mono-text" style="color:var(--cyan); font-size:11.5px; margin-bottom:16px;">
          CATEGORY // ${escapeHtml(challenge.category).toUpperCase()}
        </div>

        <!-- Production Scenario / Context -->
        <div style="margin-bottom:20px;">
          <div class="eyebrow" style="margin-bottom:6px; color:var(--amber);">SCENARIO & OBJECTIVE</div>
          <p style="font-size:13px; color:var(--text); line-height:1.6; margin:0;">
            ${escapeHtml(challenge.scenario)}
          </p>
        </div>

        <!-- Flawed Prompt Readout Box (Protected against copy-paste) -->
        <div style="margin-bottom:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div class="eyebrow">ORIGINAL UNOPTIMIZED INPUT</div>
            <span class="mono-text" style="font-size:10px; color:var(--muted);">PROTECTED INPUT</span>
          </div>
          <div id="flawedPromptBox" class="evidence-block" style="border-color:rgba(255, 0, 85, 0.4); background:rgba(255, 0, 85, 0.04); font-size:13px; line-height:1.6; user-select:none;">
            ${escapeHtml(challenge.flawed_prompt)}
          </div>
        </div>

        <!-- Known Failure Symptoms -->
        <div class="glass-card" style="padding:14px; border-left:3px solid var(--red);">
          <div class="eyebrow" style="color:var(--red); margin-bottom:6px;">KNOWN FAILURE BEHAVIORS</div>
          <ul style="padding-left:16px; margin:0; font-size:12px; color:var(--muted); line-height:1.6;">
            <li>Produces hallucinated, vague, or non-deterministic outputs.</li>
            <li>Fails to adhere to downstream system format constraints.</li>
            <li>Requires architectural prompt restructuring (role, objective, rules, format).</li>
          </ul>
        </div>
      </div>

      <!-- RIGHT PANEL: PARTICIPANT REFACTORING SOLUTION EDITOR -->
      <div class="glass bracket-frame" style="padding:24px; display:flex; flex-direction:column;">
        <span class="bl"></span><span class="br"></span>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <div class="chip chip-green">✨ REFACTORED SOLUTION</div>
          <span class="mono-text" id="charCounter" style="font-size:11.5px; color:var(--muted);">0 / 1500 chars</span>
        </div>

        <!-- Solution Editor Textarea -->
        <div class="field" style="margin-bottom:16px; flex:1; display:flex; flex-direction:column;">
          <label style="display:flex; justify-content:space-between;">
            <span>Your Optimized Prompt Formulation</span>
            <span class="mono-text" style="font-size:10.5px; color:var(--cyan); font-weight:normal;" id="autoSaveIndicator">✓ Draft preserved locally</span>
          </label>
          <textarea id="refactoredPromptInput" 
                    rows="10" 
                    maxlength="1500"
                    placeholder="Provide a clear, well-framed, constraint-driven prompt specifying:&#10;1. Persona / Role&#10;2. Specific Task & Background Context&#10;3. Strict Output Schema / Structure Constraints&#10;4. Edge-Case Guardrails"
                    style="font-family:var(--mono); font-size:13px; line-height:1.5; resize:vertical; flex:1;">${escapeHtml(savedDraft)}</textarea>
        </div>

        <!-- Optional Iteration / Diagnosis Notes -->
        <div class="field" style="margin-bottom:20px;">
          <label>Diagnosis & Refactoring Rationale <span style="color:var(--muted); font-weight:normal;">(Optional - provides context to evaluating judges)</span></label>
          <input type="text" id="diagnosisNotesInput" placeholder="e.g. Added strict JSON schema, delimited context, and explicitly forbade conversational pleasantries." maxlength="255">
        </div>

        <!-- Action Footer -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto; padding-top:16px; border-top:1px solid var(--line);">
          <div class="mono-text" style="font-size:11px; color:var(--amber);">
            ⚠️ Submissions are immutable once confirmed.
          </div>
          <button class="btn btn-primary" id="btnSubmitChallenge" style="padding:10px 22px;">
            ${currIndex === 5 ? 'LOCK FINAL CHALLENGE & COMPLETE &rarr;' : `SUBMIT & PROCEED TO CHALLENGE ${currIndex + 1} &rarr;`}
          </button>
        </div>

      </div>

    </div>
  `;

  // Attach Solution Editor Interactions
  const textarea = document.getElementById('refactoredPromptInput');
  const counter = document.getElementById('charCounter');
  const autoSave = document.getElementById('autoSaveIndicator');
  const submitBtn = document.getElementById('btnSubmitChallenge');

  const updateCount = () => {
    const len = textarea.value.length;
    if (counter) counter.textContent = `${len} / 1500 chars`;
    if (len >= 1450) {
      counter.style.color = 'var(--red)';
    } else {
      counter.style.color = 'var(--muted)';
    }
  };
  updateCount();

  // Auto-save draft on keystroke
  textarea?.addEventListener('input', () => {
    updateCount();
    localStorage.setItem(draftKey, textarea.value);
    if (autoSave) {
      autoSave.textContent = 'Saving draft...';
      autoSave.style.color = 'var(--amber)';
      setTimeout(() => {
        autoSave.textContent = '✓ Draft saved';
        autoSave.style.color = 'var(--green)';
      }, 400);
    }
  });

    // Fullscreen toggle action
  document.getElementById('btnToggleFullscreen')?.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch((err) => {
        console.warn('Fullscreen request denied:', err);
      });
    } else {
      document.exitFullscreen().catch((err) => console.warn(err));
    }
  });

  // Anti-cheat paste audit on refactored input
  textarea?.addEventListener('paste', (e) => {
    const pasteLength = (e.clipboardData || window.clipboardData)?.getData('text')?.length || 0;
    store.logSecurityEvent('PASTE_EVENT', {
      challenge_index: currIndex,
      char_count: pasteLength
    });
  });

  // Anti-cheat restriction on prompt box
  const promptBox = document.getElementById('flawedPromptBox');
  if (promptBox) {
    promptBox.addEventListener('copy', (e) => {
      e.preventDefault();
      Router.showToast('Direct copying of challenge prompts is restricted.', 'amber');
      store.logSecurityEvent('COPY_ATTEMPT', { challenge_index: currIndex });
    });
    promptBox.addEventListener('contextmenu', (e) => {
      e.preventDefault();
    });
  }

  // Submit Handler with Confirmation Modal
  submitBtn?.addEventListener('click', () => {
    const fixedPrompt = textarea.value.trim();
    if (!fixedPrompt) {
      Router.showToast('Please enter your refactored prompt before submitting.', 'red');
      textarea.focus();
      return;
    }
    if (fixedPrompt.length < 15) {
      Router.showToast('Prompt is too brief. Provide comprehensive instructions and constraints.', 'amber');
      return;
    }

    showSubmissionConfirmationModal(currIndex, async () => {
      submitBtn.disabled = true;
      submitBtn.textContent = 'TRANSMITTING & LOCKING...';

      const payload = {
        challenge_index: currIndex,
        prompt_bank_id: challenge.id,
        fixed_prompt: fixedPrompt,
        diagnosis_notes: document.getElementById('diagnosisNotesInput')?.value.trim() || null
      };

      const res = await store.submitArenaChallenge(payload);

      if (res.success) {
        // Clear draft
        localStorage.removeItem(draftKey);
        Router.showToast(`Challenge ${currIndex} locked successfully!`, 'green');

        if (res.is_arena_completed) {
          Router.showToast('All 5 challenges completed! Awaiting judge evaluation.', 'cyan');
        }

        // Re-render
        await refreshArenaView(container);
      } else {
        submitBtn.disabled = false;
        submitBtn.textContent = currIndex === 5 ? 'LOCK FINAL CHALLENGE & COMPLETE →' : `SUBMIT & PROCEED TO CHALLENGE ${currIndex + 1} →`;
        Router.showToast(res.error || 'Submission failed. Please try again.', 'red');
      }
    });
  });

  document.getElementById('btnChallengeLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out will safely preserve your current draft locally. You can resume anytime by signing back in.');
  });
}

function showSubmissionConfirmationModal(challengeIndex, onConfirm) {
  const modalWrap = document.getElementById('customModalContainer') || document.body;
  const modalDiv = document.createElement('div');
  modalDiv.className = 'neura-modal-overlay';
  modalDiv.style.display = 'flex';
  modalDiv.innerHTML = `
    <div class="neura-modal glass bracket-frame" style="max-width:440px; width:90%; padding:28px;">
      <span class="bl"></span><span class="br"></span>
      <div class="chip chip-amber" style="margin-bottom:12px;">CONFIRM CHALLENGE SUBMISSION</div>
      <h3 class="heading-md" style="margin-bottom:8px;">LOCK CHALLENGE ${challengeIndex} OF 5?</h3>
      <p class="sub-text" style="font-size:12.5px; line-height:1.5; margin-bottom:20px;">
        Once confirmed, your solution for Challenge ${challengeIndex} will be <strong>permanently locked on the server</strong> and cannot be revised. Your submission timestamp will be recorded for official tie-breaking.
      </p>
      <div style="display:flex; justify-content:flex-end; gap:12px;">
        <button class="btn btn-sm" id="btnCancelModalSubmit" style="padding:6px 14px;">CANCEL</button>
        <button class="btn btn-primary btn-sm" id="btnConfirmModalSubmit" style="padding:6px 16px;">YES, LOCK & SUBMIT &rarr;</button>
      </div>
    </div>
  `;

  modalWrap.appendChild(modalDiv);

  modalDiv.querySelector('#btnCancelModalSubmit')?.addEventListener('click', () => {
    modalDiv.remove();
  });
  modalDiv.querySelector('#btnConfirmModalSubmit')?.addEventListener('click', () => {
    modalDiv.remove();
    onConfirm();
  });
}

/* ==========================================================================
   STATE 3: COMPLETED SCREEN (WAITING FOR JUDGE EVALUATION & RESULTS)
   ========================================================================== */
function renderCompletedScreen(container, challengeRes) {
  const user = store.data.currentUser || {};
  const completedAt = challengeRes.completed_at ? new Date(challengeRes.completed_at).toLocaleTimeString() : 'Recorded';

  container.innerHTML = `
    <div style="max-width:760px; margin:40px auto; padding:40px;" class="glass bracket-frame">
      <span class="bl"></span><span class="br"></span>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <div class="chip chip-green">ARENA ROUND COMPLETED</div>
        <button class="btn btn-sm btn-red" id="btnCompletedLogout" style="padding:6px 14px; font-size:11px; font-weight:700; cursor:pointer;">
          ⎋ LOGOUT
        </button>
      </div>

      <div style="text-align:center; margin-bottom:28px;">
        <div style="font-size:48px; margin-bottom:12px;">🏆</div>
        <h1 class="heading-lg" style="margin-bottom:8px;">ALL 5 CHALLENGES SUBMITTED</h1>
        <p class="sub-text" style="font-size:13px; max-width:580px; margin:0 auto;">
          Congratulations, <strong>${escapeHtml(user.name || 'Team')}</strong>! Your 5 prompt-fixing solutions have been securely stored and locked on the competition server.
        </p>
      </div>

      <!-- Submission Confirmation Card -->
      <div class="glass-card" style="padding:22px; margin-bottom:28px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; text-align:center;">
        <div>
          <div class="eyebrow" style="margin-bottom:4px;">CHALLENGES SOLVED</div>
          <div class="heading-md" style="color:var(--cyan);">5 / 5</div>
        </div>
        <div>
          <div class="eyebrow" style="margin-bottom:4px;">COMPLETION TIMESTAMP</div>
          <div class="heading-md" style="color:var(--green); font-size:16px;">${escapeHtml(completedAt)}</div>
        </div>
        <div>
          <div class="eyebrow" style="margin-bottom:4px;">EVALUATION STATUS</div>
          <div class="heading-md" style="color:var(--violet); font-size:14px;">IN EVALUATION</div>
        </div>
      </div>

      <!-- Live Waiting Callout -->
      <div style="text-align:center; padding:20px; background:rgba(0, 243, 255, 0.04); border:1px dashed var(--cyan-dim); border-radius:4px; margin-bottom:28px;">
        <div class="mono-text" style="font-size:12.5px; color:var(--cyan); animation:pulse-glow 2s infinite;">
          ⏳ JUDGES ARE SCORING SOLUTIONS USING THE 5-CRITERIA RUBRIC...
        </div>
        <p class="sub-text" style="font-size:12px; margin-top:8px; margin-bottom:0;">
          Your detailed educational performance report and official leaderboard rankings will automatically appear here once released by the judging panel.
        </p>
      </div>

      <div style="text-align:center;">
        <button class="btn btn-primary" onclick="window.location.reload()">REFRESH STATUS ⟳</button>
      </div>
    </div>
  `;

  document.getElementById('btnCompletedLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out will close your session. Your 5 submitted solutions remain securely locked for evaluation.');
  });
}

/* ==========================================================================
   STATE 4: DETAILED EDUCATIONAL PERFORMANCE REPORT & SCORE DASHBOARD
   ========================================================================== */
async function renderResultsReport(container) {
  // First try the official 5-characteristic score dashboard endpoint
  const resultsRes = await store.getMyArenaResults();

  if (resultsRes.success && resultsRes.challenges && resultsRes.challenges.length > 0) {
    const data = resultsRes;
    const rankDisplay = data.rank ? `#${data.rank}` : 'TBD';
    const podiumBadge = data.rank === 1 ? '<span class="chip chip-green" style="font-weight:700;">🥇 WINNER (1ST PLACE)</span>'
                      : data.rank === 2 ? '<span class="chip chip-cyan" style="font-weight:700;">🥈 RUNNER UP (2ND PLACE)</span>'
                      : data.rank === 3 ? '<span class="chip chip-violet" style="font-weight:700;">🥉 2ND RUNNER UP (3RD PLACE)</span>'
                      : '';
    const completionTimeStr = data.completion_time ? new Date(data.completion_time).toLocaleTimeString() : 'Recorded';

    // Calculate characteristic averages across evaluated challenges
    const chs = data.challenges;
    const avgClarity = (chs.reduce((acc, c) => acc + (c.characteristics?.clarity || 0), 0) / chs.length).toFixed(1);
    const avgSpec = (chs.reduce((acc, c) => acc + (c.characteristics?.specificity || 0), 0) / chs.length).toFixed(1);
    const avgContext = (chs.reduce((acc, c) => acc + (c.characteristics?.context || 0), 0) / chs.length).toFixed(1);
    const avgFormat = (chs.reduce((acc, c) => acc + (c.characteristics?.output_format || 0), 0) / chs.length).toFixed(1);
    const avgConstraints = (chs.reduce((acc, c) => acc + (c.characteristics?.constraints || 0), 0) / chs.length).toFixed(1);

    container.innerHTML = `
      <div style="max-width:960px; margin:20px auto; padding:32px;" class="glass bracket-frame">
        <span class="bl"></span><span class="br"></span>

        <!-- Report Header -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:28px; flex-wrap:wrap; gap:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
              <span class="chip chip-green">OFFICIAL PERFORMANCE REPORT</span>
              ${podiumBadge}
            </div>
            <h1 class="heading-lg" style="margin-bottom:4px;">ARENA SCORE DASHBOARD</h1>
            <div class="mono-text" style="font-size:12px; color:var(--muted);">
              TEAM // ${escapeHtml(data.team_name)} &bull; ${escapeHtml(data.college)} &bull; 5 QUESTIONS EVALUATED
            </div>
          </div>

          <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
            <!-- Overall Score Cards -->
            <div class="glass-card" style="padding:14px 20px; text-align:center; border-color:var(--cyan);">
              <div class="eyebrow" style="margin-bottom:2px;">TOTAL SCORE</div>
              <div class="heading-lg" style="color:var(--cyan); font-size:32px; line-height:1;">
                ${data.total_score} <span style="font-size:16px; color:var(--muted);">/ 500</span>
              </div>
              <div class="mono-text" style="font-size:11px; color:var(--green); margin-top:4px;">
                AVG: ${data.average_score} / 100
              </div>
            </div>

            <div class="glass-card" style="padding:14px 20px; text-align:center; border-color:var(--violet);">
              <div class="eyebrow" style="margin-bottom:2px;">OFFICIAL RANK</div>
              <div class="heading-lg" style="color:var(--violet); font-size:32px; line-height:1;">
                ${rankDisplay}
              </div>
              <div class="mono-text" style="font-size:10.5px; color:var(--muted); margin-top:4px;">
                TIME: ${escapeHtml(completionTimeStr)}
              </div>
            </div>

            <button class="btn btn-sm btn-red" id="btnReportLogout" style="padding:8px 16px; font-size:11px; font-weight:700; cursor:pointer;">
              ⎋ LOGOUT
            </button>
          </div>
        </div>

        <!-- 5-Characteristic Mastery Progress Bars (Max 20 per characteristic) -->
        <div class="glass-card" style="padding:24px; margin-bottom:28px;">
          <div class="eyebrow" style="margin-bottom:16px; color:var(--cyan);">5-CHARACTERISTIC MASTERY BREAKDOWN (AVERAGE SCORE / 20)</div>
          
          <div style="display:flex; flex-direction:column; gap:14px;">
            ${renderCriterionBar('1. Clarity & Objective Formulation', avgClarity, 20, 'var(--cyan)')}
            ${renderCriterionBar('2. Specificity & Detail Enforcement', avgSpec, 20, 'var(--green)')}
            ${renderCriterionBar('3. Operational Context & Framing', avgContext, 20, 'var(--violet)')}
            ${renderCriterionBar('4. Output Structuring & Formatting', avgFormat, 20, 'var(--amber)')}
            ${renderCriterionBar('5. Constraints & Edge Guardrails', avgConstraints, 20, 'var(--blue)')}
          </div>
        </div>

        <!-- Per-Challenge Evaluation Breakdown Cards -->
        <div class="eyebrow" style="margin-bottom:16px;">QUESTION-BY-QUESTION EVALUATION BREAKDOWN</div>
        <div style="display:flex; flex-direction:column; gap:18px;">
          ${data.challenges.map((ch) => {
            const timeFormatted = ch.server_timestamp ? new Date(ch.server_timestamp).toLocaleTimeString() : 'Recorded';
            return `
              <div class="glass bracket-frame" style="padding:22px;">
                <span class="bl"></span><span class="br"></span>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
                  <div>
                    <span class="chip chip-cyan" style="margin-right:8px;">QUESTION ${ch.challenge_index}</span>
                    <span class="mono-text" style="color:var(--muted); font-size:11.5px; margin-right:8px;">[${escapeHtml(ch.code)}]</span>
                    <strong style="font-size:15px;">${escapeHtml(ch.title)}</strong>
                  </div>
                  <div style="display:flex; align-items:center; gap:12px;">
                    <span class="chip chip-violet">${escapeHtml(ch.category || 'General').toUpperCase()}</span>
                    <div class="heading-md" style="color:var(--cyan); font-size:20px;">
                      ${ch.score} <span style="font-size:13px; color:var(--muted);">/ 100</span>
                    </div>
                  </div>
                </div>

                <!-- Submitted Solution -->
                <div style="margin-bottom:14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="eyebrow">YOUR SUBMITTED PROMPT FORMULATION</div>
                    <span class="mono-text" style="font-size:10px; color:var(--muted);">LOCKED AT ${escapeHtml(timeFormatted)}</span>
                  </div>
                  <div class="evidence-block" style="font-size:12.5px; max-height:110px; line-height:1.5; font-family:var(--mono);">${escapeHtml(ch.submitted_prompt)}</div>
                </div>

                <!-- 5 Characteristic Scores Breakdown -->
                <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:8px; margin-bottom:12px; text-align:center;">
                  <div class="glass-card" style="padding:8px 4px;">
                    <div style="font-size:9.5px; color:var(--muted);">CLARITY</div>
                    <div style="font-weight:bold; color:var(--cyan); font-size:13px;">${ch.characteristics?.clarity || 0} / 20</div>
                  </div>
                  <div class="glass-card" style="padding:8px 4px;">
                    <div style="font-size:9.5px; color:var(--muted);">SPECIFICITY</div>
                    <div style="font-weight:bold; color:var(--green); font-size:13px;">${ch.characteristics?.specificity || 0} / 20</div>
                  </div>
                  <div class="glass-card" style="padding:8px 4px;">
                    <div style="font-size:9.5px; color:var(--muted);">CONTEXT</div>
                    <div style="font-weight:bold; color:var(--violet); font-size:13px;">${ch.characteristics?.context || 0} / 20</div>
                  </div>
                  <div class="glass-card" style="padding:8px 4px;">
                    <div style="font-size:9.5px; color:var(--muted);">OUTPUT FORMAT</div>
                    <div style="font-weight:bold; color:var(--amber); font-size:13px;">${ch.characteristics?.output_format || 0} / 20</div>
                  </div>
                  <div class="glass-card" style="padding:8px 4px;">
                    <div style="font-size:9.5px; color:var(--muted);">CONSTRAINTS</div>
                    <div style="font-weight:bold; color:var(--blue); font-size:13px;">${ch.characteristics?.constraints || 0} / 20</div>
                  </div>
                </div>

                <!-- Constructive Judge Feedback -->
                ${ch.judge_feedback ? `
                  <div class="glass-card" style="padding:10px 14px; border-left:3px solid var(--violet);">
                    <div class="eyebrow" style="color:var(--violet); margin-bottom:4px;">OFFICIAL EVALUATION FEEDBACK</div>
                    <div style="font-size:12.5px; font-style:italic; color:var(--text);">"${escapeHtml(ch.judge_feedback)}"</div>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>

        <!-- Action: Navigate to Spectator Leaderboard -->
        <div style="margin-top:32px; text-align:center;">
          <button class="btn btn-violet" id="btnViewArenaLeaderboard" style="padding:10px 24px;">
            VIEW OFFICIAL ARENA LEADERBOARD &rarr;
          </button>
        </div>

      </div>
    `;

    document.getElementById('btnViewArenaLeaderboard')?.addEventListener('click', () => {
      Router.navigate('spectator-view');
    });

    document.getElementById('btnReportLogout')?.addEventListener('click', () => {
      Router.confirmLogout();
    });
    return;
  }

  // Fallback to getArenaReport() if my-results has no evaluated challenges yet
  const reportRes = await store.getArenaReport();
  if (!reportRes.success) {
    container.innerHTML = `
      <div style="max-width:540px; margin:80px auto; padding:36px; text-align:center;" class="glass bracket-frame">
        <span class="bl"></span><span class="br"></span>
        <div class="chip chip-violet" style="margin-bottom:12px;">RESULTS PENDING</div>
        <h2 class="heading-md" style="margin-bottom:12px;">EVALUATION IN PROGRESS</h2>
        <p class="sub-text" style="font-size:13px; line-height:1.6; margin-bottom:20px;">
          The judging panel is currently finalizing 5-characteristic scores. Please refresh shortly.
        </p>
        <button class="btn btn-primary" onclick="window.location.reload()">REFRESH STATUS ⟳</button>
      </div>
    `;
    return;
  }

  const report = reportRes.report;
  const rank = report.current_rank ? `#${report.current_rank}` : 'TBD';

  container.innerHTML = `
    <div style="max-width:960px; margin:20px auto; padding:32px;" class="glass bracket-frame">
      <span class="bl"></span><span class="br"></span>

      <!-- Report Header -->
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:28px; flex-wrap:wrap; gap:16px;">
        <div>
          <div class="chip chip-green" style="margin-bottom:8px;">OFFICIAL PERFORMANCE REPORT</div>
          <h1 class="heading-lg" style="margin-bottom:4px;">ARENA PERFORMANCE AUDIT</h1>
          <div class="mono-text" style="font-size:12px; color:var(--muted);">
            TEAM // ${escapeHtml(report.team_name)} &bull; ${report.challenges_completed}/5 CHALLENGES EVALUATED
          </div>
        </div>

        <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
          <div class="glass-card" style="padding:16px 24px; text-align:center; border-color:var(--cyan);">
            <div class="eyebrow" style="margin-bottom:4px;">TOTAL ARENA SCORE</div>
            <div class="heading-lg" style="color:var(--cyan); font-size:36px; line-height:1;">
              ${report.total_score} <span style="font-size:18px; color:var(--muted);">/ 50</span>
            </div>
            <div class="mono-text" style="font-size:11px; color:var(--green); margin-top:4px;">
              STANDINGS RANK: ${rank}
            </div>
          </div>
          <button class="btn btn-sm btn-red" id="btnReportLogout" style="padding:8px 16px; font-size:11px; font-weight:700; cursor:pointer;">
            ⎋ LOGOUT
          </button>
        </div>
      </div>

      <div style="margin-top:32px; text-align:center;">
        <button class="btn btn-violet" id="btnViewArenaLeaderboard" style="padding:10px 24px;">
          VIEW OFFICIAL ARENA LEADERBOARD &rarr;
        </button>
      </div>
    </div>
  `;

  document.getElementById('btnViewArenaLeaderboard')?.addEventListener('click', () => {
    Router.navigate('spectator-view');
  });

  document.getElementById('btnReportLogout')?.addEventListener('click', () => {
    Router.confirmLogout();
  });
}

function renderCriterionBar(label, current, max, color) {
  const pct = Math.min(Math.round((current / max) * 100), 100);
  return `
    <div>
      <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
        <span>${escapeHtml(label)}</span>
        <span class="mono-text" style="font-weight:bold;">${current} / ${max}</span>
      </div>
      <div style="height:8px; background:rgba(255,255,255,0.06); border-radius:4px; overflow:hidden;">
        <div style="width:${pct}%; height:100%; background:${color}; border-radius:4px; transition:width 0.6s ease;"></div>
      </div>
    </div>
  `;
}

/* ==========================================================================
   ANTI-CHEAT TELEMETRY & EVENT LISTENERS
   ========================================================================== */
function setupAntiCheatListeners() {
  // 1. Tab switch detection
  document.addEventListener('visibilitychange', () => {
    const isArenaActive = document.getElementById('page-arena-workspace')?.classList.contains('active');
    if (document.hidden && isArenaActive && currentChallengeData && !currentChallengeData.is_arena_completed) {
      securityViolationCount++;
      store.logSecurityEvent('TAB_SWITCH', {
        challenge_index: currentChallengeData.challenge_index,
        violation_count: securityViolationCount
      });
      triggerSecurityAlert('Tab switch detected. Maintain window focus during live evaluation.');
    }
  });

  // 2. Window blur detection (switching to other desktop apps)
  window.addEventListener('blur', () => {
    const isArenaActive = document.getElementById('page-arena-workspace')?.classList.contains('active');
    if (isArenaActive && currentChallengeData && !currentChallengeData.is_arena_completed) {
      securityViolationCount++;
      store.logSecurityEvent('WINDOW_BLUR', {
        challenge_index: currentChallengeData.challenge_index,
        violation_count: securityViolationCount
      });
      triggerSecurityAlert('Application blur detected. All focus transitions are proctored.');
    }
  });

  // 3. Fullscreen exit detection
  document.addEventListener('fullscreenchange', () => {
    const isArenaActive = document.getElementById('page-arena-workspace')?.classList.contains('active');
    if (!document.fullscreenElement && isArenaActive && currentChallengeData && !currentChallengeData.is_arena_completed) {
      securityViolationCount++;
      store.logSecurityEvent('FULLSCREEN_EXIT', {
        challenge_index: currentChallengeData.challenge_index,
        violation_count: securityViolationCount
      });
      triggerSecurityAlert('Fullscreen exited. Competition session should remain in fullscreen mode.');
    }
  });

  // 4. Prevent external context menu during active challenge
  document.addEventListener('contextmenu', (e) => {
    const isArenaActive = document.getElementById('page-arena-workspace')?.classList.contains('active');
    if (isArenaActive && currentChallengeData && !currentChallengeData.is_arena_completed) {
      // Allow default only if clicking on buttons or inputs
      if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
      }
    }
  });
}

function triggerSecurityAlert(message) {
  const banner = document.getElementById('arenaSecurityBanner');
  if (banner) {
    banner.style.display = 'flex';
    banner.innerHTML = `
      <span>⚠️ <strong>PROCTORING WARNING:</strong> ${escapeHtml(message)} (${securityViolationCount} violation${securityViolationCount > 1 ? 's' : ''} recorded).</span>
      <button class="btn btn-sm" onclick="document.getElementById('arenaSecurityBanner').style.display='none'" style="padding:2px 8px; font-size:10px;">DISMISS</button>
    `;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
