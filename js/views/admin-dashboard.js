/* ==========================================================================
   NEURA ADMIN / ORGANIZER DASHBOARD VIEW
   Hackathon Management, Team Registration, Timers, Cases & Result Gating
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';

let newTeamMembers = ['', ''];

export async function renderAdminDashboard() {
  const container = document.getElementById('page-admin-dashboard');
  if (!container) return;

  const hackathon = store.getHackathon();
  const cases = store.getRound1Cases();
  const hiddenTests = store.data.hiddenTestCases || [];
  const submissions = store.data.submissions || [];
  const evaluations = store.data.evaluations || [];
  const teams = await store.getAdminTeams();

  const timerSecs = hackathon.timerSeconds !== undefined ? hackathon.timerSeconds : 180;
  const mins = Math.floor(timerSecs / 60);
  const secs = timerSecs % 60;
  const timerDisplay = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  container.innerHTML = `
    <div class="dash-head mb-4" style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
      <div>
        <div class="eyebrow">Admin Control Center // Hackathon Director</div>
        <h1 class="heading-lg" style="margin-top:4px;">ORGANIZER DASHBOARD</h1>
        <p class="sub-text">Register participating teams, control competition flow, author broken-prompt cases, and publish official competition results.</p>
      </div>
      <button class="btn btn-sm btn-red" id="btnAdminLogout" style="padding:8px 18px; font-size:11.5px; font-weight:700; cursor:pointer;">
        ⎋ LOGOUT
      </button>
    </div>

    <!-- Admin Top Stats Row -->
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:18px;" class="mb-4">
      <div class="glass bracket-frame" style="padding:20px;">
        <span class="bl"></span><span class="br"></span>
        <div class="eyebrow" style="margin-bottom:8px;">Competition Status</div>
        <div style="font-family:var(--disp); font-size:26px; font-weight:700; color:var(--cyan);">FIX THE PROMPT</div>
        <div style="font-family:var(--mono); font-size:11px; color:var(--muted);">${hackathon.isTimerRunning ? '● RUNNING' : '⏸ PAUSED'}</div>
      </div>

      <div class="glass bracket-frame" style="padding:20px;">
        <span class="bl"></span><span class="br"></span>
        <div class="eyebrow" style="margin-bottom:8px;">Registered Teams</div>
        <div style="font-family:var(--disp); font-size:32px; font-weight:700; color:var(--green);">${teams.length}</div>
        <div style="font-family:var(--mono); font-size:11px; color:var(--muted);">Active Roster</div>
      </div>

      <div class="glass bracket-frame" style="padding:20px;">
        <span class="bl"></span><span class="br"></span>
        <div class="eyebrow" style="margin-bottom:8px;">Total Submissions</div>
        <div style="font-family:var(--disp); font-size:32px; font-weight:700; color:var(--text);">${submissions.length}</div>
        <div style="font-family:var(--mono); font-size:11px; color:var(--muted);">Across All Cases</div>
      </div>

      <div class="glass bracket-frame" style="padding:20px;">
        <span class="bl"></span><span class="br"></span>
        <div class="eyebrow" style="margin-bottom:8px;">Prompt Cases</div>
        <div style="font-family:var(--disp); font-size:32px; font-weight:700; color:var(--violet);">${cases.length} Active</div>
        <div style="font-family:var(--mono); font-size:11px; color:var(--muted);">Broken Prompt Challenges</div>
      </div>
    </div>

    <!-- Competition Control & Timer Manager Panel -->
    <div class="glass bracket-frame mb-4" style="padding:24px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center;" class="mb-3">
        <div>
          <div class="eyebrow">Competition Control & Timer Manager</div>
          <div class="heading-md" style="margin-top:4px;">Server-Authoritative Competition Timer</div>
        </div>
        <div style="display:flex; gap:10px;">
          <span class="chip chip-cyan" style="font-weight:700; padding:6px 14px; font-size:11px;">FIX THE PROMPT ARENA</span>
        </div>
      </div>

      <div style="display:flex; align-items:center; gap:20px; background:var(--panel-2); padding:16px; border-radius:6px; border:1px solid var(--line-strong); flex-wrap:wrap;">
        <div style="font-family:var(--mono); font-size:28px; font-weight:700; color:var(--cyan);" id="adminTimerReadout">
          ${timerDisplay}
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary" id="btnAdminStartTimer">▶ START TIMER</button>
          <button class="btn btn-sm" id="btnAdminPauseTimer">⏸ PAUSE TIMER</button>
          <button class="btn btn-sm" id="btnAdminResetTimer">⟳ RESET TIMER (180s)</button>
        </div>
        <div style="margin-left:auto;">
          <button class="btn btn-sm" style="border-color:var(--red); color:var(--red);" id="btnAdminResetSeed">RESET ALL SEED DATA</button>
        </div>
      </div>
    </div>

    <!-- ====================================================================
         SECTION 1: ADMIN TEAM REGISTRATION & PROVISIONING (EXPERT FEATURE)
         ==================================================================== -->
    <div class="glass bracket-frame mb-4" style="padding:26px; border-color:var(--cyan-dim);">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
        <div>
          <div class="eyebrow" style="color:var(--cyan);">Participant Onboarding & Provisioning</div>
          <h2 class="heading-md" style="margin-top:4px;">REGISTER NEW PARTICIPATING TEAM (2-MEMBER TEAMS)</h2>
          <p class="sub-text" style="margin-top:2px;">
            Provision participating teams for live competition. Each team must have exactly 2 student members with unique names.
          </p>
        </div>
        <span class="chip chip-green">✓ 2-MEMBER MODEL</span>
      </div>

      <!-- Registration Form -->
      <form id="formAdminRegisterTeam" onsubmit="return false;" style="margin-top:16px;">
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:18px;">
          <div class="field">
            <label>Team Name <span style="color:var(--red);">*</span></label>
            <input type="text" id="regTeamName" placeholder="e.g. Neural Mavericks" required autocomplete="off">
          </div>
          <div class="field">
            <label>College / Institution Name <span style="color:var(--red);">*</span></label>
            <input type="text" id="regCollege" placeholder="e.g. MMCOE Pune" required autocomplete="off">
          </div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; background:var(--panel-2); padding:18px 20px; border-radius:6px; border:1px solid var(--line); margin-bottom:20px;">
          <div class="field">
            <label>Member 1 Full Name (Team Lead) <span style="color:var(--red);">*</span></label>
            <input type="text" id="regMember1" placeholder="e.g. Alex Mercer" required autocomplete="off">
          </div>
          <div class="field">
            <label>Member 2 Full Name <span style="color:var(--red);">*</span></label>
            <input type="text" id="regMember2" placeholder="e.g. Elena Rostova" required autocomplete="off">
          </div>
        </div>

        <div style="display:flex; justify-content:flex-end;">
          <button type="submit" class="btn btn-primary" id="btnSubmitTeamRegistration" style="padding:12px 32px; box-shadow:0 0 16px rgba(71,224,255,0.3);">
            REGISTER TEAM & GENERATE CREDENTIALS →
          </button>
        </div>
      </form>
    </div>

    <!-- ====================================================================
         SECTION 2: REGISTERED TEAMS MANAGEMENT TABLE
         ==================================================================== -->
    <div class="glass bracket-frame mb-4" style="padding:24px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <div>
          <div class="eyebrow">Roster & Access Directory</div>
          <h2 class="heading-md" style="margin-top:4px;">REGISTERED PARTICIPATING TEAMS (${teams.length})</h2>
        </div>
        <button class="btn btn-sm" id="btnRefreshTeamsList" style="border-color:var(--line-strong);">⟳ REFRESH</button>
      </div>

      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-family:var(--mono); font-size:12px; text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--line-strong); color:var(--muted); font-size:10.5px; text-transform:uppercase; letter-spacing:0.08em;">
              <th style="padding:12px 14px;">Team Name</th>
              <th style="padding:12px 14px;">College / Institution</th>
              <th style="padding:12px 14px;">Members</th>
              <th style="padding:12px 14px;">Login Email</th>
              <th style="padding:12px 14px;">Invite Code</th>
              <th style="padding:12px 14px;">Status</th>
              <th style="padding:12px 14px; text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${teams.map((t, idx) => {
              const isElim = t.status === 'eliminated';
              return `
                <tr style="border-bottom:1px solid rgba(140,180,220,0.08); background:${idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'}; ${isElim ? 'opacity:0.6;' : ''}">
                  <td style="padding:14px; font-weight:700; color:var(--cyan);">${escapeHtml(t.name)}</td>
                  <td style="padding:14px; color:var(--text);">${escapeHtml(t.college || 'MMCOE Pune')}</td>
                  <td style="padding:14px; color:#cbd5e1; max-width:240px;">
                    <span title="${escapeHtml(Array.isArray(t.members) ? t.members.join(', ') : '')}">
                      ${escapeHtml(Array.isArray(t.members) ? t.members.join(', ') : '2 Members')}
                    </span>
                  </td>
                  <td style="padding:14px; color:var(--green);">${escapeHtml(t.login_email || `${t.name.toLowerCase().replace(/[^a-z0-9]/g, '.')}@neura.io`)}</td>
                  <td style="padding:14px; color:var(--text); font-weight:600;">${escapeHtml(t.invite_code || t.inviteCode || 'NR-XXXX')}</td>
                  <td style="padding:14px;">
                    <span class="chip ${isElim ? 'chip-red' : t.status === 'locked' ? 'chip-amber' : 'chip-green'}" style="font-size:10px; padding:3px 8px;">
                      ${(t.status || 'ACTIVE').toUpperCase()}
                    </span>
                  </td>
                  <td style="padding:14px; text-align:right;">
                    ${!isElim ? `
                      <button class="btn btn-sm btn-red" onclick="window.adminEliminateTeam('${t.id}', '${escapeHtml(t.name)}')" style="padding:4px 10px; font-size:10px; font-weight:700;">
                        🛑 ELIMINATE
                      </button>
                    ` : `
                      <span class="mono-text" style="color:var(--red); font-size:10px;">DISQUALIFIED</span>
                    `}
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Phase 3: Results Publication & Official Export Panel -->
    <div class="glass bracket-frame mb-4" style="padding:24px; border-color:var(--cyan-dim);">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
        <div>
          <div class="eyebrow" style="color:var(--cyan);">Competition Results Authority (FR-097, FR-101)</div>
          <div class="heading-md" style="margin-top:4px;">Official Results Gating & Data Export</div>
          <p class="sub-text" style="margin-top:2px;">Participants cannot view standings until results are published. Recomputing rankings applies deterministic 4-step tie-breaking.</p>
        </div>
        <div style="display:flex; gap:12px; align-items:center;">
          <button class="btn btn-primary" id="btnAdminPublishResults" style="box-shadow:0 0 15px rgba(71,224,255,0.3);">
            🚀 PUBLISH FINAL RESULTS
          </button>
          <button class="btn btn-sm" id="btnAdminExportCSV">📥 EXPORT CSV</button>
          <button class="btn btn-sm" id="btnAdminExportJSON">📥 EXPORT JSON</button>
        </div>
      </div>
    </div>

    <!-- Case Authoring & Management Panel -->
    <div class="glass bracket-frame mb-4" style="padding:24px;">
      <span class="bl"></span><span class="br"></span>
      <div class="eyebrow" style="margin-bottom:12px;">Broken-Prompt Case Authoring (${cases.length} Cases Active)</div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px;">
        ${cases.map(c => `
          <div class="glass-card" style="padding:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span class="mono-text" style="font-weight:700; color:var(--cyan);">${c.title}</span>
              <span class="chip chip-amber">${c.difficulty}</span>
            </div>
            <div style="font-size:12px; color:var(--muted);">${c.description}</div>
          </div>
        `).join('')}
      </div>

      <!-- Add Case Form -->
      <div style="border-top:1px solid var(--line-strong); padding-top:16px;">
        <div class="eyebrow" style="margin-bottom:8px;">+ Author New Broken-Prompt Case</div>
        <div style="display:grid; grid-template-columns: 2fr 1fr 1fr; gap:14px; margin-bottom:14px;">
          <div class="field">
            <label>Case Title</label>
            <input type="text" id="adminCaseTitle" placeholder="e.g. Case 03 — Persona Vacuum">
          </div>
          <div class="field">
            <label>Root Cause</label>
            <select id="adminCaseReason" style="background:var(--panel-2); color:var(--cyan); border:1px solid var(--line-strong); border-radius:4px; padding:8px 12px; font-family:var(--mono); font-size:12px; width:100%;">
              <option value="no_format_specified">no_format_specified</option>
              <option value="contradictory">contradictory</option>
              <option value="vague">vague</option>
              <option value="no_role_context">no_role_context</option>
              <option value="missing_edge_cases">missing_edge_cases</option>
            </select>
          </div>
          <div class="field">
            <label>Difficulty</label>
            <select id="adminCaseDifficulty" style="background:var(--panel-2); color:var(--amber); border:1px solid var(--line-strong); border-radius:4px; padding:8px 12px; font-family:var(--mono); font-size:12px; width:100%;">
              <option value="easy">Easy</option>
              <option value="medium" selected>Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <div class="field mb-3">
          <label>Original Flawed Prompt</label>
          <textarea id="adminCasePrompt" rows="2" placeholder="Deliberately broken prompt text..."></textarea>
        </div>

        <div class="field mb-3">
          <label>Observed Degraded Output</label>
          <textarea id="adminCaseOutput" rows="2" placeholder="Flawed or broken output text..."></textarea>
        </div>

        <button class="btn btn-primary" id="btnAddAdminCase">PUBLISH CASE TO COMPETITION →</button>
      </div>
    </div>
  `;

  attachAdminDashboardHandlers();
}

function renderMemberInputsHtml() {
  return newTeamMembers.map((name, idx) => `
    <div class="member-input-row" data-idx="${idx}">
      <input type="text" class="team-member-input" placeholder="Member ${idx + 1} Full Name ${idx === 0 ? '(Team Leader)' : ''}" value="${escapeHtml(name)}" autocomplete="off" required>
      ${newTeamMembers.length > 1 ? `
        <button type="button" class="btn-remove-member" title="Remove Member" data-remove-idx="${idx}">✕</button>
      ` : ''}
    </div>
  `).join('');
}

function attachAdminDashboardHandlers() {
  const hackathon = store.getHackathon();
  const cases = store.getRound1Cases();

  // Add Member Row Button
  document.getElementById('btnAddMemberRow')?.addEventListener('click', () => {
    if (newTeamMembers.length < 4) {
      syncCurrentMemberInputs();
      newTeamMembers.push('');
      refreshMemberInputsUI();
    }
  });

  // Remove Member Row Buttons
  attachRemoveMemberListeners();

  // Team Registration Form Submit Handler (2-Member Rule)
  document.getElementById('formAdminRegisterTeam')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const teamName = document.getElementById('regTeamName')?.value.trim();
    const college = document.getElementById('regCollege')?.value.trim();
    const member1 = document.getElementById('regMember1')?.value.trim();
    const member2 = document.getElementById('regMember2')?.value.trim();

    if (!teamName || !college) {
      showCustomErrorModal('MISSING REQUIRED FIELDS', 'Both Team Name and College / Institution Name are required.');
      return;
    }

    if (!member1 || !member2) {
      showCustomErrorModal('2 MEMBERS REQUIRED', 'Every team must have exactly 2 student members. Please provide both Member 1 and Member 2.');
      return;
    }

    if (member1.toLowerCase() === member2.toLowerCase()) {
      showCustomErrorModal('DUPLICATE MEMBER NAMES', 'Member 1 and Member 2 cannot have the same name. Each member must be distinct.');
      return;
    }

    const validMembers = [member1, member2];

    const submitBtn = document.getElementById('btnSubmitTeamRegistration');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'VALIDATING & GENERATING CREDENTIALS...';
    }

    const res = await store.adminRegisterTeam({
      team_name: teamName,
      college,
      members: validMembers
    });

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'REGISTER TEAM & GENERATE CREDENTIALS →';
    }

    if (res.success) {
      const registeredTeam = res.data.team;
      const creds = res.data.credentials;

      // Show Custom Animated Success Modal
      showCustomSuccessModal(registeredTeam, creds);

      // Reset form fields
      document.getElementById('regTeamName').value = '';
      document.getElementById('regCollege').value = '';
      const m1 = document.getElementById('regMember1');
      const m2 = document.getElementById('regMember2');
      if (m1) m1.value = '';
      if (m2) m2.value = '';

      // Refresh table
      renderAdminDashboard();
    } else {
      // Show Custom Animated Error Modal
      showCustomErrorModal('REGISTRATION REJECTED', res.error || 'A team with this name or member is already registered.');
    }
  });

  document.getElementById('btnAdminLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out as Hackathon Director will end your administrative session.');
  });

  document.getElementById('btnRefreshTeamsList')?.addEventListener('click', () => {
    renderAdminDashboard();
    Router.showToast('Teams directory refreshed', 'cyan');
  });

  // Timer Handlers
  document.getElementById('btnAdminStartTimer')?.addEventListener('click', () => {
    hackathon.isTimerRunning = true;
    store.saveState();
    Router.showToast('Server Timer Started', 'green');
    renderAdminDashboard();
  });

  document.getElementById('btnAdminPauseTimer')?.addEventListener('click', () => {
    hackathon.isTimerRunning = false;
    store.saveState();
    Router.showToast('Server Timer Paused', 'amber');
    renderAdminDashboard();
  });

  document.getElementById('btnAdminResetTimer')?.addEventListener('click', () => {
    hackathon.timerSeconds = 180;
    store.saveState();
    Router.showToast('Server Timer Reset to 180s', 'cyan');
    renderAdminDashboard();
  });

  document.getElementById('btnAdminResetSeed')?.addEventListener('click', () => {
    if (confirm("Reset all platform state back to original seed defaults?")) {
      store.resetToDefaults();
      Router.showToast('All seed data reset successfully', 'cyan');
      renderAdminDashboard();
    }
  });

  document.getElementById('btnAdminPublishResults')?.addEventListener('click', () => {
    store.data.hackathon.resultsPublished = true;
    store.saveState();
    Router.showToast('Competition Results Successfully Published! Leaderboard Unlocked.', 'green');
    renderAdminDashboard();
  });

  document.getElementById('btnAdminExportCSV')?.addEventListener('click', () => {
    const lb = store.calculateLeaderboard();
    let csv = "Rank,Team Name,Solved,Case Score,Total Score\n";
    lb.forEach((r, idx) => {
      csv += `${idx + 1},"${r.teamName}",${r.solved},${r.caseScore || r.r1Score},${r.totalScore}\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'neura_official_rankings.csv';
    a.click();
    URL.revokeObjectURL(url);
    Router.showToast('Rankings Exported as CSV!', 'cyan');
  });

  document.getElementById('btnAdminExportJSON')?.addEventListener('click', () => {
    const lb = store.calculateLeaderboard();
    const blob = new Blob([JSON.stringify({ hackathon: "NEURA Global 2026", rankings: lb }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'neura_official_rankings.json';
    a.click();
    URL.revokeObjectURL(url);
    Router.showToast('Rankings Exported as JSON!', 'violet');
  });

  document.getElementById('btnAddAdminCase')?.addEventListener('click', () => {
    const title = document.getElementById('adminCaseTitle').value.trim();
    const reason = document.getElementById('adminCaseReason').value;
    const difficulty = document.getElementById('adminCaseDifficulty').value;
    const prompt = document.getElementById('adminCasePrompt').value.trim();
    const output = document.getElementById('adminCaseOutput').value.trim();

    if (!title || !prompt || !output) {
      Router.showToast('All case fields are required', 'red');
      return;
    }

    cases.push({
      id: 'r1-case-' + Date.now(),
      title,
      difficulty,
      brokenReason: reason,
      originalPrompt: prompt,
      badOutput: output,
      description: `Author-defined case with broken reason '${reason}' and ${difficulty} difficulty.`
    });

    store.saveState();
    Router.showToast(`New Case Published (${reason})!`, 'green');
    renderAdminDashboard();
  });
}

function syncCurrentMemberInputs() {
  const inputs = document.querySelectorAll('.team-member-input');
  newTeamMembers = [];
  inputs.forEach(inp => newTeamMembers.push(inp.value));
}

function refreshMemberInputsUI() {
  const container = document.getElementById('memberInputsContainer');
  const badge = document.getElementById('memberCountBadge');
  if (container) {
    container.innerHTML = renderMemberInputsHtml();
    attachRemoveMemberListeners();
  }
  if (badge) {
    badge.textContent = newTeamMembers.length;
  }
}

function attachRemoveMemberListeners() {
  document.querySelectorAll('.btn-remove-member').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(e.currentTarget.getAttribute('data-remove-idx'), 10);
      syncCurrentMemberInputs();
      if (newTeamMembers.length > 1) {
        newTeamMembers.splice(idx, 1);
        refreshMemberInputsUI();
      }
    });
  });
}

/* ==========================================================================
   CUSTOM MODALS (SUCCESS & ERROR POPUPS)
   ========================================================================== */

