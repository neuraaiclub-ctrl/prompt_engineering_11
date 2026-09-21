/* ==========================================================================
   NEURA LOGIN PAGE VIEW
   Focused login page with team email / invite code authentication, error handling,
   and animated entry sequence into the prompt engineering arena.
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { warpWormhole } from '../components/wormhole.js';
import { renderTeamLobby } from './auth-team.js';

const CHECK = '<svg viewBox="0 0 12 12"><path d="M2 6.5l2.6 2.6L10 3.4"/></svg>';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function homeFor(role) {
  return role === 'admin' ? 'admin-dashboard' : role === 'judge' ? 'judge-dashboard' : 'arena-workspace';
}

export function renderLoginPage(targetContainer) {
  const container = targetContainer || document.getElementById('page-login') || document.getElementById('page-team-lobby');
  if (!container) return;

  if (store.isAuthenticated()) {
    const role = store.getRole();
    Router.navigate(homeFor(role));
    return;
  }

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
    void card.offsetWidth; // restart the animation
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

    // Fallback: identifier may be a team invite code
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

/* Entry sequence animation upon successful sign-in */
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
  if (window.location.pathname.endsWith('login.html') || window.location.href.includes('login.html')) {
    window.location.href = 'index.html';
  } else {
    renderTeamLobby();
    Router.navigate(homeFor(role));
  }
}
