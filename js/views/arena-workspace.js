/* ==========================================================================
   NEURA PROMPT ARENA — the page players actually compete on

   States (each rendered once, then left alone so typing is never interrupted):
     signed out · desktop required · stand-by · live challenge · all locked ·
     released results · eliminated

   Live challenge is a "repair bench": the broken prompt on the left, the
   player's rewrite on the right, a coverage radar that fills as they write,
   a five-step progress rail on top, and a wormhole surge each time they lock.

   API contract, anti-cheat telemetry and draft autosave are unchanged from the
   previous version of this file.
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { setWormholeMood, warpWormhole } from '../components/wormhole.js';
import { mountRadar, CRITERIA } from '../components/radar.js';
import { analyzePrompt } from '../utils/prompt-coverage.js';

/* Switch the coverage radar and hints off by setting this to false. */
const ARENA_UI = { showCoverage: true, maxChars: 1500, minChars: 15 };

const CHECK = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 6.5l2.6 2.6L10 3.4"/></svg>';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pollId = null;
let clockId = null;
let endsAt = null;              // epoch ms when the round ends, if the server tells us
let renderedKey = null;         // which screen is currently on the page
let currentChallengeData = null;
let securityViolationCount = 0;
let antiCheatReady = false;

const escapeHtml = (s) =>
  s == null ? '' : String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ==========================================================================
   ENTRY
   ========================================================================== */
export function renderArenaWorkspace() {
  const container = document.getElementById('page-arena-workspace');
  if (!container) return;

  clearInterval(pollId);
  clearInterval(clockId);
  renderedKey = null;
  currentChallengeData = null;

  if (window.innerWidth < 800) return renderDesktopRequired(container);
  if (!store.isAuthenticated()) return renderUnauthenticated(container);

  if (!antiCheatReady) { setupAntiCheatListeners(); antiCheatReady = true; }

  refresh(container).then(() => {
    pollId = setInterval(() => {
      if (container.classList.contains('active') && store.isAuthenticated()) refresh(container, true);
    }, 2500);
  });
}

/* Render a screen only when it changes. `enter` runs once per change. */
function show(container, key, render, { focus = false, mood = 'calm' } = {}) {
  if (renderedKey === key) return false;
  renderedKey = key;
  document.body.classList.toggle('focus-mode', focus);
  setWormholeMood(mood);
  render();
  return true;
}

async function refresh(container, isBackground = false) {
  try {
    const status = await store.getArenaStatus();
    const st = status.status || 'waiting';
    syncClock(status);

    if (st === 'eliminated') return show(container, 'eliminated', () => renderEliminated(container, status));

    if (status.is_results_released || st === 'results_available') {
      if (renderedKey !== 'results') { renderedKey = 'results'; document.body.classList.remove('focus-mode'); setWormholeMood('calm'); await renderResults(container); }
      return;
    }

    if (st === 'waiting') return show(container, 'standby', () => renderStandby(container));

    const res = await store.getMyArenaChallenge();
    if (!res.success) {
      if (res.status === 'eliminated' || (res.error && res.error.toLowerCase().includes('eliminated'))) {
        return show(container, 'eliminated', () => renderEliminated(container, res));
      }
      if (!isBackground) show(container, 'error', () => renderError(container, res.error), { mood: 'dim' });
      return;
    }

    // Team's own status can lag behind global status — guard all per-team states
    const competitionStatus = res.competition_status || st;
    if (res.is_eliminated || competitionStatus === 'eliminated') {
      return show(container, 'eliminated', () => renderEliminated(container, res));
    }
    if (competitionStatus === 'waiting' || !res.challenge) {
      // Arena started globally but team session hasn't received a challenge yet — stay on standby
      return show(container, 'standby', () => renderStandby(container));
    }
    if (res.is_completed || res.is_arena_completed || competitionStatus === 'completed') {
      return show(container, 'done', () => renderCompleted(container, res));
    }

    const key = `live:${res.current_challenge_index || res.challenge_index}`;
    if (renderedKey === key) return;

    const cameFromStandby = renderedKey === 'standby';
    currentChallengeData = res;

    if (cameFromStandby) await playStartCountdown();
    show(container, key, () => renderChallenge(container, res), { focus: true, mood: 'focus' });
  } catch (err) {
    console.error('Error refreshing arena view:', err);
  }
}