function showCustomSuccessModal(team, creds) {
  const container = document.getElementById('customModalContainer');
  if (!container) return;

  const membersList = Array.isArray(team.members) ? team.members : [];

  container.innerHTML = `
    <div class="neura-modal-overlay" id="successRegModalOverlay">
      <div class="neura-modal glass bracket-frame modal-glow-green" style="max-width:540px; width:92%; padding:30px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <div class="chip chip-green">✓ TEAM SUCCESSFULLY REGISTERED</div>
          <button class="btn-modal-close" id="btnCloseSuccessModal" style="background:none; border:none; color:var(--muted); font-size:22px; cursor:pointer; line-height:1;">&times;</button>
        </div>

        <h3 class="heading-md" style="margin-bottom:6px; color:#ffffff;">PROVISIONED TEAM CREDENTIALS</h3>
        <p class="sub-text" style="font-size:12px; margin-bottom:14px;">The participating team is registered and locked in the hackathon directory.</p>

        <div class="cred-display-box">
          <div class="cred-row">
            <span class="cred-label">Team Name</span>
            <span class="cred-val">${escapeHtml(team.name)}</span>
          </div>
          <div class="cred-row">
            <span class="cred-label">College / Institution</span>
            <span class="cred-val" style="color:var(--text);">${escapeHtml(team.college || 'N/A')}</span>
          </div>
          <div class="cred-row">
            <span class="cred-label">Roster Members</span>
            <span class="cred-val" style="color:var(--text); font-size:11.5px;">${escapeHtml(membersList.join(', '))}</span>
          </div>
          <div class="cred-row">
            <span class="cred-label">Team Login Email</span>
            <span class="cred-val">${escapeHtml(creds.email)}</span>
          </div>
          <div class="cred-row">
            <span class="cred-label">Temporary Password</span>
            <span class="cred-val password-val">${escapeHtml(creds.password)}</span>
          </div>
        </div>

        <div style="display:flex; gap:12px; margin-top:18px;">
          <button class="btn btn-primary" id="btnCopyTeamCreds" style="flex:1;">
            📋 COPY CREDENTIALS
          </button>
          <button class="btn" id="btnCloseSuccessModalBtn" style="border-color:var(--line-strong);">
            CLOSE
          </button>
        </div>
        <div id="copySuccessFeedback" class="mono-text" style="color:var(--green); font-size:11px; text-align:center; margin-top:8px; display:none;">
          ✓ CREDENTIALS COPIED TO CLIPBOARD
        </div>
      </div>
    </div>
  `;

  const overlay = document.getElementById('successRegModalOverlay');
  const close = () => { overlay?.remove(); };

  document.getElementById('btnCloseSuccessModal')?.addEventListener('click', close);
  document.getElementById('btnCloseSuccessModalBtn')?.addEventListener('click', close);

  document.getElementById('btnCopyTeamCreds')?.addEventListener('click', () => {
    const textToCopy = `NEURA TEAM LOGIN\nTeam: ${team.name}\nCollege: ${team.college || 'N/A'}\nEmail: ${creds.email}\nPassword: ${creds.password}`;
    navigator.clipboard.writeText(textToCopy).then(() => {
      const fb = document.getElementById('copySuccessFeedback');
      if (fb) fb.style.display = 'block';
      Router.showToast('Credentials copied to clipboard!', 'green');
    }).catch(() => {
      Router.showToast('Could not auto-copy, please select and copy manually.', 'amber');
    });
  });
}

