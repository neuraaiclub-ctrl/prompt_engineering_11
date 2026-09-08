/* ==========================================================================
   NEURA ROUND 2 WORKSPACE VIEW - CONSTRAINT-BASED CHALLENGE
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { AIProviderAdapter } from '../ai-provider.js';

let activeChalIndex = 0;

export function renderRound2Workspace() {
  const container = document.getElementById('page-r2-workspace');
  if (!container) return;

  const challenges = store.getRound2Challenges();
  const activeChal = challenges[activeChalIndex] || challenges[0];
  const user = store.data.currentUser;
  const teamId = user.teamId;

  const submission = store.getSubmission(activeChal.id, teamId);
  const isSubmitted = !!submission;

  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-end;" class="mb-4">
      <div>
        <div class="eyebrow">Round 02 // Constraint-Based Challenge</div>
        <h1 class="heading-lg" style="margin-top:4px;">SINGLE PROMPT WORKSPACE</h1>
        <p class="sub-text">Solve the fixed task under strict artificial constraints. You get <strong>exactly ONE final submission</strong> for automated hidden-test scoring.</p>
      </div>

      <!-- Challenge Switcher Tabs -->
      <div style="display:flex; gap:8px;">
        ${challenges.map((ch, idx) => `
          <button class="btn btn-sm ${idx === activeChalIndex ? 'btn-violet' : ''}" onclick="window.switchR2Challenge(${idx})">
            ${ch.title.split('—')[1] || ch.title}
          </button>
        `).join('')}
      </div>
    </div>

    <!-- Workspace Grid -->
    <div class="workspace-grid">
      <!-- LEFT: Task Description & Constraint Rules -->
      <div class="glass bracket-frame" style="padding:24px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center;" class="mb-2">
          <div class="eyebrow">Task Specification</div>
          <span class="chip chip-violet">${activeChal.constraintType.toUpperCase()}</span>
        </div>

        <h3 class="heading-md" style="color:var(--cyan); margin-bottom:12px;">${activeChal.title}</h3>
        <p class="sub-text" style="margin-bottom:18px;">${activeChal.taskDescription}</p>

        <!-- Constraint Details Card -->
        <div class="glass-card" style="padding:16px; margin-bottom:18px;">
          <div class="eyebrow" style="margin-bottom:6px; color:var(--amber);">Active Constraint Rule</div>
          <div style="font-family:var(--mono); font-size:13px; color:var(--text); margin-bottom:8px;">
            ${activeChal.constraintType === 'max_tokens_50' ? '⚠️ PROMPT LENGTH MUST BE UNDER 50 TOKENS.' : '⚠️ OUTPUT MUST BE VALID JSON MATCHING SCHEMA.'}
          </div>
          <div style="font-family:var(--mono); font-size:11.5px; color:var(--muted);">${activeChal.formatRule}</div>
        </div>

        <!-- Hidden Test Disclosure Panel -->
        <div class="glass-card" style="padding:16px;">
          <div class="eyebrow" style="margin-bottom:6px;">Hidden Evaluation Suite</div>
          <div style="font-family:var(--mono); font-size:12px; color:var(--text); margin-bottom:6px;">
            🔒 5 Hidden Unseen Test Cases Configured
          </div>
          <div style="font-family:var(--mono); font-size:11px; color:var(--muted);">
            Test inputs and expected outputs are encrypted. Results are disclosed strictly as aggregate pass counts upon submission.
          </div>
        </div>
      </div>

      <!-- RIGHT: Single Final Prompt Submission Surface -->
      <div class="glass bracket-frame" style="padding:24px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <div class="eyebrow">Submission Surface</div>
          ${isSubmitted ? `<span class="chip chip-green">🔒 FINAL SUBMISSION LOCKED</span>` : `<span class="chip chip-amber">ONE SUBMISSION ALLOWED</span>`}
        </div>

        <!-- Live Token Counter Bar -->
        <div class="token-counter-bar">
          <span>TOKEN COUNT: <strong id="r2TokenCountDisplay">0</strong> / ${activeChal.maxTokens}</span>
          <span id="r2TokenStatus" style="color:var(--green);">COMPLIANT</span>
        </div>
        <div class="token-progress-track mb-3">
          <div id="r2TokenBarFill" class="token-progress-fill" style="width:0%;"></div>
        </div>

        <!-- Final Prompt Text Input -->
        <div class="field">
          <label>Final Prompt Content</label>
          <textarea id="r2PromptInput" rows="6" ${isSubmitted ? 'disabled' : ''} placeholder="Write your optimized, constraint-compliant prompt here...">${isSubmitted ? escapeHtml(submission.promptText) : ''}</textarea>
        </div>

        <!-- Technique Explanation Input -->
        <div class="field">
          <label style="color:var(--violet);">Technique Explanation (Briefly explain your approach)</label>
          <input type="text" id="r2TechniqueInput" ${isSubmitted ? 'disabled' : ''} placeholder="e.g. Applied role prompting with zero-shot format constraints to stay under 20 tokens." value="${isSubmitted ? escapeHtml(submission.explanation) : ''}">
        </div>

        <!-- Submission Status Result (if submitted) -->
        ${isSubmitted ? `
          <div class="glass-card" style="padding:16px; border-color:var(--green); background:rgba(78,230,168,0.05); margin-bottom:18px; text-align:center;">
            <div style="font-family:var(--disp); font-size:18px; font-weight:700; color:var(--green); margin-bottom:4px;">
              ✓ SUBMITTED & EVALUATED
            </div>
            <div style="font-family:var(--mono); font-size:22px; font-weight:700; color:var(--cyan); margin:8px 0;">
              PASSED: ${submission.passCount} / ${submission.totalCount} HIDDEN TESTS
            </div>
            <div style="font-family:var(--mono); font-size:11px; color:var(--muted);">
              Submitted at ${submission.submittedAt} · Constraint Status: ${submission.constraintViolated ? '<span style="color:var(--red);">VIOLATED (PENALIZED)</span>' : '<span style="color:var(--green);">VERIFIED COMPLIANT</span>'}
            </div>
          </div>
        ` : ''}

        <!-- Submit Button -->
        <div style="display:flex; justify-content:flex-end;">
          <button class="btn btn-primary" id="btnR2SubmitFinal" ${isSubmitted ? 'disabled' : ''}>
            SUBMIT FINAL PROMPT FOR HIDDEN TESTING →
          </button>
        </div>
      </div>

    </div>
  `;

  // Attach handlers
  window.switchR2Challenge = (idx) => {
    activeChalIndex = idx;
    renderRound2Workspace();
  };

  const promptInput = document.getElementById('r2PromptInput');
  const techniqueInput = document.getElementById('r2TechniqueInput');
  const tokenDisplay = document.getElementById('r2TokenCountDisplay');
  const tokenStatus = document.getElementById('r2TokenStatus');
  const tokenBarFill = document.getElementById('r2TokenBarFill');
  const submitBtn = document.getElementById('btnR2SubmitFinal');

  const updateTokens = () => {
    if (!promptInput) return;
    const count = AIProviderAdapter.countTokens(promptInput.value);
    const max = activeChal.maxTokens;
    tokenDisplay.textContent = count;
    
    const pct = Math.min(100, Math.round((count / max) * 100));
    tokenBarFill.style.width = pct + '%';

    if (count > max) {
      tokenStatus.textContent = 'OVER LIMIT';
      tokenStatus.style.color = 'var(--red)';
      tokenBarFill.classList.add('overlimit');
    } else {
      tokenStatus.textContent = 'COMPLIANT';
      tokenStatus.style.color = 'var(--green)';
      tokenBarFill.classList.remove('overlimit');
    }
  };

  promptInput?.addEventListener('input', updateTokens);
  updateTokens();

  submitBtn?.addEventListener('click', async () => {
    const text = promptInput.value.trim();
    const tech = techniqueInput.value.trim();
    if (!text) { Router.showToast('Prompt text cannot be empty', 'red'); return; }
    if (!tech) { Router.showToast('Technique explanation is required', 'red'); return; }

    const confirmSubmit = confirm("ARE YOU SURE?\nRound 2 allows exactly ONE final prompt submission. Once submitted, your prompt will be executed live against all hidden test cases and locked.");
    if (!confirmSubmit) return;

    submitBtn.disabled = true;
    submitBtn.textContent = '⚡ RUNNING HIDDEN TESTS...';

    // Execute automated hidden test evaluation
    const hiddenTests = store.data.hiddenTestCases;
    const evalRes = await AIProviderAdapter.evaluateHiddenTests(activeChal.id, text, hiddenTests);
    
    const count = AIProviderAdapter.countTokens(text);
    const constraintViolated = count > activeChal.maxTokens;

    store.submitRound2(activeChal.id, teamId, text, tech, evalRes.passCount, evalRes.totalCount, constraintViolated);

    Router.showToast(`Round 2 Submitted! Passed ${evalRes.passCount}/${evalRes.totalCount} Hidden Tests.`, 'green');
    renderRound2Workspace();
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