/* ==========================================================================
   SMALL SCREENS: signed out / desktop only / error
   ========================================================================== */
function panel(container, { tone = 'cyan', title, body, actions = '' }) {
  container.innerHTML = `
    <div class="ar-center">
      <div class="ar-panel ar-panel-${tone}">
        <h1 class="heading-lg">${title}</h1>
        <p class="ar-panel-body">${body}</p>
        <div class="ar-panel-actions">${actions}</div>
      </div>
    </div>`;
}

function renderDesktopRequired(container) {
  setWormholeMood('calm');
  panel(container, {
    tone: 'amber',
    title: 'Open the arena on a laptop or desktop',
    body: 'The arena shows the broken prompt and your rewrite side by side and needs a screen at least 800 pixels wide. Widen the window or switch devices, then check again.',
    actions: '<button class="btn btn-primary" id="btnRecheck">Check again</button>'
  });
  document.getElementById('btnRecheck')?.addEventListener('click', () => renderArenaWorkspace());
}

function renderUnauthenticated(container) {
  setWormholeMood('calm');
  panel(container, {
    title: 'Sign in to enter the arena',
    body: 'Your five prompts are assigned to your team, so the arena opens once you’re signed in.',
    actions: '<button class="btn btn-primary" id="btnGoToLogin">Go to sign-in</button>'
  });
  document.getElementById('btnGoToLogin')?.addEventListener('click', () => Router.navigate('team-lobby'));
}

function renderError(container, message) {
  panel(container, {
    tone: 'red',
    title: 'Couldn’t load your prompt',
    body: escapeHtml(message || 'The server didn’t answer.') + ' Your draft is safe on this device.',
    actions: '<button class="btn btn-primary" id="btnRetry">Try again</button>'
  });
  document.getElementById('btnRetry')?.addEventListener('click', () => renderArenaWorkspace());
}

/* ==========================================================================
   ELIMINATED
   ========================================================================== */
function renderEliminated(container, data) {
  const reason = data.elimination_reason || data.reason || data.error ||
    'The panel removed this team for a rule or integrity violation.';
  container.innerHTML = `
    <div class="ar-center">
      <div class="ar-panel ar-panel-red">
        <h1 class="heading-lg">Your team is out of the arena</h1>
        <p class="ar-panel-body">The judging panel has removed this team from live competition. Submissions are closed.</p>
        <blockquote class="ar-reason"><span>Reason on record</span>${escapeHtml(reason)}</blockquote>
        <div class="ar-panel-actions"><button class="btn" id="btnEliminatedLogout">Sign out</button></div>
      </div>
    </div>`;
  document.getElementById('btnEliminatedLogout')?.addEventListener('click', () => Router.confirmLogout());
}

/* ==========================================================================
   STAND-BY
   ========================================================================== */
function renderStandby(container) {
  const user = store.data.currentUser || {};
  container.innerHTML = `
    <div class="ar-standby">
      <div class="ar-standby-main">
        <p class="ar-standby-team">${escapeHtml(user.name || 'Your team')}</p>
        <h1 class="heading-xl">Standing by</h1>
        <p class="ar-standby-sub">
          The arena opens for every team at the same moment. Keep this tab open and it will start on its own.
        </p>
        <p class="ar-waiting" role="status">
          <span class="ar-waiting-dots" aria-hidden="true"><i></i><i></i><i></i></span>
          Waiting for the director to start the round
        </p>
      </div>

      <div class="ar-brief">
        <section>
          <h2>How it runs</h2>
          <ul>
            <li>Five prompts, chosen for your team alone.</li>
            <li>Solve them in order. You can’t skip ahead.</li>
            <li>Locking a prompt is final and timestamped.</li>
          </ul>
        </section>
        <section>
          <h2>How it’s scored</h2>
          <p>Each prompt is worth 100 points: 20 for each of five criteria. Five prompts make 500.</p>
          <ul class="ar-criteria">
            ${CRITERIA.map(c => `<li>${c.label}</li>`).join('')}
          </ul>
        </section>
        <section>
          <h2>Fair play</h2>
          <p>Tab switches, window changes, leaving fullscreen, and pasting are logged. Stay in fullscreen once the round starts.</p>
        </section>
      </div>
    </div>`;
}

