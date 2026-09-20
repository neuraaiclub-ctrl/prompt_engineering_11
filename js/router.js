/* ==========================================================================
   NEURA ROUTER & VIEW CONTROLLER
   Role-based navigation, route guards, page mood for the wormhole background,
   and the shared modal/toast helpers.
   ========================================================================== */

import { store } from './store.js';
import { setupStaffModal } from './components/staff-modal.js';
import { setWormholeMood, warpWormhole } from './components/wormhole.js';
import { renderLandingPage } from './views/landing-page.js';
import { renderTeamLobby } from './views/auth-team.js';

export const ROLE_PERMISSIONS = {
  participant: ['arena-workspace', 'r1-workspace', 'team-lobby', 'landing'],
  judge: ['judge-dashboard', 'arena-workspace', 'spectator-view', 'landing'],
  admin: ['admin-dashboard', 'judge-dashboard', 'arena-workspace', 'spectator-view', 'landing']
};

/* How visible the tunnel is behind each page */
const PAGE_MOOD = {
  landing: 'calm',
  'team-lobby': 'calm',
  'arena-workspace': 'calm',   // the arena view switches to 'focus' itself while a prompt is live
  'spectator-view': 'calm'
};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function homeFor(role) {
  return role === 'admin' ? 'admin-dashboard' : role === 'judge' ? 'judge-dashboard' : 'arena-workspace';
}

export class Router {
  /** Views that must (re)render every time they are entered, e.g. the arena after sign-in */
  static onEnter = {};

  static registerOnEnter(pageId, fn) { this.onEnter[pageId] = fn; }

  static init() {
    this.setupNavigation();
    this.setupLogout();
    this.setupStaffModal();
    this.applyRolePermissions(store.getRole());

    // Signed-in users go straight to their workspace, everyone else to the landing page
    this.navigate(store.isAuthenticated() ? homeFor(store.getRole()) : 'landing');
  }

  static setupNavigation() {
    document.querySelectorAll('.navlinks button').forEach(btn => {
      btn.addEventListener('click', (e) => this.navigate(e.currentTarget.getAttribute('data-page')));
    });

    const brand = document.getElementById('brandLogo');
    const goHome = () => this.navigate(store.isAuthenticated() ? homeFor(store.getRole()) : 'landing');
    brand?.addEventListener('click', goHome);
    brand?.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goHome(); } });

    document.getElementById('btnNavSignIn')?.addEventListener('click', () => this.navigate('team-lobby'));
  }

  static setupLogout() {
    document.getElementById('btnNavLogout')?.addEventListener('click', () => this.confirmLogout());
  }

  /** Confirmation dialog shared by every "sign out" button */
  static confirmLogout(message = 'You’ll need to sign in again to continue.') {
    document.getElementById('modalLogoutConfirm')?.remove();

    const user = store.data.currentUser || {};
    const who = user.name || user.email || 'this account';

    const overlay = document.createElement('div');
    overlay.id = 'modalLogoutConfirm';
    overlay.className = 'neura-modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.innerHTML = `
      <div class="neura-modal" style="max-width:420px; width:100%; padding:28px;">
        <h3 class="modal-title">Sign out?</h3>
        <p class="modal-body">This ends the session for <strong>${esc(who)}</strong>. ${esc(message)}</p>
        <div class="modal-actions">
          <button class="btn" id="btnCancelLogoutModal">Stay signed in</button>
          <button class="btn btn-red" id="btnConfirmLogoutModal">Sign out</button>
        </div>
      </div>
    `;
    (document.getElementById('customModalContainer') || document.body).appendChild(overlay);

    const close = () => overlay.remove();
    overlay.querySelector('#btnCancelLogoutModal').addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    overlay.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
    overlay.querySelector('#btnCancelLogoutModal').focus();

    overlay.querySelector('#btnConfirmLogoutModal').addEventListener('click', () => {
      close();
      store.logout();
      Router.showToast('Signed out', 'cyan');
      Router.applyRolePermissions('participant');
      renderLandingPage();
      renderTeamLobby();
      Router.navigate('landing');
    });
  }

  static setupStaffModal() {
    setupStaffModal({
      showToast: (msg, type) => Router.showToast(msg, type),
      applyRolePermissions: (role) => Router.applyRolePermissions(role),
      navigate: (page) => Router.navigate(page)
    });
  }

  /** Central route guard + view switch */
  static navigate(pageId) {
    const isAuth = store.isAuthenticated();
    const role = store.getRole();

    if (isAuth && pageId === 'landing') { this.navigate(homeFor(role)); return; }

    const protectedPages = ['arena-workspace', 'r1-workspace', 'judge-dashboard', 'admin-dashboard'];
    if (!isAuth && protectedPages.includes(pageId)) {
      this.showToast('Sign in to open this page.', 'amber');
      this.navigate('team-lobby');
      return;
    }

    const allowedPages = ROLE_PERMISSIONS[role] || ['landing'];
    if (isAuth && !allowedPages.includes(pageId)) {
      this.showToast(`Your ${role} account can’t open that page.`, 'red');
      this.navigate(homeFor(role));
      return;
    }

    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.navlinks button').forEach(btn => btn.classList.remove('on'));
    document.querySelector(`.navlinks button[data-page="${pageId}"]`)?.classList.add('on');

    // Page-level hooks for CSS and the background
    document.body.dataset.page = pageId;
    if (pageId !== 'arena-workspace') document.body.classList.remove('focus-mode');
    setWormholeMood(PAGE_MOOD[pageId] || 'dim');

    const target = document.getElementById(`page-${pageId}`);
    if (target) {
      target.classList.add('active');
      window.scrollTo(0, 0);
    }

    this.onEnter[pageId]?.();
  }

  /** Show only the links this role may use; signed-out visitors get a Sign in button instead */
  static applyRolePermissions(role) {
    const isAuth = store.isAuthenticated();

    const visibleFor = {
      participant: ['arena-workspace', 'team-lobby'],
      judge: ['judge-dashboard', 'spectator-view', 'arena-workspace'],
      admin: ['admin-dashboard', 'spectator-view', 'arena-workspace']
    };

    document.querySelectorAll('.navlinks button').forEach(btn => {
      const page = btn.getAttribute('data-page');
      const visible = isAuth && (visibleFor[role] || []).includes(page);
      btn.style.display = visible ? 'inline-block' : 'none';
    });

    const signIn = document.getElementById('btnNavSignIn');
    if (signIn) signIn.style.display = isAuth ? 'none' : 'inline-flex';

    const sessionWrap = document.getElementById('userSessionWrap');
    const roleBadge = document.getElementById('navRoleBadge');
    const userName = document.getElementById('navUserName');
    if (sessionWrap && roleBadge && userName) {
      if (isAuth) {
        sessionWrap.style.display = 'flex';
        roleBadge.textContent = role.charAt(0).toUpperCase() + role.slice(1);
        roleBadge.dataset.role = role;
        const u = store.data.currentUser;
        userName.textContent = u?.name || u?.email || role;
      } else {
        sessionWrap.style.display = 'none';
      }
    }
  }

  static showToast(message, type = 'cyan') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.setAttribute('aria-live', 'polite');
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('leaving');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}

export { warpWormhole };
