/* ==========================================================================
   NEURA ADMIN / ORGANIZER DASHBOARD VIEW
   Hackathon Management, Team Registration, Timers, Cases & Result Gating
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';

let newTeamMembers = ['', ''];
let adminPollInterval = null;

export async function renderAdminDashboard() {
  const container = document.getElementById('page-admin-dashboard');
  if (!container) return;

  if (adminPollInterval) clearInterval(adminPollInterval);
  adminPollInterval = setInterval(() => {
    if (document.getElementById('page-admin-dashboard')?.classList.contains('active')) {
      renderAdminDashboard();
    } else {
      clearInterval(adminPollInterval);
    }
  }, 10000);

  const hackathon = store.getHackathon();
  const cases = store.getRound1Cases();
  const hiddenTests = store.data.hiddenTestCases || [];
  const submissions = store.data.submissions || [];
  const evaluations = store.data.evaluations || [];
  const teams = await store.getAdminTeams();
  const regSummary = await store.getRegistrationStatusSummary();
  const registrations = await store.getAdminRegistrations();
  const arenaRes = await store.getArenaJudgeOverview();
  const promptBank = await store.getPromptBank();
  const arenaStatus = arenaRes?.success && arenaRes.status ? arenaRes.status : 'waiting';
  const isResultsReleased = arenaRes?.success && arenaRes.is_results_released ? arenaRes.is_results_released : false;
  
  const statusBadge = arenaStatus === 'live' ? '<span class="chip chip-cyan" style="animation:pulse-glow 1.5s infinite;">● LIVE ARENA</span>'
                    : arenaStatus === 'completed' ? '<span class="chip chip-violet">■ ARENA COMPLETED</span>'
                    : arenaStatus === 'results_available' || isResultsReleased ? '<span class="chip chip-green">✓ RESULTS RELEASED</span>'
                    : '<span class="chip chip-amber">⏳ WAITING FOR START</span>';


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

    <!-- Evaluation Link Section -->
    <div class="glass bracket-frame mb-4" style="padding:24px; border-color:var(--violet);">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <h2 class="heading-md" style="color:var(--violet); margin-bottom:4px;">⚖️ EVALUATION & SCORING (JUDGE DASHBOARD)</h2>
          <p class="sub-text">Assign marks and verify the scores generated by the score engine. <strong>All grading happens in the Judge Dashboard.</strong></p>
        </div>
        <button class="btn btn-primary" onclick="document.querySelector('[data-page=judge-dashboard]').click()" style="background:var(--violet); box-shadow:0 0 15px rgba(138,43,226,0.4);">
          OPEN JUDGE DASHBOARD →
        </button>
      </div>
    </div>

    <!-- Competition Control & Timer Manager Panel -->
    <details class="glass bracket-frame mb-4" open style="padding:0; overflow:hidden;">
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan); display:flex; justify-content:space-between; align-items:center;">
        <span> 1. COMPETITION CONTROL & ARENA STATUS</span>
        <span>${statusBadge}</span>
      </summary>
      <div style="padding:24px;">
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
          <button class="btn btn-sm btn-primary" id="btnAdminStartTimer"> START TIMER</button>
          <button class="btn btn-sm" id="btnAdminPauseTimer">⏸ PAUSE TIMER</button>
          <button class="btn btn-sm" id="btnAdminResetTimer">⟳ RESET TIMER (180s)</button>
        </div>
        <div style="margin-left:auto;">
          <button class="btn btn-sm" style="border-color:var(--red); color:var(--red);" id="btnAdminResetSeed">RESET ALL SEED DATA</button>
        </div>
      </div>
      
      <div style="display:flex; align-items:center; gap:20px; background:var(--panel-2); padding:16px; border-radius:6px; border:1px solid var(--line-strong); flex-wrap:wrap; margin-top: 10px;">
        <div><span class="eyebrow">NEW ARENA CONTROLS</span></div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary" id="btnAdminStartArena" style="background:var(--violet);"> START NEW ARENA</button>
          <button class="btn btn-sm" id="btnAdminEndArena">🛑 END ARENA</button>
          <button class="btn btn-sm" id="btnAdminReleaseArenaResults" style="border-color:var(--green); color:var(--green);">📊 RELEASE RESULTS</button>
        </div>
      </div>
    </div>

      </div>
    </details>

    <!-- ====================================================================
         SECTION 0: LIVE GOOGLE FORM REGISTRATION & DATABASE SYNC CONTROL
         ==================================================================== -->
    <details class="glass bracket-frame mb-4" style="padding:0; overflow:hidden; border-color:var(--cyan-dim);">
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan);">
         2. GOOGLE FORM / SHEETS LIVE REGISTRATION CONTROL
      </summary>
      <div style="padding:26px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
        <div>
          <div class="eyebrow" style="color:var(--cyan);">Source of Truth // Participant Authentication</div>
          <h2 class="heading-md" style="margin-top:4px;">GOOGLE FORM / SHEETS LIVE REGISTRATION CONTROL</h2>
          <p class="sub-text" style="margin-top:2px;">
            Synchronize participant registrations from Google Sheets or CSV/XLSX imports into NEURA database.
          </p>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="chip ${regSummary.google_sheets_connected ? 'chip-green' : 'chip-amber'}">
            ● GOOGLE SHEETS: ${regSummary.google_sheets_connected ? 'CONNECTED' : 'NOT CONFIGURED'}
          </span>
          ${regSummary.last_synced_at ? `<span class="mono-text" style="font-size:11px; color:var(--muted);">Last Sync: ${new Date(regSummary.last_synced_at).toLocaleTimeString()}</span>` : ''}
        </div>
      </div>

      <!-- Registration Stats Counter Grid -->
      <div style="display:grid; grid-template-columns: repeat(6, 1fr); gap:12px; margin-bottom:20px;">
        <div class="glass-card" style="padding:12px; text-align:center;">
          <div class="eyebrow" style="font-size:9.5px;">TOTAL RECORDS</div>
          <div style="font-family:var(--disp); font-size:22px; font-weight:700; color:var(--cyan); margin-top:2px;">${regSummary.total_registrations || 0}</div>
        </div>
        <div class="glass-card" style="padding:12px; text-align:center;">
          <div class="eyebrow" style="font-size:9.5px;">VERIFIED</div>
          <div style="font-family:var(--disp); font-size:22px; font-weight:700; color:var(--green); margin-top:2px;">${regSummary.verified || 0}</div>
        </div>
        <div class="glass-card" style="padding:12px; text-align:center;">
          <div class="eyebrow" style="font-size:9.5px;">PENDING</div>
          <div style="font-family:var(--disp); font-size:22px; font-weight:700; color:var(--amber); margin-top:2px;">${regSummary.pending || 0}</div>
        </div>
        <div class="glass-card" style="padding:12px; text-align:center;">
          <div class="eyebrow" style="font-size:9.5px;">REJECTED</div>
          <div style="font-family:var(--disp); font-size:22px; font-weight:700; color:var(--red); margin-top:2px;">${regSummary.rejected || 0}</div>
        </div>
        <div class="glass-card" style="padding:12px; text-align:center;">
          <div class="eyebrow" style="font-size:9.5px;">ACTIVE ACCOUNTS</div>
          <div style="font-family:var(--disp); font-size:22px; font-weight:700; color:var(--cyan); margin-top:2px;">${regSummary.active_accounts || 0}</div>
        </div>
        <div class="glass-card" style="padding:12px; text-align:center;">
          <div class="eyebrow" style="font-size:9.5px;">UNPROVISIONED</div>
          <div style="font-family:var(--disp); font-size:22px; font-weight:700; color:var(--violet); margin-top:2px;">${regSummary.unprovisioned || 0}</div>
        </div>
      </div>

      <!-- Actions Toolbar -->
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:20px; background:var(--panel-2); padding:14px 18px; border-radius:6px; border:1px solid var(--line);">
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary" id="btnSyncGoogleSheets" ${!regSummary.google_sheets_connected ? 'disabled title="Configure Google Sheets API credentials in backend .env"' : ''}>
            ⚡ SYNC GOOGLE SHEETS NOW
          </button>
          <button class="btn btn-sm" id="btnTriggerCsvImport" style="border-color:var(--cyan); color:var(--cyan);">
            📁 IMPORT CSV / XLSX FILE
          </button>
          <input type="file" id="registrationFileInput" accept=".csv,.xlsx,.xls" style="display:none;">
          <button class="btn btn-sm" id="btnProvisionAllVerified" style="border-color:var(--green); color:var(--green);">
            ⚡ PROVISION ALL VERIFIED (${regSummary.unprovisioned || 0})
          </button>
        </div>
        <div>
          <button class="btn btn-sm" id="btnExportRegistrationsCsv" style="border-color:var(--line-strong);">
            📥 EXPORT REGISTRATIONS CSV
          </button>
        </div>
      </div>

      <!-- Registration Data Directory Table -->
      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-family:var(--mono); font-size:11.5px; text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--line-strong); color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:0.08em;">
              <th style="padding:10px 12px;">Reg ID / Ext ID</th>
              <th style="padding:10px 12px;">Team Name</th>
              <th style="padding:10px 12px;">Participant Name</th>
              <th style="padding:10px 12px;">Email</th>
              <th style="padding:10px 12px;">College</th>
              <th style="padding:10px 12px;">Status</th>
              <th style="padding:10px 12px;">Account Status</th>
              <th style="padding:10px 12px; text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${registrations.length === 0 ? `
              <tr>
                <td colspan="8" style="padding:24px; text-align:center; color:var(--muted);">
                  No registration records found. Click <strong>SYNC GOOGLE SHEETS NOW</strong> or <strong>IMPORT CSV / XLSX FILE</strong> to import participant responses.
                </td>
              </tr>
            ` : registrations.map((r, idx) => {
              const isVer = r.registration_status === 'VERIFIED';
              const isRej = r.registration_status === 'REJECTED';
              const isDis = r.registration_status === 'DISABLED';
              const isAct = r.account_status === 'ACTIVE';

              return `
                <tr style="border-bottom:1px solid rgba(140,180,220,0.08); background:${idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'}">
                  <td style="padding:10px 12px; font-weight:600; color:var(--text);">${escapeHtml(r.external_registration_id || r.id.substring(0, 8))}</td>
                  <td style="padding:10px 12px; font-weight:700; color:var(--cyan);">${escapeHtml(r.team_name)}</td>
                  <td style="padding:10px 12px; color:var(--text);">${escapeHtml(r.participant_name)}</td>
                  <td style="padding:10px 12px; color:var(--green);">${escapeHtml(r.email)}</td>
                  <td style="padding:10px 12px; color:var(--muted);">${escapeHtml(r.college || 'N/A')}</td>
                  <td style="padding:10px 12px;">
                    <span class="chip ${isVer ? 'chip-green' : isRej ? 'chip-red' : isDis ? 'chip-red' : 'chip-amber'}" style="font-size:9.5px; padding:2px 6px;">
                      ${(r.registration_status || 'PENDING').toUpperCase()}
                    </span>
                  </td>
                  <td style="padding:10px 12px;">
                    <span class="chip ${isAct ? 'chip-cyan' : 'chip-amber'}" style="font-size:9.5px; padding:2px 6px;">
                      ${(r.account_status || 'NOT_PROVISIONED').toUpperCase()}
                    </span>
                  </td>
                  <td style="padding:10px 12px; text-align:right;">
                    <div style="display:flex; justify-content:flex-end; gap:6px; flex-wrap:wrap;">
                      ${!isVer && !isRej ? `
                        <button class="btn btn-sm btn-primary" onclick="window.verifyRegAction('${r.id}')" style="padding:3px 8px; font-size:9.5px;">✓ VERIFY</button>
                        <button class="btn btn-sm btn-red" onclick="window.rejectRegAction('${r.id}')" style="padding:3px 8px; font-size:9.5px;">✕ REJECT</button>
                      ` : ''}
                      ${isVer && !isAct ? `
                        <button class="btn btn-sm" onclick="window.provisionRegAction('${r.id}')" style="padding:3px 8px; font-size:9.5px; border-color:var(--green); color:var(--green);">⚡ PROVISION</button>
                      ` : ''}
                      ${isAct ? `
                        <button class="btn btn-sm" onclick="window.resetRegCredsAction('${r.id}')" style="padding:3px 8px; font-size:9.5px; border-color:var(--cyan); color:var(--cyan);">🔑 RESET PASS</button>
                      ` : ''}
                      ${!isDis ? `
                        <button class="btn btn-sm btn-red" onclick="window.disableRegAction('${r.id}')" style="padding:3px 8px; font-size:9.5px;">🛑 DISABLE</button>
                      ` : ''}
                    </div>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>

      </div>
    </details>

    <!-- ====================================================================
         SECTION 1A: PROMPT BANK MANAGER
         ==================================================================== -->
    <details class="glass bracket-frame mb-4" style="padding:0; overflow:hidden; border-color:var(--cyan-dim);" open>
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan);">
         3. PROMPT BANK MANAGER (CONTENT EDITOR)
      </summary>
      <div style="padding:26px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
          <div>
            <div class="eyebrow" style="color:var(--cyan);">Arena Content Editor</div>
            <h2 class="heading-md" style="margin-top:4px;">PROMPT BANK ITEMS</h2>
            <p class="sub-text" style="margin-top:2px;">
              Manage the pool of broken prompts that will be dynamically assigned to participants.
            </p>
          </div>
          <div>
            <button class="btn btn-sm btn-primary" id="btnAdminCreatePromptBankItem" style="background:var(--cyan); color:#000;">
              + NEW PROMPT CASE
            </button>
          </div>
        </div>

        <div style="overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse; font-family:var(--mono); font-size:11.5px; text-align:left;">
            <thead>
              <tr style="border-bottom:1px solid var(--line-strong); color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:0.08em;">
                <th style="padding:10px 12px;">Code</th>
                <th style="padding:10px 12px;">Title</th>
                <th style="padding:10px 12px;">Category</th>
                <th style="padding:10px 12px;">Difficulty</th>
                <th style="padding:10px 12px; text-align:right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${promptBank.length === 0 ? `
                <tr>
                  <td colspan="5" style="padding:24px; text-align:center; color:var(--muted);">
                    No prompt bank items found. Click <strong>+ NEW PROMPT CASE</strong> to create one.
                  </td>
                </tr>
              ` : promptBank.map(p => `
                <tr style="border-bottom:1px solid var(--line);">
                  <td style="padding:12px; color:var(--cyan); font-weight:700;">${p.code}</td>
                  <td style="padding:12px;">${p.title}</td>
                  <td style="padding:12px; color:var(--violet);">${p.category}</td>
                  <td style="padding:12px; color:${p.difficulty === 'hard' ? 'var(--red)' : p.difficulty === 'medium' ? 'var(--amber)' : 'var(--green)'};">${p.difficulty.toUpperCase()}</td>
                  <td style="padding:12px; text-align:right;">
                    <button class="btn btn-sm btn-edit-prompt" data-id="${p.id}" style="padding:4px 8px; font-size:10px; border-color:var(--line-strong);">EDIT</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <!-- ====================================================================
         SECTION 1: ADMIN TEAM REGISTRATION & PROVISIONING (EXPERT FEATURE)
         ==================================================================== -->
    <details class="glass bracket-frame mb-4" style="padding:0; overflow:hidden; border-color:var(--cyan-dim);">
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan);">
         3. REGISTER NEW PARTICIPATING TEAM (MANUAL)
      </summary>
      <div style="padding:26px;">
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

      </div>
    </details>

    <!-- ====================================================================
         SECTION 2: REGISTERED TEAMS MANAGEMENT TABLE
         ==================================================================== -->
    <details class="glass bracket-frame mb-4" style="padding:0; overflow:hidden;">
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan);">
         4. REGISTERED PARTICIPATING TEAMS ROSTER
      </summary>
      <div style="padding:24px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <div>
          <div class="eyebrow">Roster & Access Directory</div>
          <h2 class="heading-md" style="margin-top:4px;">REGISTERED PARTICIPATING TEAMS (${teams.length})</h2>
        </div>
        <button class="btn btn-sm" id="btnRefreshTeamsList" style="border-color:var(--line-strong);">⟳ REFRESH</button>
      </div>

      <div class="table-responsive">
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
            ${teams.length === 0 ? `
              <tr>
                <td colspan="7" style="padding:0;">
                  <div class="empty-state-card">
                    <div class="empty-state-icon">👥</div>
                    <div class="heading-md" style="font-size:15px; margin-bottom:4px;">No Registered Teams Found</div>
                    <p class="sub-text" style="font-size:12px;">Register a team above or import records from Google Form sync.</p>
                  </div>
                </td>
              </tr>
            ` : teams.map((t, idx) => {
              const isElim = t.status === 'eliminated';
              return `
                <tr style="border-bottom:1px solid rgba(140,180,220,0.08); background:${idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'}; ${isElim ? 'opacity:0.6;' : ''}">
                  <td style="padding:14px; font-weight:700; color:var(--cyan);" class="truncate-text" style="max-width:180px;">${escapeHtml(t.name)}</td>
                  <td style="padding:14px; color:var(--text);" class="truncate-text" style="max-width:180px;">${escapeHtml(t.college || 'MMCOE Pune')}</td>
                  <td style="padding:14px; color:#cbd5e1; max-width:240px;" class="truncate-text">
                    <span title="${escapeHtml(Array.isArray(t.members) ? t.members.join(', ') : '')}">
                      ${escapeHtml(Array.isArray(t.members) ? t.members.join(', ') : '2 Members')}
                    </span>
                  </td>
                  <td style="padding:14px; color:var(--green);" class="truncate-text" style="max-width:200px;">${escapeHtml(t.login_email || `${t.name.toLowerCase().replace(/[^a-z0-9]/g, '.')}@neura.io`)}</td>
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

      </div>
    </details>

    <!-- Phase 3: Results Publication & Official Export Panel -->
    <details class="glass bracket-frame mb-4" style="padding:0; overflow:hidden; border-color:var(--cyan-dim);">
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan);">
         5. OFFICIAL RESULTS GATING & DATA EXPORT
      </summary>
      <div style="padding:24px;">
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

      </div>
    </details>

    <!-- Case Authoring & Management Panel -->
    <details class="glass bracket-frame mb-4" style="padding:0; overflow:hidden;">
      <summary style="padding:16px 24px; cursor:pointer; font-weight:700; background:rgba(0,0,0,0.2); border-bottom:1px solid var(--line-strong); outline:none; user-select:none; color:var(--cyan);">
         6. BROKEN-PROMPT CASE AUTHORING & MANAGEMENT
      </summary>
      <div style="padding:24px;">
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
      </div>
    </details>
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

  // Section 0: Registration Sync & File Import Event Handlers
  document.getElementById('btnSyncGoogleSheets')?.addEventListener('click', async () => {
    Router.showToast('Synchronizing live responses from Google Sheets...', 'cyan');
    const res = await store.syncGoogleSheetsRegistrations();
    if (res.success) {
      Router.showToast(`Sync complete! Total: ${res.total_rows}, Created: ${res.created}, Updated: ${res.updated}`, 'green');
      await renderAdminDashboard();
    } else {
      Router.showToast(res.error || 'Google Sheets sync failed', 'red');
    }
  });

  const fileInput = document.getElementById('registrationFileInput');
  document.getElementById('btnTriggerCsvImport')?.addEventListener('click', () => {
    fileInput?.click();
  });

  fileInput?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    Router.showToast(`Processing file '${file.name}'...`, 'cyan');
    const res = await store.importRegistrationsFile(file);
    if (res.success) {
      Router.showToast(`Import complete! Total: ${res.total_rows}, Created: ${res.created}, Updated: ${res.updated}`, 'green');
      await renderAdminDashboard();
    } else {
      Router.showToast(res.error || 'Import failed', 'red');
    }
  });

  document.getElementById('btnProvisionAllVerified')?.addEventListener('click', async () => {
    Router.showToast('Provisioning all verified registrations...', 'cyan');
    const res = await store.provisionAllVerifiedRegistrations();
    if (res.success) {
      Router.showToast(`Provisioned ${res.total_provisioned} accounts!`, 'green');
      await renderAdminDashboard();
    } else {
      Router.showToast(res.error || 'Bulk provisioning failed', 'red');
    }
  });

  document.getElementById('btnExportRegistrationsCsv')?.addEventListener('click', async () => {
    Router.showToast('Exporting registrations CSV...', 'cyan');
    await store.downloadRegistrationsCsv();
  });

  // Prompt Bank Handlers
  document.getElementById('btnAdminCreatePromptBankItem')?.addEventListener('click', () => {
    showPromptBankModal();
  });

  document.querySelectorAll('.btn-edit-prompt').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = e.target.getAttribute('data-id');
      const promptBank = await store.getPromptBank();
      const promptItem = promptBank.find(p => p.id === id);
      if (promptItem) {
        showPromptBankModal(promptItem);
      }
    });
  });

  document.getElementById('btnAdminLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out as Hackathon Director will end your administrative session.');
  });
  
  document.getElementById('btnAdminStartArena')?.addEventListener('click', async () => {
    const res = await store.startArena();
    if (res.success) {
        Router.showToast('New Arena Started!', 'green');
        renderAdminDashboard();
    }
    else Router.showToast(res.error || 'Failed to start arena', 'red');
  });

  document.getElementById('btnAdminEndArena')?.addEventListener('click', async () => {
    const res = await store.endArena();
    if (res.success) {
        Router.showToast('New Arena Ended!', 'amber');
        renderAdminDashboard();
    }
    else Router.showToast(res.error || 'Failed to end arena', 'red');
  });

  document.getElementById('btnAdminReleaseArenaResults')?.addEventListener('click', async () => {
    const res = await store.releaseArenaResults();
    if (res.success) {
        Router.showToast('Arena Results Released!', 'green');
        renderAdminDashboard();
    }
    else Router.showToast(res.error || 'Failed to release results', 'red');
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

// Registration Action Handlers
window.verifyRegAction = async (regId) => {
  const res = await store.verifyRegistration(regId);
  if (res.success) {
    Router.showToast('Registration verified.', 'green');
    renderAdminDashboard();
  } else {
    Router.showToast(res.error || 'Verification failed', 'red');
  }
};

window.rejectRegAction = async (regId) => {
  const res = await store.rejectRegistration(regId);
  if (res.success) {
    Router.showToast('Registration rejected.', 'red');
    renderAdminDashboard();
  } else {
    Router.showToast(res.error || 'Rejection failed', 'red');
  }
};

function attachAdminArenaListeners(container) {
  container.querySelector('#btnAdminResetTimer')?.addEventListener('click', async () => {
    const res = await store.resetTimer(hackathon.timerSeconds || 180);
    if (res.success) { Router.showToast('Timer Reset', 'cyan'); renderAdminDashboard(); }
    else Router.showToast(res.error || 'Failed to reset', 'red');
  });

  container.querySelector('#btnAdminStartArena')?.addEventListener('click', async () => {
    const res = await store.startArena();
    if (res.success) {
        Router.showToast('New Arena Started!', 'green');
        renderAdminDashboard();
    }
    else Router.showToast(res.error || 'Failed to start arena', 'red');
  });
  
  container.querySelector('#btnAdminEndArena')?.addEventListener('click', async () => {
    const res = await store.endArena();
    if (res.success) {
        Router.showToast('New Arena Ended!', 'amber');
        renderAdminDashboard();
    }
    else Router.showToast(res.error || 'Failed to end arena', 'red');
  });
  
  container.querySelector('#btnAdminReleaseArenaResults')?.addEventListener('click', async () => {
    const res = await store.releaseArenaResults();
    if (res.success) {
        Router.showToast('Arena Results Released!', 'green');
        renderAdminDashboard();
    }
    else Router.showToast(res.error || 'Failed to release results', 'red');
  });
}

window.disableRegAction = async (regId) => {
  const res = await store.disableRegistration(regId);
  if (res.success) {
    Router.showToast('Registration disabled.', 'red');
    renderAdminDashboard();
  } else {
    Router.showToast(res.error || 'Disabling failed', 'red');
  }
};

window.provisionRegAction = async (regId) => {
  const res = await store.provisionRegistrationAccount(regId);
  if (res.success) {
    showAdminRegistrationCredsModal(res);
    renderAdminDashboard();
  } else {
    Router.showToast(res.error || 'Provisioning failed', 'red');
  }
};

window.resetRegCredsAction = async (regId) => {
  const res = await store.resetRegistrationCredentials(regId);
  if (res.success) {
    showAdminRegistrationCredsModal(res);
    renderAdminDashboard();
  } else {
    Router.showToast(res.error || 'Credential reset failed', 'red');
  }
};

function showAdminRegistrationCredsModal(res) {
  const container = document.getElementById('customModalContainer') || document.body;
  const modalDiv = document.createElement('div');
  modalDiv.className = 'neura-modal-overlay';
  modalDiv.style.display = 'flex';

  const email = res.credentials?.email || res.email;
  const pass = res.credentials?.password || '••••••••';

  modalDiv.innerHTML = `
    <div class="neura-modal glass bracket-frame" style="max-width:520px; width:92%; padding:28px; border-color:var(--cyan-dim);">
      <span class="bl"></span><span class="br"></span>
      <div class="chip chip-green" style="margin-bottom:12px; font-weight:800;">✓ ACCOUNT PROVISIONED</div>
      <h3 class="heading-md" style="margin-bottom:8px; color:var(--cyan);">CREDENTIALS FOR ${escapeHtml(res.participant_name || res.team_name)}</h3>
      <p class="sub-text" style="font-size:12.5px; line-height:1.5; margin-bottom:16px;">
        Account is provisioned and linked to team <strong>${escapeHtml(res.team_name)}</strong>.
      </p>

      <div style="background:var(--panel-2); padding:14px; border-radius:6px; border:1px solid var(--line); font-family:var(--mono); font-size:12px; margin-bottom:18px;">
        <div style="margin-bottom:8px;"><strong style="color:var(--muted);">Login Email:</strong> <span style="color:var(--green);">${escapeHtml(email)}</span></div>
        <div><strong style="color:var(--muted);">Temporary Passcode:</strong> <span style="color:var(--cyan); font-weight:700;">${escapeHtml(pass)}</span></div>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:12px;">
        <button class="btn btn-sm btn-primary" id="btnCopyCredsModal">📋 COPY CREDENTIALS</button>
        <button class="btn btn-sm" id="btnCloseCredsModal">CLOSE</button>
      </div>
    </div>
  `;
  container.appendChild(modalDiv);

  modalDiv.querySelector('#btnCloseCredsModal')?.addEventListener('click', () => { modalDiv.remove(); });
  modalDiv.querySelector('#btnCopyCredsModal')?.addEventListener('click', () => {
    navigator.clipboard.writeText(`NEURA CREDENTIALS\nName: ${res.participant_name}\nTeam: ${res.team_name}\nEmail: ${email}\nPassword: ${pass}`).then(() => {
      Router.showToast('Credentials copied to clipboard!', 'green');
      modalDiv.remove();
    });
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

window.showPromptBankModal = function(promptItem = null) {
  const container = document.getElementById('customModalContainer') || document.body;
  const modalDiv = document.createElement('div');
  modalDiv.className = 'neura-modal-overlay';
  modalDiv.style.display = 'flex';
  
  const isEdit = !!promptItem;
  
  modalDiv.innerHTML = `
    <div class="neura-modal glass bracket-frame" style="max-width:600px; width:92%; padding:28px; border-color:var(--cyan-dim); max-height: 90vh; overflow-y: auto;">
      <span class="bl"></span><span class="br"></span>
      <h3 class="heading-md" style="margin-bottom:16px; color:var(--cyan);">${isEdit ? 'EDIT PROMPT CASE' : 'NEW PROMPT CASE'}</h3>
      
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:14px; margin-bottom:14px;">
        <div class="field">
          <label>Code (e.g. P001) <span style="color:var(--red);">*</span></label>
          <input type="text" id="pbCode" value="${isEdit ? escapeHtml(promptItem.code) : ''}" required>
        </div>
        <div class="field">
          <label>Category <span style="color:var(--red);">*</span></label>
          <input type="text" id="pbCategory" value="${isEdit ? escapeHtml(promptItem.category) : 'general'}" required>
        </div>
      </div>
      
      <div class="field mb-3">
        <label>Title <span style="color:var(--red);">*</span></label>
        <input type="text" id="pbTitle" value="${isEdit ? escapeHtml(promptItem.title) : ''}" required>
      </div>
      
      <div class="field mb-3">
        <label>Difficulty</label>
        <select id="pbDifficulty" style="background:var(--panel-2); color:var(--text); border:1px solid var(--line-strong); border-radius:4px; padding:8px 12px; font-family:var(--mono); font-size:12px; width:100%;">
          <option value="easy" ${isEdit && promptItem.difficulty === 'easy' ? 'selected' : ''}>Easy</option>
          <option value="medium" ${!isEdit || promptItem.difficulty === 'medium' ? 'selected' : ''}>Medium</option>
          <option value="hard" ${isEdit && promptItem.difficulty === 'hard' ? 'selected' : ''}>Hard</option>
        </select>
      </div>

      <div class="field mb-3">
        <label>Original Broken Prompt <span style="color:var(--red);">*</span></label>
        <textarea id="pbOriginalPrompt" rows="3" required>${isEdit ? escapeHtml(promptItem.original_bad_prompt) : ''}</textarea>
      </div>

      <div class="field mb-3">
        <label>Observed Bad Output Evidence <span style="color:var(--red);">*</span></label>
        <textarea id="pbBadOutput" rows="3" required>${isEdit ? escapeHtml(promptItem.bad_output_evidence) : ''}</textarea>
      </div>
      
      <div class="field mb-3">
        <label>Flawed Reasons (comma separated)</label>
        <input type="text" id="pbFlawedReasons" value="${isEdit && promptItem.flawed_reasons ? escapeHtml(promptItem.flawed_reasons.join(', ')) : ''}">
      </div>
      
      <div class="field mb-4">
        <label>Expected Improvements (comma separated)</label>
        <input type="text" id="pbImprovements" value="${isEdit && promptItem.expected_improvements ? escapeHtml(promptItem.expected_improvements.join(', ')) : ''}">
      </div>

      <div style="display:flex; justify-content:flex-end; gap:12px;">
        <button class="btn btn-sm" id="btnCancelPbModal">CANCEL</button>
        <button class="btn btn-sm btn-primary" id="btnSavePbModal">${isEdit ? 'SAVE CHANGES' : 'CREATE PROMPT'}</button>
      </div>
    </div>
  `;
  
  container.appendChild(modalDiv);
  
  modalDiv.querySelector('#btnCancelPbModal').addEventListener('click', () => modalDiv.remove());
  
  modalDiv.querySelector('#btnSavePbModal').addEventListener('click', async () => {
    const code = document.getElementById('pbCode').value.trim();
    const category = document.getElementById('pbCategory').value.trim();
    const title = document.getElementById('pbTitle').value.trim();
    const difficulty = document.getElementById('pbDifficulty').value;
    const original_bad_prompt = document.getElementById('pbOriginalPrompt').value.trim();
    const bad_output_evidence = document.getElementById('pbBadOutput').value.trim();
    const flawed_reasons = document.getElementById('pbFlawedReasons').value.split(',').map(s => s.trim()).filter(Boolean);
    const expected_improvements = document.getElementById('pbImprovements').value.split(',').map(s => s.trim()).filter(Boolean);
    
    if (!code || !category || !title || !original_bad_prompt || !bad_output_evidence) {
      Router.showToast('Please fill all required fields.', 'red');
      return;
    }
    
    const payload = {
      code, category, title, difficulty, original_bad_prompt, bad_output_evidence, flawed_reasons, expected_improvements
    };
    
    const btn = modalDiv.querySelector('#btnSavePbModal');
    btn.disabled = true;
    btn.textContent = 'SAVING...';
    
    let res;
    if (isEdit) {
      res = await store.updatePrompt(promptItem.id, payload);
    } else {
      res = await store.createPrompt(payload);
    }
    
    if (res.success) {
      Router.showToast(`Prompt Case ${isEdit ? 'updated' : 'created'} successfully!`, 'green');
      modalDiv.remove();
      renderAdminDashboard();
    } else {
      Router.showToast(res.error || 'Failed to save prompt', 'red');
      btn.disabled = false;
      btn.textContent = isEdit ? 'SAVE CHANGES' : 'CREATE PROMPT';
    }
  });
};