/* 3 – 2 – 1 – go, with a wormhole surge on each beat */
async function playStartCountdown() {
  const overlay = document.createElement('div');
  overlay.className = 'ar-countdown';
  overlay.setAttribute('role', 'status');
  overlay.innerHTML = '<div class="ar-cd-num" id="arCdNum">3</div><p class="ar-cd-note">The arena is opening</p>';
  document.body.appendChild(overlay);
  const num = overlay.querySelector('#arCdNum');

  for (const label of ['3', '2', '1', 'Go']) {
    num.textContent = label;
    num.classList.remove('beat'); void num.offsetWidth; num.classList.add('beat');
    warpWormhole(label === 'Go' ? 1.7 : 0.6);
    await sleep(label === 'Go' ? 700 : 850);
  }
  overlay.classList.add('out');
  await sleep(350);
  overlay.remove();
}

/* ==========================================================================
   LIVE CHALLENGE
   ========================================================================== */
function renderChallenge(container, res) {
  const challenge = res.challenge;
  // Safety guard: if challenge data is missing, fall back to standby instead of crashing
  if (!challenge) {
    console.warn('renderChallenge called with no challenge data, falling back to standby');
    return renderStandby(container);
  }
  const idx = res.current_challenge_index || res.challenge_index;
  const user = store.data.currentUser || {};
  const teamKey = user.teamId || user.id || 'team';
  const draftKey = `ARENA_DRAFT_${teamKey}_${idx}`;
  const noteKey = `ARENA_NOTE_${teamKey}_${idx}`;
  const savedDraft = safeGet(draftKey);
  const savedNote = safeGet(noteKey);
  const diff = (challenge.difficulty || 'medium').toLowerCase();
  const diffTone = diff === 'easy' ? 'green' : diff === 'hard' ? 'red' : 'amber';
  const isLast = idx === 5;

  container.innerHTML = `
    <div class="ar-live">
      <header class="ar-hud">
        <div class="ar-hud-team">
          <span class="ar-hud-mark" aria-hidden="true">N</span>
          <span class="ar-hud-name">${escapeHtml(user.name || 'Team')}</span>
        </div>

        <ol class="ar-rail" aria-label="Progress: prompt ${idx} of 5">
          ${[1, 2, 3, 4, 5].map(n => {
            const st = n < idx ? 'done' : n === idx ? 'current' : 'todo';
            return `<li class="ar-node ${st}" ${st === 'current' ? 'aria-current="step"' : ''}>
                      <span class="ar-node-dot">${st === 'done' ? CHECK : n}</span>
                    </li>`;
          }).join('')}
        </ol>

        <div class="ar-hud-right">
          <div class="ar-clock" id="arenaClock" hidden>
            <span class="ar-clock-num" id="arenaClockText">--:--</span>
            <span class="ar-clock-label">left</span>
          </div>
          <button class="ar-icon-btn" id="btnToggleFullscreen" title="Toggle fullscreen" aria-label="Toggle fullscreen">
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 8V3h5M12 3h5v5M17 12v5h-5M8 17H3v-5"/></svg>
          </button>
          <button class="btn btn-sm btn-ghost" id="btnChallengeLogout">Exit</button>
        </div>
      </header>

      <div class="ar-notice" id="arenaSecurityBanner" role="status" ${securityViolationCount > 0 ? '' : 'hidden'}></div>

      <main class="ar-bench">
        <!-- LEFT: the case file -->
        <section class="ar-case" aria-label="Broken prompt">
          <div class="ar-case-meta">
            <span class="chip chip-${diffTone}">${escapeHtml(capitalize(diff))}</span>
            <span class="ar-case-cat">${escapeHtml(challenge.category || 'General')}</span>
            <span class="ar-case-count">Prompt ${idx} of 5</span>
          </div>

          <h1 class="ar-case-title">${escapeHtml(challenge.title)}</h1>

          <h2 class="ar-label">The situation</h2>
          <p class="ar-scenario">${escapeHtml(challenge.scenario || challenge.bad_output_evidence)}</p>

          <h2 class="ar-label ar-label-fault"><span class="ar-fault-dot" aria-hidden="true"></span>Broken prompt</h2>
          <blockquote class="ar-specimen" id="flawedPromptBox">${escapeHtml(challenge.flawed_prompt || challenge.original_bad_prompt)}</blockquote>

          <h2 class="ar-label">Ask the broken prompt</h2>
          <ul class="ar-asks">
            <li>What exactly is the task?</li>
            <li>Who is the model, and who is the answer for?</li>
            <li>What does a good answer look like?</li>
            <li>Which limits or rules apply?</li>
            <li>What should happen when the input is odd?</li>
          </ul>
        </section>

        <!-- RIGHT: the repair -->
        <section class="ar-editor" aria-label="Your rewrite">
          <div class="ar-editor-head">
            <label for="refactoredPromptInput" class="ar-label ar-label-fix"><span class="ar-fix-dot" aria-hidden="true"></span>Your rewrite</label>
            <span class="ar-save" id="autoSaveIndicator">${savedDraft ? 'Draft restored' : 'Saved as you type'}</span>
          </div>

          <div class="ar-editor-body ${ARENA_UI.showCoverage ? 'has-radar' : ''}">
            <div class="ar-write">
              <div class="ar-textwrap">
                <textarea id="refactoredPromptInput" spellcheck="true" maxlength="${ARENA_UI.maxChars}"
                  placeholder="Rewrite the prompt so the model can’t misread it.&#10;&#10;Think: who the model is, what it must do, what the answer looks like, and what to do when the input is odd."></textarea>
                <div class="ar-textfoot">
                  <div class="ar-meter" aria-hidden="true"><i id="charMeter"></i></div>
                  <span class="ar-count" id="charCounter">0 / ${ARENA_UI.maxChars}</span>
                </div>
              </div>

              <div class="field ar-note">
                <label for="diagnosisNotesInput">What was wrong, and what did you change? <span class="ar-optional">Optional, but judges read it</span></label>
                <input type="text" id="diagnosisNotesInput" maxlength="255" placeholder="e.g. Added a JSON schema and told it what to do when the message is unclear.">
              </div>
            </div>

            ${ARENA_UI.showCoverage ? `
            <aside class="ar-coverage" aria-label="Draft coverage">
              <h2 class="ar-label">Draft coverage</h2>
              <div id="radarMount"></div>
              <p class="ar-cover-hint" id="coverHint">Start writing and the chart fills in.</p>
              <p class="ar-cover-fine">A rough read of what your draft mentions. It isn’t your score; judges score the locked prompt.</p>
            </aside>` : ''}
          </div>

          <footer class="ar-lockbar">
            <p class="ar-lockbar-msg" id="lockHint">Locking is final and records your time.</p>
            <button class="btn btn-primary btn-lg" id="btnSubmitChallenge">
              ${isLast ? 'Lock final prompt' : `Lock prompt ${idx}`}
            </button>
          </footer>
        </section>
      </main>
    </div>`;

  /* ---- wire up the editor ------------------------------------------------ */
  const textarea = container.querySelector('#refactoredPromptInput');
  const noteInput = container.querySelector('#diagnosisNotesInput');
  const counter = container.querySelector('#charCounter');
  const meter = container.querySelector('#charMeter');
  const saveEl = container.querySelector('#autoSaveIndicator');
  const submitBtn = container.querySelector('#btnSubmitChallenge');
  const lockHint = container.querySelector('#lockHint');
  const coverHint = container.querySelector('#coverHint');

  textarea.value = savedDraft;
  noteInput.value = savedNote;

  const radar = ARENA_UI.showCoverage ? mountRadar(container.querySelector('#radarMount')) : null;
  const HINTS = [
    'Say what the task is, and why it’s needed.',
    'Add numbers, limits, or an example.',
    'Tell the model who it is and who the answer is for.',
    'Describe the exact shape of the answer.',
    'Say what to do when the input is missing or odd.'
  ];

  let coverTimer = 0;
  const updateCoverage = () => {
    if (!radar) return;
    const vals = analyzePrompt(textarea.value);
    radar.set(vals);
    if (textarea.value.trim().length < 20) { coverHint.textContent = 'Start writing and the chart fills in.'; return; }
    const low = vals.indexOf(Math.min(...vals));
    coverHint.textContent = vals[low] < 0.5 ? HINTS[low] : 'Every criterion is covered. Tighten the wording.';
  };

  const updateCount = () => {
    const len = textarea.value.length;
    counter.textContent = `${len} / ${ARENA_UI.maxChars}`;
    meter.style.width = `${Math.min(100, (len / ARENA_UI.maxChars) * 100)}%`;
    const near = len >= ARENA_UI.maxChars * 0.95;
    counter.classList.toggle('is-near', near);
    meter.classList.toggle('is-near', near);
  };

  let saveTimer = 0;
  const markSaved = () => {
    saveEl.textContent = 'Saving…';
    saveEl.classList.remove('is-ok');
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { saveEl.textContent = 'Draft saved'; saveEl.classList.add('is-ok'); }, 450);
  };

  updateCount();
  updateCoverage();

  textarea.addEventListener('input', () => {
    updateCount();
    safeSet(draftKey, textarea.value);
    markSaved();
    clearTimeout(coverTimer);
    coverTimer = setTimeout(updateCoverage, 140);
    lockHint.textContent = 'Locking is final and records your time.';
    lockHint.classList.remove('is-error');
  });
  noteInput.addEventListener('input', () => { safeSet(noteKey, noteInput.value); markSaved(); });

  // Anti-cheat: log pastes into the editor, block copying the broken prompt
  textarea.addEventListener('paste', (e) => {
    const len = (e.clipboardData || window.clipboardData)?.getData('text')?.length || 0;
    store.logSecurityEvent('PASTE_EVENT', { challenge_index: idx, char_count: len });
  });
  const specimen = container.querySelector('#flawedPromptBox');
  specimen.addEventListener('copy', (e) => {
    e.preventDefault();
    Router.showToast('Copying the challenge prompt is turned off.', 'amber');
    store.logSecurityEvent('COPY_ATTEMPT', { challenge_index: idx });
  });
  specimen.addEventListener('contextmenu', (e) => e.preventDefault());

  container.querySelector('#btnToggleFullscreen').addEventListener('click', () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(err => console.warn('Fullscreen denied:', err));
    else document.exitFullscreen().catch(err => console.warn(err));
  });
  container.querySelector('#btnChallengeLogout').addEventListener('click', () => {
    Router.confirmLogout('Your draft stays on this device, so you can pick up where you left off.');
  });

  /* ---- lock ------------------------------------------------------------- */
  submitBtn.addEventListener('click', () => {
    const fixed = textarea.value.trim();
    const complain = (msg) => { lockHint.textContent = msg; lockHint.classList.add('is-error'); textarea.focus(); };

    if (!fixed) return complain('Write your rewrite before locking.');
    if (fixed.length < ARENA_UI.minChars) return complain('That’s too short to be a real prompt. Add the task, the format, and the rules.');

    const note = noteInput.value.trim();
    confirmLock({ idx, isLast, chars: fixed.length, hasNote: !!note }, async () => {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Locking…';

      const res2 = await store.submitArenaChallenge({
        prompt_text: fixed
      });

      if (res2.success) {
        safeRemove(draftKey); safeRemove(noteKey);
        warpWormhole(1.6);
        Router.showToast(isLast ? 'All five prompts locked.' : `Prompt ${idx} locked.`, 'green');
        await refresh(container);
      } else {
        submitBtn.disabled = false;
        submitBtn.textContent = isLast ? 'Lock final prompt' : `Lock prompt ${idx}`;
        complain(res2.error || 'The server didn’t accept that. Try again.');
        Router.showToast(res2.error || 'Lock failed', 'red');
      }
    });
  });

  // First paint: focus the editor so players can type immediately
  setTimeout(() => textarea.focus({ preventScroll: true }), 350);
  startClock();
}