function showCustomErrorModal(title, message) {
  const container = document.getElementById('customModalContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="neura-modal-overlay" id="errorRegModalOverlay">
      <div class="neura-modal glass bracket-frame modal-glow-red" style="max-width:480px; width:92%; padding:30px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <div class="chip chip-red">⚠ REGISTRATION FAILED</div>
          <button class="btn-modal-close" id="btnCloseErrorModal" style="background:none; border:none; color:var(--muted); font-size:22px; cursor:pointer; line-height:1;">&times;</button>
        </div>
        <h3 class="heading-md" style="margin-bottom:8px; color:var(--red); font-size:18px;">${escapeHtml(title)}</h3>
        <p class="sub-text" style="font-size:13px; margin-bottom:20px; color:#cbd5e1; line-height:1.5;">${escapeHtml(message)}</p>

        <button class="btn btn-primary" id="btnCloseErrorModalBtn" style="width:100%; border-color:var(--red);">
          CLOSE & TRY AGAIN
        </button>
      </div>
    </div>
  `;

  const overlay = document.getElementById('errorRegModalOverlay');
  const close = () => { overlay?.remove(); };

  document.getElementById('btnCloseErrorModal')?.addEventListener('click', close);
  document.getElementById('btnCloseErrorModalBtn')?.addEventListener('click', close);
}

function showAdminEliminateModal(teamId, teamName) {
  const container = document.getElementById('customModalContainer') || document.body;
  const modalDiv = document.createElement('div');
  modalDiv.className = 'neura-modal-overlay';
  modalDiv.style.display = 'flex';
  modalDiv.innerHTML = `
    <div class="neura-modal glass bracket-frame" style="max-width:500px; width:92%; padding:28px; border-color:rgba(255,0,85,0.6);">
      <span class="bl" style="border-color:var(--red);"></span><span class="br" style="border-color:var(--red);"></span>
      <div class="chip chip-red" style="margin-bottom:12px; font-weight:800;">ADMINISTRATIVE SANCTION</div>
      <h3 class="heading-md" style="margin-bottom:8px; color:var(--red);">ELIMINATE TEAM: ${escapeHtml(teamName)}</h3>
      <p class="sub-text" style="font-size:12.5px; line-height:1.5; margin-bottom:16px;">
        Eliminating this team will permanently disqualify them, revoke live challenge access, and remove them from official leaderboard podium eligibility.
      </p>

      <div class="field" style="margin-bottom:14px;">
        <label>Elimination Reason / Audit Finding <span style="color:var(--red);">*</span></label>
        <input type="text" id="adminElimReasonInput" value="Disqualified by Competition Administration" style="font-size:12px;">
      </div>

      <div style="display:flex; justify-content:flex-end; gap:12px;">
        <button class="btn btn-sm" id="btnCancelAdminElim" style="padding:6px 14px;">CANCEL</button>
        <button class="btn btn-sm btn-red" id="btnConfirmAdminElim" style="padding:6px 18px; font-weight:700;">CONFIRM ELIMINATION 🛑</button>
      </div>
    </div>
  `;
  container.appendChild(modalDiv);

  modalDiv.querySelector('#btnCancelAdminElim')?.addEventListener('click', () => { modalDiv.remove(); });
  modalDiv.querySelector('#btnConfirmAdminElim')?.addEventListener('click', async () => {
    const reason = modalDiv.querySelector('#adminElimReasonInput')?.value.trim() || 'Disqualified by Administration';
    const btn = modalDiv.querySelector('#btnConfirmAdminElim');
    btn.disabled = true;
    btn.textContent = 'TRANSMITTING...';

    const res = await store.eliminateTeam(teamId, reason);
    modalDiv.remove();
    if (res.success) {
      Router.showToast(`Team '${teamName}' eliminated.`, 'red');
      await renderAdminDashboard();
    } else {
      Router.showToast(res.error || 'Elimination failed', 'red');
    }
  });
}
window.adminEliminateTeam = showAdminEliminateModal;

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
