/* ==========================================================================
   NEURA TEAM VIEW
   Signed out: one focused sign-in card. Signed in: your team and a way in.
   A successful sign-in plays a short entry sequence and a wormhole surge
   before the arena opens, so the page never just "jumps".
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { warpWormhole } from '../components/wormhole.js';
import { renderLoginPage } from './login-page.js';

const CHECK = '<svg viewBox="0 0 12 12"><path d="M2 6.5l2.6 2.6L10 3.4"/></svg>';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function findCurrentTeam(user) {
  const teams = store.getTeams();
  return teams.find(t =>
    t.id === user.teamId ||
    (user.email && t.loginEmail && t.loginEmail.toLowerCase() === user.email.toLowerCase()) ||
    (t.members && t.members.includes(user.name))
  ) || null;
}

function homeFor(role) {
  return role === 'admin' ? 'admin-dashboard' : role === 'judge' ? 'judge-dashboard' : 'arena-workspace';
}

export function renderTeamLobby() {
  const container = document.getElementById('page-team-lobby');
  if (!container) return;

  if (store.isAuthenticated()) renderSignedIn(container);
  else renderLoginPage(container);
}
/* ---------------------------------------------------------------------------
   Signed in
   --------------------------------------------------------------------------- */
function renderSignedIn(container) {
  const user = store.data.currentUser || {};
  const team = findCurrentTeam(user);
  const role = store.getRole();
  const title = team?.name || user.name || user.email || 'Your team';
  const members = team?.members || [];

  container.innerHTML = `
    <div class="tm">
      <div class="tm-head">
        <div>
          <div class="eyebrow">${role === 'participant' ? 'Your team' : 'Signed in'}</div>
          <h1 class="heading-lg">${esc(title)}</h1>
          <p class="tm-meta">
            ${team?.college ? esc(team.college) + ' · ' : ''}${team?.inviteCode ? 'Team code <b>' + esc(team.inviteCode) + '</b>' : esc(user.email || '')}
          </p>
        </div>
        <div class="tm-actions">
          <button class="btn btn-primary btn-lg" id="btnEnterWorkspaceNow">Enter the arena</button>
          <button class="btn btn-ghost" id="btnTeamLogout">Sign out</button>
        </div>
      </div>

      ${members.length ? `
        <ul class="tm-roster" aria-label="Team members">
          ${members.map((m, i) => `
            <li><span>${esc(m)}</span><span class="tm-role">${i === 0 ? 'Team leader' : 'Member'}</span></li>
          `).join('')}
        </ul>` : ''}

      <details class="tm-join">
        <summary>Join a different team with a code</summary>
        <div class="tm-join-body">
          <div class="field">
            <label for="joinInviteInput">Team code</label>
            <input type="text" id="joinInviteInput" placeholder="NR-4827" maxlength="7" autocapitalize="characters">
          </div>
          <button class="btn" id="btnJoinTeam">Join</button>
        </div>
      </details>
    </div>
  `;

  container.querySelector('#btnEnterWorkspaceNow')?.addEventListener('click', () => {
    warpWormhole(0.9);
    Router.navigate(homeFor(role));
  });

  container.querySelector('#btnTeamLogout')?.addEventListener('click', () => {
    Router.confirmLogout('You’ll return to the home page.');
  });

  container.querySelector('#btnJoinTeam')?.addEventListener('click', () => {
    const code = container.querySelector('#joinInviteInput').value.trim().toUpperCase();
    if (!code) { Router.showToast('Enter a team code first.', 'red'); return; }
    const match = store.getTeams().find(t => t.inviteCode.toUpperCase() === code);
    if (!match) { Router.showToast('That team code doesn’t exist.', 'red'); return; }

    if (store.data.currentUser) store.data.currentUser.teamId = match.id;
    if (!match.members.includes(user.name)) match.members.push(user.name || 'New member');
    store.setAuthenticated(true);
    store.saveState();
    Router.showToast(`Joined ${match.name}`, 'green');
    Router.applyRolePermissions('participant');
    renderTeamLobby();
  });
}
