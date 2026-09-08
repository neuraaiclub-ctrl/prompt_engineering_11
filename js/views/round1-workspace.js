/* ==========================================================================
   NEURA ITERATIVE PROMPT WORKSPACE VIEW - FIX THE PROMPT
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { AIProviderAdapter } from '../ai-provider.js';

let activeCaseIndex = 0;

export function renderRound1Workspace() {
  const container = document.getElementById('page-r1-workspace');
  if (!container) return;

  const cases = store.getRound1Cases();
  const activeCase = cases[activeCaseIndex] || cases[0];
  const user = store.data.currentUser;
  const teamId = user.teamId;

  const versions = store.getVersionsForCase(activeCase.id, teamId);
  const submission = store.getSubmission(activeCase.id, teamId);

  const isSubmitted = !!submission;

  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-end;" class="mb-4">
      <div>
        <div class="eyebrow">Competition // Fix the Prompt</div>
        <h1 class="heading-lg" style="margin-top:4px;">ITERATIVE PROMPT WORKSPACE</h1>
        <p class="sub-text">Diagnose why the original prompt failed, iterate your prompt, and document each change with a required explanation.</p>
      </div>

      <!-- Case Switcher Tabs & Logout -->
      <div style="display:flex; gap:10px; align-items:center;">
        ${cases.map((c, idx) => `
          <button class="btn btn-sm ${idx === activeCaseIndex ? 'btn-primary' : ''}" onclick="window.switchR1Case(${idx})">
            ${c.title.split('—')[1] || c.title}
          </button>
        `).join('')}
        <button class="btn btn-sm btn-red" id="btnR1Logout" style="padding:6px 14px; font-size:11px; font-weight:700; cursor:pointer;">
          ⎋ LOGOUT
        </button>
      </div>
    </div>

    <!-- Workspace Grid: Left Evidence Panel, Right Editor -->
    <div class="workspace-grid">
      <!-- LEFT: Case Evidence & Bad Output -->
      <div class="evidence-panel glass bracket-frame">
        <span class="bl"></span><span class="br"></span>
        <div class="evidence-header">
          <div class="evidence-eyebrow">EVIDENCE CASE FILE</div>
          <span class="evidence-pill-${activeCase.difficulty === 'hard' ? 'red' : activeCase.difficulty === 'easy' ? 'green' : 'amber'}">${activeCase.difficulty.toUpperCase()}</span>
        </div>

        <h3 class="evidence-title">${activeCase.title}</h3>
        <p class="evidence-desc">${activeCase.description}</p>

        <!-- Original Broken Prompt Box -->
        <div class="evidence-section">
          <div class="evidence-eyebrow">ORIGINAL BAD PROMPT</div>
          <div class="evidence-block">${escapeHtml(activeCase.originalPrompt)}</div>
        </div>

        <!-- Bad Output Evidence Box -->
        <div class="evidence-section">
          <div class="evidence-eyebrow red">ORIGINAL BAD OUTPUT (EVIDENCE)</div>
          <div class="evidence-block bad-output">${escapeHtml(activeCase.badOutput)}</div>
        </div>
      </div>

      <!-- RIGHT: Iterative Prompt Editor & Version History -->
      <div style="display:flex; flex-direction:column; gap:20px;">
        
        <!-- Editor Box -->
        <div class="glass bracket-frame" style="padding:22px;">
          <span class="bl"></span><span class="br"></span>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <div class="eyebrow">Prompt Editor</div>
            ${isSubmitted ? `<span class="chip chip-green">🔒 SUBMITTED & LOCKED</span>` : `<span class="chip chip-cyan">DRAFTING VERSION ${versions.length + 1}</span>`}
          </div>

          <!-- Prompt Text Area -->
          <div class="field">
            <label>Improved Prompt Text</label>
            <textarea id="r1PromptInput" rows="5" ${isSubmitted ? 'disabled' : ''} placeholder="Rewrite the prompt to solve the formatting/logic failure...">${versions.length > 0 ? escapeHtml(versions[versions.length - 1].promptText) : escapeHtml(activeCase.originalPrompt)}</textarea>
          </div>

          <!-- Mandatory 1-Line Explanation Field -->
          <div class="field">
            <label style="color:var(--amber);">Mandatory Explanation (What changed & why it helps)</label>
            <input type="text" id="r1ExplanationInput" ${isSubmitted ? 'disabled' : ''} placeholder="e.g. Added strict JSON schema rules to eliminate unformatted narrative prose." value="${versions.length > 0 ? escapeHtml(versions[versions.length - 1].explanation) : ''}">
          </div>

          <!-- Execution Preview Response Panel -->
          <div id="executionResultBox" style="display:none; margin-bottom:16px;" class="glass-card">
            <div style="padding:10px 14px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; font-family:var(--mono); font-size:11px;">
              <span style="color:var(--cyan);">MODEL OUTPUT PREVIEW</span>
              <span id="executionMeta" style="color:var(--muted);">LATENCY: --ms | TOKENS: --</span>
            </div>
            <pre id="executionText" style="padding:14px; font-family:var(--mono); font-size:12px; color:var(--text); white-space:pre-wrap; max-height:160px; overflow-y:auto;"></pre>
          </div>

          <!-- Actions Row -->
          <div style="display:flex; gap:12px; justify-content:flex-end;">
            <button class="btn" id="btnR1Run" ${isSubmitted ? 'disabled' : ''}>⚡ PREVIEW RUN</button>
            <button class="btn btn-violet" id="btnR1SaveVer" ${isSubmitted ? 'disabled' : ''}>+ SAVE VERSION</button>
            <button class="btn btn-primary" id="btnR1Submit" ${isSubmitted ? 'disabled' : ''}>SUBMIT FINAL CASE →</button>
          </div>
        </div>

        <!-- Version History Timeline -->
        <div class="glass bracket-frame" style="padding:22px;">
          <span class="bl"></span><span class="br"></span>
          <div class="eyebrow" style="margin-bottom:12px;">Iteration History (${versions.length} Versions)</div>

          <div class="version-timeline">
            ${versions.length === 0 ? `<div style="color:var(--muted); font-size:12.5px; font-family:var(--mono);">No versions saved yet. Edit prompt and click "+ SAVE VERSION".</div>` : ''}
            ${versions.map(v => `
              <div class="version-item ${v.isFinal ? 'final' : ''}">
                <div class="version-header">
                  <span class="version-tag">VERSION ${String(v.versionNumber).padStart(2, '0')} ${v.isFinal ? '✓ [FINAL]' : ''}</span>
                  <span style="color:var(--muted);">${v.timestamp}</span>
                </div>
                <div style="font-family:var(--mono); font-size:12px; color:var(--cyan-dim); margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                  "${escapeHtml(v.promptText)}"
                </div>
                <div class="version-explanation">
                  <strong style="color:var(--amber);">Reasoning:</strong> ${escapeHtml(v.explanation)}
                </div>
              </div>
            `).join('')}
          </div>
        </div>

      </div>
    </div>
  `;

  // Attach handlers
  window.switchR1Case = (idx) => {
    activeCaseIndex = idx;
    renderRound1Workspace();
  };

  const promptInput = document.getElementById('r1PromptInput');
  const explanationInput = document.getElementById('r1ExplanationInput');
  const runBtn = document.getElementById('btnR1Run');
  const saveBtn = document.getElementById('btnR1SaveVer');
  const submitBtn = document.getElementById('btnR1Submit');
  const resultBox = document.getElementById('executionResultBox');
  const resultText = document.getElementById('executionText');
  const resultMeta = document.getElementById('executionMeta');

  runBtn?.addEventListener('click', async () => {
    const text = promptInput.value.trim();
    if (!text) return;
    runBtn.disabled = true;
    runBtn.textContent = '⚡ RUNNING...';

    const res = await AIProviderAdapter.executePrompt(text);
    resultBox.style.display = 'block';
    resultText.textContent = res.outputText;
    resultMeta.textContent = `LATENCY: ${res.latencyMs}ms | PROMPT TOKENS: ${res.tokenCountPrompt} | OUT TOKENS: ${res.tokenCountOutput}`;

    runBtn.disabled = false;
    runBtn.textContent = '⚡ PREVIEW RUN';
  });

  saveBtn?.addEventListener('click', () => {
    const text = promptInput.value.trim();
    const explanation = explanationInput.value.trim();
    if (!text) { Router.showToast('Prompt cannot be empty', 'red'); return; }
    if (!explanation) { Router.showToast('Mandatory explanation is required!', 'red'); return; }

    store.addPromptVersion(activeCase.id, teamId, text, explanation);
    Router.showToast('Version saved to iteration history!', 'cyan');
    renderRound1Workspace();
  });

  submitBtn?.addEventListener('click', () => {
    const currentText = promptInput.value.trim();
    const currentExplanation = explanationInput.value.trim();

    let vers = store.getVersionsForCase(activeCase.id, teamId);
    const lastVer = vers.length > 0 ? vers[vers.length - 1] : null;

    // Auto-save draft version if user edited prompt or explanation since last saved version
    if (!lastVer || currentText !== lastVer.promptText || (currentExplanation && currentExplanation !== lastVer.explanation)) {
      if (!currentText) {
        Router.showToast('Prompt cannot be empty before submitting!', 'red');
        return;
      }
      if (!currentExplanation) {
        Router.showToast('Mandatory explanation is required before final submission!', 'red');
        explanationInput.focus();
        return;
      }
      store.addPromptVersion(activeCase.id, teamId, currentText, currentExplanation);
      vers = store.getVersionsForCase(activeCase.id, teamId);
    }

    if (vers.length === 0) {
      Router.showToast('Please save at least one version before submitting!', 'red');
      return;
    }
    const finalVer = vers[vers.length - 1];
    store.submitRound1(activeCase.id, teamId, finalVer.id);
    Router.showToast('Prompt Case Submitted and Locked!', 'green');
    renderRound1Workspace();
  });

  document.getElementById('btnR1Logout')?.addEventListener('click', () => {
    Router.confirmLogout();
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
