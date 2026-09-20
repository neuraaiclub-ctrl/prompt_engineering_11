/* ==========================================================================
   NEURA TEAM VIEW
   Signed out: one focused sign-in card. Signed in: your team and a way in.
   A successful sign-in plays a short entry sequence and a wormhole surge
   before the arena opens, so the page never just "jumps".
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { warpWormhole } from '../components/wormhole.js';

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
  else renderSignIn(container);
}

/* ---------------------------------------------------------------------------
   Signed out
   --------------------------------------------------------------------------- */
function renderSignIn(container) {
  container.innerHTML = `
    <div class="gw">
      <div class="gw-card" id="gwCard">
        <h1>Team sign-in</h1>
        <p class="gw-sub">Use the credentials sent after your registration was verified. A team code works too.</p>

        <form id="teamLoginForm" novalidate>
          <div class="field">
            <label for="authTeamEmail">Team email or code</label>
            <input type="text" id="authTeamEmail" placeholder="team@school.edu or NR-4827" autocomplete="username" autocapitalize="off" spellcheck="false">
          </div>
          <div class="field">
            <label for="authTeamPassword">Password</label>
            <input type="password" id="authTeamPassword" autocomplete="current-password">
          </div>
          <button class="btn btn-primary btn-lg gw-submit" id="btnPerformTeamLogin" type="submit">
            <span class="gw-submit-label">Sign in</span>
          </button>
          <p class="gw-error" id="teamLoginError" role="alert"></p>
        </form>
      </div>
      <p class="gw-foot">Sign-up is closed. Teams register through the official form. If your credentials don’t work, ask a hackathon director.</p>
    </div>
  `;

  const card = container.querySelector('#gwCard');
  const form = container.querySelector('#teamLoginForm');
  const btn = container.querySelector('#btnPerformTeamLogin');
  const label = btn.querySelector('.gw-submit-label');
  const errBox = container.querySelector('#teamLoginError');

  const fail = (msg) => {
    errBox.textContent = msg;
    card.classList.remove('shake');
    void card.offsetWidth;              // restart the animation
    card.classList.add('shake');
    Router.showToast(msg, 'red');
  };

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errBox.textContent = '';
    const id = container.querySelector('#authTeamEmail').value.trim();
    const pass = container.querySelector('#authTeamPassword').value.trim();

    if (!id) { fail('Enter your team email or team code.'); container.querySelector('#authTeamEmail').focus(); return; }

    btn.classList.add('busy');
    btn.disabled = true;
    label.textContent = 'Checking credentials';

    const result = await store.loginWithCredentials(id, pass);

    if (result.success) {
      await playEntrySequence(card, result);
      return;
    }

    // Fallback: the identifier may be a team invite code
    const codeMatch = store.getTeams().find(t => t.inviteCode.toUpperCase() === id.toUpperCase());
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
      await playEntrySequence(card, { role: 'participant', user: store.data.currentUser });
      return;
    }

    btn.classList.remove('busy');
    btn.disabled = false;
    label.textContent = 'Sign in';
    fail(result.error || 'Those details didn’t match a team. Check them and try again.');
  });

  setTimeout(() => container.querySelector('#authTeamEmail')?.focus(), 250);
}

/* A short, honest sequence: each line ticks once the step it names is done. */
async function playEntrySequence(card, result) {
  const role = result.role || 'participant';
  const name = result.user?.name || result.user?.email || 'there';
  const lines = role === 'participant'
    ? ['Credentials verified', `Team found: ${name}`, 'Arena ready']
    : ['Credentials verified', `Signed in as ${role}`, 'Dashboard ready'];

  card.innerHTML = `
    <h1>Welcome${role === 'participant' ? '' : ', ' + esc(name)}</h1>
    <p class="gw-sub">${role === 'participant' ? esc(name) : 'Opening your workspace.'}</p>
    <ul class="gw-seq" aria-live="polite">
      ${lines.map(l => `<li><span class="tick">${CHECK}</span><span>${esc(l)}</span></li>`).join('')}
    </ul>
  `;

  const items = [...card.querySelectorAll('.gw-seq li')];
  warpWormhole(1.1);
  for (const li of items) {
    await sleep(420);
    li.classList.add('done');
  }
  await sleep(500);

  Router.applyRolePermissions(role);
  renderTeamLobby();
  Router.navigate(homeFor(role));
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