function confirmLock({ idx, isLast, chars, hasNote }, onConfirm) {
  const overlay = document.createElement('div');
  overlay.className = 'neura-modal-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.innerHTML = `
    <div class="neura-modal" style="max-width:440px; width:100%; padding:28px;">
      <h3 class="modal-title">${isLast ? 'Lock your final prompt?' : `Lock prompt ${idx} of 5?`}</h3>
      <p class="modal-body">
        This can’t be changed afterwards, and your time is recorded for tie-breaks.
        <span class="ar-confirm-facts">${chars} characters · ${hasNote ? 'note added' : 'no note added'}</span>
      </p>
      <div class="modal-actions">
        <button class="btn" id="btnCancelModalSubmit">Keep editing</button>
        <button class="btn btn-primary" id="btnConfirmModalSubmit">Lock it in</button>
      </div>
    </div>`;
  (document.getElementById('customModalContainer') || document.body).appendChild(overlay);

  const close = () => overlay.remove();
  overlay.querySelector('#btnCancelModalSubmit').addEventListener('click', close);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  overlay.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
  overlay.querySelector('#btnConfirmModalSubmit').addEventListener('click', () => { close(); onConfirm(); });
  overlay.querySelector('#btnConfirmModalSubmit').focus();
}

/* ==========================================================================
   ROUND CLOCK
   Uses whatever the server reports (remaining_seconds, or ends_at / end_time).
   If it reports nothing, the clock stays hidden rather than showing a guess.
   ========================================================================== */
function syncClock(status) {
  let next = null;
  if (typeof status.remaining_seconds === 'number') next = Date.now() + status.remaining_seconds * 1000;
  else if (status.ends_at || status.end_time) {
    const t = Date.parse(status.ends_at || status.end_time);
    if (!Number.isNaN(t)) next = t;
  }
  endsAt = next;
}

function startClock() {
  clearInterval(clockId);
  const tick = () => {
    const wrap = document.getElementById('arenaClock');
    const text = document.getElementById('arenaClockText');
    if (!wrap || !text) return;
    if (endsAt == null) { wrap.hidden = true; return; }

    const left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
    const h = Math.floor(left / 3600), m = Math.floor((left % 3600) / 60), s = left % 60;
    text.textContent = h > 0
      ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
      : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    wrap.hidden = false;
    wrap.classList.toggle('is-warn', left <= 600 && left > 120);
    wrap.classList.toggle('is-crit', left <= 120);
  };
  tick();
  clockId = setInterval(tick, 1000);
}

/* ==========================================================================
   ALL LOCKED — waiting on the judges
   ========================================================================== */
function renderCompleted(container, res) {
  document.body.classList.remove('focus-mode');
  setWormholeMood('calm');
  clearInterval(clockId);

  const user = store.data.currentUser || {};
  const when = res.completed_at ? new Date(res.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : null;

  container.innerHTML = `
    <div class="ar-center">
      <div class="ar-done">
        <ol class="ar-rail ar-rail-lg" aria-label="All five prompts locked">
          ${[1, 2, 3, 4, 5].map(() => `<li class="ar-node done"><span class="ar-node-dot">${CHECK}</span></li>`).join('')}
        </ol>
        <h1 class="heading-xl">All five locked</h1>
        <p class="ar-done-sub">
          ${escapeHtml(user.name || 'Your team')}’s prompts are stored and timestamped. The judges are scoring them now.
          Your report appears here as soon as results are released.
        </p>
        <p class="ar-waiting" role="status">
          <span class="ar-waiting-dots" aria-hidden="true"><i></i><i></i><i></i></span>
          With the judges${when ? ` · finished at ${escapeHtml(when)}` : ''}
        </p>
        <div class="ar-panel-actions">
          <button class="btn" id="btnCheckStatus">Check now</button>
          <button class="btn btn-ghost" id="btnCompletedLogout">Sign out</button>
        </div>
      </div>
    </div>`;

  document.getElementById('btnCheckStatus')?.addEventListener('click', async (e) => {
    e.currentTarget.disabled = true;
    await refresh(container);
    if (renderedKey === 'done') { Router.showToast('Still with the judges.', 'cyan'); e.currentTarget.disabled = false; }
  });
  document.getElementById('btnCompletedLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Your five locked prompts stay safely with the judges.');
  });
}

/* ==========================================================================
   RESULTS
   ========================================================================== */
async function renderResults(container) {
  clearInterval(clockId);
  const res = await store.getMyArenaResults();

  if (!(res.success && res.challenges && res.challenges.length)) {
    const rep = await store.getArenaReport();
    if (!rep.success) {
      return panel(container, {
        tone: 'violet',
        title: 'Scores are being finalised',
        body: 'The panel is finishing its scoring. This page updates on its own.',
        actions: '<button class="btn btn-primary" id="btnRecheck">Check now</button>'
      }), document.getElementById('btnRecheck')?.addEventListener('click', () => { renderedKey = null; refresh(container); });
    }
    const r = rep.report;
    container.innerHTML = `
      <div class="ar-center"><div class="ar-panel">
        <h1 class="heading-lg">${escapeHtml(r.team_name)}</h1>
        <p class="ar-panel-body">${r.challenges_completed} of 5 prompts scored · ${r.total_score} points${r.current_rank ? ` · rank #${r.current_rank}` : ''}</p>
        <div class="ar-panel-actions">
          <button class="btn btn-violet" id="btnViewArenaLeaderboard">View the leaderboard</button>
          <button class="btn btn-ghost" id="btnReportLogout">Sign out</button>
        </div>
      </div></div>`;
    wireResultButtons();
    return;
  }

  const chs = res.challenges;
  const avg = (key) => chs.reduce((a, c) => a + (c.characteristics?.[key] || 0), 0) / chs.length;
  const avgs = CRITERIA.map(c => avg(c.key));
  const podium = res.rank === 1 ? 'First place' : res.rank === 2 ? 'Second place' : res.rank === 3 ? 'Third place' : '';
  const timeStr = (iso) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'recorded';

  container.innerHTML = `
    <div class="ar-results">
      <header class="ar-res-head">
        <div>
          <p class="eyebrow">Official results${res.college ? ' · ' + escapeHtml(res.college) : ''}</p>
          <h1 class="heading-lg">${escapeHtml(res.team_name)}</h1>
          ${podium ? `<span class="chip chip-${res.rank === 1 ? 'green' : res.rank === 2 ? 'cyan' : 'violet'}" style="margin-top:10px;">${podium}</span>` : ''}
        </div>
        <div class="ar-res-stats">
          <div class="ar-stat"><b>${escapeHtml(res.total_score)}</b><span>of 500 points</span></div>
          <div class="ar-stat"><b>${res.rank ? '#' + escapeHtml(res.rank) : '—'}</b><span>rank</span></div>
        </div>
      </header>

      <section class="ar-res-summary">
        <div class="ar-res-radar" id="resRadar"></div>
        <div>
          <h2 class="ar-label">Average per criterion, out of 20</h2>
          <ul class="ar-bars">
            ${CRITERIA.map((c, i) => `
              <li>
                <div class="ar-bar-row"><span>${c.label}</span><b>${avgs[i].toFixed(1)}</b></div>
                <div class="ar-bar"><i style="width:${Math.round((avgs[i] / 20) * 100)}%"></i></div>
              </li>`).join('')}
          </ul>
        </div>
      </section>

      <section class="ar-res-list" aria-label="Your five prompts">
        <h2 class="ar-label">Your five prompts</h2>
        ${chs.map((c, n) => `
          <details class="ar-res-item" ${n === 0 ? 'open' : ''}>
            <summary>
              <span class="ar-res-n">${escapeHtml(c.challenge_index)}</span>
              <span class="ar-res-title">${escapeHtml(c.title)}<em>${escapeHtml(c.category || 'General')}</em></span>
              <span class="ar-res-score"><b>${escapeHtml(c.score)}</b> / 100</span>
            </summary>
            <div class="ar-res-body">
              <p class="ar-label">What you locked at ${escapeHtml(timeStr(c.server_timestamp))}</p>
              <pre class="ar-locked">${escapeHtml(c.submitted_prompt)}</pre>
              <ul class="ar-chars">
                ${CRITERIA.map(k => `<li><span>${k.label}</span><b>${c.characteristics?.[k.key] ?? 0}<small>/20</small></b></li>`).join('')}
              </ul>
              ${c.judge_feedback ? `<blockquote class="ar-feedback"><span>Judge feedback</span>${escapeHtml(c.judge_feedback)}</blockquote>` : ''}
            </div>
          </details>`).join('')}
      </section>

      <footer class="ar-res-foot">
        <button class="btn btn-violet btn-lg" id="btnViewArenaLeaderboard">View the leaderboard</button>
        <button class="btn btn-ghost" id="btnReportLogout">Sign out</button>
      </footer>
    </div>`;

  const radar = mountRadar(container.querySelector('#resRadar'), { tone: 'green', title: 'Average judge score per criterion' });
  requestAnimationFrame(() => radar.set(avgs.map(v => v / 20)));
  wireResultButtons();
}

function wireResultButtons() {
  document.getElementById('btnViewArenaLeaderboard')?.addEventListener('click', () => Router.navigate('spectator-view'));
  document.getElementById('btnReportLogout')?.addEventListener('click', () => Router.confirmLogout());
}

/* ==========================================================================
   ANTI-CHEAT TELEMETRY — same signals as before
   ========================================================================== */
function isLiveNow() {
  const active = document.getElementById('page-arena-workspace')?.classList.contains('active');
  return !!(active && currentChallengeData && !currentChallengeData.is_arena_completed && renderedKey?.startsWith('live:'));
}

function setupAntiCheatListeners() {
  const flag = (type, message) => {
    securityViolationCount++;
    store.logSecurityEvent(type, { challenge_index: currentChallengeData.challenge_index, violation_count: securityViolationCount });
    triggerSecurityAlert(message);
  };

  document.addEventListener('visibilitychange', () => {
    if (document.hidden && isLiveNow()) flag('TAB_SWITCH', 'You switched tabs.');
  });
  window.addEventListener('blur', () => {
    if (isLiveNow()) flag('WINDOW_BLUR', 'The arena window lost focus.');
  });
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement && isLiveNow()) flag('FULLSCREEN_EXIT', 'You left fullscreen.');
  });
  document.addEventListener('contextmenu', (e) => {
    if (isLiveNow() && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') e.preventDefault();
  });
}

function triggerSecurityAlert(message) {
  const banner = document.getElementById('arenaSecurityBanner');
  if (!banner) return;
  banner.hidden = false;
  banner.innerHTML = `
    <span><strong>Logged:</strong> ${escapeHtml(message)} That’s ${securityViolationCount} on record. Every event is visible to the judges.</span>
    <button class="btn btn-sm btn-ghost" id="btnDismissNotice">Dismiss</button>`;
  banner.classList.remove('flash'); void banner.offsetWidth; banner.classList.add('flash');
  banner.querySelector('#btnDismissNotice')?.addEventListener('click', () => { banner.hidden = true; });
}

/* ==========================================================================
   Helpers
   ========================================================================== */
function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
function safeGet(k) { try { return localStorage.getItem(k) || ''; } catch { return ''; } }
function safeSet(k, v) { try { localStorage.setItem(k, v); } catch { /* storage full or blocked */ } }
function safeRemove(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } }
