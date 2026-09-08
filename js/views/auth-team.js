/* ==========================================================================
   NEURA TEAM LOBBY & AUTH VIEW
   Participant Authentication, Team Management & Roster Status
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';

export function renderTeamLobby() {
  const container = document.getElementById('page-team-lobby');
  if (!container) return;

  const teams = store.getTeams();
  const user = store.data.currentUser || {};
  const currentTeam = teams.find(t => 
    t.id === user.teamId || 
    (user.email && t.loginEmail && t.loginEmail.toLowerCase() === user.email.toLowerCase()) ||
    (t.members && t.members.includes(user.name))
  ) || teams[0] || {
    name: 'Neural Mavericks',
    college: 'MMCOE Pune',
    inviteCode: 'NR-4827',
    status: 'locked',
    members: ['Alex Mercer', 'Elena Rostova', 'Kaelen Vance']
  };
  const isAuth = store.isAuthenticated();

  container.innerHTML = `
    <div class="dash-head mb-4">
      <div class="eyebrow">Team Authentication // ${currentTeam.inviteCode || 'PORTAL'}</div>
      <h1 class="heading-lg" style="margin-top:6px;">TEAM LOBBY & AUTHENTICATION</h1>
      <p class="sub-text">Authenticate your registered hackathon team to access your competition environment.</p>
    </div>

    ${!isAuth ? `
      <!-- Unauthenticated State: Clean Participant Team Login Card -->
      <div class="glass bracket-frame mb-4" style="padding:32px; max-width:620px; margin:0 auto 28px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div class="chip chip-cyan">● PARTICIPATING TEAM AUTHENTICATION</div>
          <div class="mono-text" style="font-size:11px; color:var(--muted);">NEURA 2026</div>
        </div>

        <h2 class="heading-md" style="margin-bottom:6px;">ENTER TEAM CREDENTIALS</h2>
        <p class="sub-text" style="margin-bottom:20px;">Use the login email and secure passcode provisioned by the event organizer.</p>

        <div class="field" style="margin-bottom:14px;">
          <label>Team Login Email / Team Identifier</label>
          <input type="text" id="authTeamEmail" placeholder="e.g. neural.mavericks@neura.io or NR-4827" autocomplete="username">
        </div>

        <div class="field" style="margin-bottom:18px;">
          <label>Password / Access Passcode</label>
          <input type="password" id="authTeamPassword" placeholder="••••••••••••" autocomplete="current-password">
        </div>

        <button class="btn btn-primary" style="width:100%; margin-top:8px;" id="btnPerformTeamLogin">
          SIGN IN & ENTER WORKSPACE →
        </button>
        <div id="teamLoginError" class="mono-text" style="color:var(--red); font-size:11.5px; margin-top:12px; display:none;"></div>
      </div>
    ` : `
      <!-- Authenticated State: Active Status Banner with Direct Workspace Entry -->
      <div class="glass bracket-frame mb-4" style="padding:20px 28px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; border-color:var(--cyan-dim);">
        <span class="bl"></span><span class="br"></span>
        <div>
          <div class="chip chip-green" style="margin-bottom:6px;">✓ AUTHENTICATED: ${currentTeam.name.toUpperCase()}</div>
          <div style="font-size:13px; color:var(--muted);">
            Signed in as <strong>${user.name || currentTeam.name}</strong> (${user.email || 'Team Session'})
          </div>
        </div>
        <div style="display:flex; gap:12px;">
          <button class="btn btn-primary" id="btnEnterWorkspaceNow">
            ENTER FIX PROMPT WORKSPACE →
          </button>
          <button class="btn btn-sm" id="btnTeamLogout" style="border-color:var(--line-strong);">
            LOG OUT
          </button>
        </div>
      </div>
    `}

    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px;" class="mb-4">
      <!-- Current Team Status -->
      <div class="glass bracket-frame" style="padding:28px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div class="chip ${isAuth ? 'chip-green' : 'chip-amber'}">
            ● STATUS: ${isAuth ? currentTeam.status.toUpperCase() : 'AWAITING LOGIN'}
          </div>
          <div class="mono-text" style="font-size:11px; color:var(--muted);">HACKATHON 2026</div>
        </div>

        <div style="margin-bottom:16px;">
          <div class="eyebrow" style="margin-bottom:4px;">Team Name</div>
          <div class="heading-md" style="color:var(--cyan);">${currentTeam.name}</div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">
          <div>
            <div class="eyebrow" style="margin-bottom:4px;">College / Institution</div>
            <div class="mono-text" style="font-size:14px; color:var(--text);">${currentTeam.college || 'Engineering Institute'}</div>
          </div>
          <div>
            <div class="eyebrow" style="margin-bottom:4px;">Invite Code</div>
            <div class="mono-text" style="font-size:15px; font-weight:700; color:var(--cyan);">${currentTeam.inviteCode}</div>
          </div>
        </div>

        <div class="eyebrow" style="margin-bottom:10px;">Active Roster (${(currentTeam.members || []).length} Members)</div>
        <div style="display:flex; flex-direction:column; gap:8px;">
          ${(currentTeam.members || []).map((m, idx) => `
            <div class="glass-card" style="padding:10px 14px; display:flex; justify-content:space-between; align-items:center; font-family:var(--mono); font-size:12.5px;">
              <span>${m} ${idx === 0 ? '<span style="color:var(--cyan); font-size:10px; margin-left:6px;">(LEADER)</span>' : ''}</span>
              <span style="color:var(--green); font-size:10.5px;">READY</span>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Join or Create Team Action Cards (For Forming Stages) -->
      <div style="display:flex; flex-direction:column; gap:20px;">
        <!-- Join Team Form -->
        <div class="glass bracket-frame" style="padding:24px;">
          <span class="bl"></span><span class="br"></span>
          <div class="eyebrow" style="margin-bottom:8px;">Join Existing Team</div>
          <div class="heading-md" style="margin-bottom:12px;">ENTER INVITE CODE</div>
          <div class="field">
            <label>6-Character Team Code</label>
            <input type="text" id="joinInviteInput" placeholder="e.g. NR-4827" maxlength="7">
          </div>
          <button class="btn btn-primary" style="width:100%;" id="btnJoinTeam">JOIN TEAM →</button>
        </div>

        <!-- Help Info Card -->
        <div class="glass bracket-frame" style="padding:24px;">
          <span class="bl"></span><span class="br"></span>
          <div class="eyebrow" style="margin-bottom:8px;">Notice for Participants</div>
          <div class="heading-md" style="margin-bottom:8px; font-size:16px;">EVENT CREDENTIALS</div>
          <p class="sub-text" style="font-size:12px; line-height:1.5;">
            All participating teams receive their unique login email and passcode during on-site registration. 
            If you need credential assistance, contact your Hackathon Director or room judge.
          </p>
        </div>
      </div>
    </div>
  `;

  // Attach Event Handlers
  const loginBtn = document.getElementById('btnPerformTeamLogin');
  const errBox = document.getElementById('teamLoginError');

  const executeLogin = async () => {
    const inputVal = document.getElementById('authTeamEmail')?.value.trim();
    const passVal = document.getElementById('authTeamPassword')?.value.trim();

    if (!inputVal) {
      Router.showToast('Please enter your team login email or invite code', 'red');
      return;
    }

    if (loginBtn) {
      loginBtn.disabled = true;
      loginBtn.textContent = 'VERIFYING CREDENTIALS...';
    }

    // Attempt login via store
    const result = await store.loginWithCredentials(inputVal, passVal || 'Pass123!');

    if (loginBtn) {
      loginBtn.disabled = false;
      loginBtn.textContent = 'SIGN IN & ENTER WORKSPACE →';
    }

    if (result.success) {
      Router.showToast(`Welcome back, ${result.user.name || result.user.email}!`, 'green');
      Router.applyRolePermissions(result.role);
      renderTeamLobby();
      setTimeout(() => {
        if (result.role === 'admin') {
          Router.navigate('admin-dashboard');
        } else if (result.role === 'judge') {
          Router.navigate('judge-dashboard');
        } else {
          Router.navigate('arena-workspace');
        }
      }, 250);
    } else {
      // Fallback check: If user typed an invite code directly
      const codeMatch = teams.find(t => t.inviteCode.toUpperCase() === inputVal.toUpperCase());
      if (codeMatch) {
        store.data.currentUser = {
          id: 'usr-' + codeMatch.id,
          name: codeMatch.name,
          email: `${codeMatch.name.toLowerCase().replace(/\s+/g, '.')}@neura.io`,
          teamId: codeMatch.id,
          roles: ['participant']
        };
        store.setRole('participant');
        store.setAuthenticated(true);
        Router.showToast(`Authenticated with invite code for ${codeMatch.name}!`, 'green');
        Router.applyRolePermissions('participant');
        renderTeamLobby();
        setTimeout(() => Router.navigate('arena-workspace'), 250);
      } else {
        if (errBox) {
          errBox.textContent = result.error || 'Invalid credentials or invite code.';
          errBox.style.display = 'block';
        }
        Router.showToast(result.error || 'Authentication failed', 'red');
      }
    }
  };

  loginBtn?.addEventListener('click', executeLogin);
  document.getElementById('authTeamPassword')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') executeLogin();
  });

  document.getElementById('btnEnterWorkspaceNow')?.addEventListener('click', () => {
    Router.navigate('arena-workspace');
  });

  document.getElementById('btnTeamLogout')?.addEventListener('click', () => {
    Router.confirmLogout('Logging out of your team session will return you to the home briefing.');
  });

  document.getElementById('btnJoinTeam')?.addEventListener('click', () => {
    const code = document.getElementById('joinInviteInput').value.trim().toUpperCase();
    if (!code) { Router.showToast('Please enter a team invite code', 'red'); return; }
    const match = store.getTeams().find(t => t.inviteCode.toUpperCase() === code);
    if (match) {
      if (store.data.currentUser) store.data.currentUser.teamId = match.id;
      if (!match.members.includes(user.name)) match.members.push(user.name || 'New Member');
      store.setAuthenticated(true);
      store.saveState();
      Router.showToast(`Successfully joined team: ${match.name}`, 'green');
      Router.applyRolePermissions('participant');
      renderTeamLobby();
    } else {
      Router.showToast('Invalid team invite code', 'red');
    }
  });
}
