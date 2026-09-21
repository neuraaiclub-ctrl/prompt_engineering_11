/* ==========================================================================
   NEURA ROUTER & AUTH GUARD (MPA Version)
   Role-based navigation guards, shared UI helpers (toast, modal).
   ========================================================================== */

import { store } from './store.js';
import { setupStaffModal } from './components/staff-modal.js';
import { setWormholeMood, warpWormhole } from './components/wormhole.js';

export const ROLE_PERMISSIONS = {
  participant: ['arena', 'r1', 'team'],
  judge: ['judge', 'arena', 'live'],
  admin: ['admin', 'judge', 'arena', 'live']
};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function homeFor(role) {
  return role === 'admin' ? 'admin.html' : role === 'judge' ? 'judge.html' : 'arena.html';
}

export class Router {
  static init(currentPage, mood = 'calm') {
    this.setupLogout();
    this.setupStaffModal();
    this.applyRolePermissions(store.getRole());
    this.guardRoute(currentPage);
    
    document.body.dataset.page = currentPage;
    setWormholeMood(mood);
    
    // Highlight the active nav link
    document.querySelectorAll('.navlinks a').forEach(btn => btn.classList.remove('on'));
    const activeLink = document.querySelector(`.navlinks a[data-page="${currentPage}"]`);
    if (activeLink) activeLink.classList.add('on');
  }

  static guardRoute(pageId) {
    const isAuth = store.isAuthenticated();
    const role = store.getRole();

    // If on landing or login while authenticated, redirect to home
    if (isAuth && (pageId === 'landing' || pageId === 'login')) {
      window.location.href = homeFor(role);
      return;
    }

    const protectedPages = ['arena', 'r1', 'team', 'judge', 'admin', 'live'];
    if (!isAuth && protectedPages.includes(pageId)) {
      this.showToast('Sign in to open this page.', 'amber');
      window.location.href = 'login.html';
      return;
    }

    const allowedPages = ROLE_PERMISSIONS[role] || [];
    if (isAuth && protectedPages.includes(pageId) && !allowedPages.includes(pageId)) {
      this.showToast(`Your ${role} account can’t open that page.`, 'red');
      window.location.href = homeFor(role);
      return;
    }
  }

  static setupLogout() {
    document.getElementById('btnNavLogout')?.addEventListener('click', () => this.confirmLogout());
  }

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
      window.location.href = 'index.html';
    });
  }

  static setupStaffModal() {
    setupStaffModal({
      showToast: (msg, type) => Router.showToast(msg, type),
      applyRolePermissions: (role) => Router.applyRolePermissions(role),
      navigate: (page) => {
        const role = store.getRole();
        window.location.href = homeFor(role);
      }
    });
  }

  static applyRolePermissions(role) {
    const isAuth = store.isAuthenticated();

    const visibleFor = {
      participant: ['arena', 'team'],
      judge: ['judge', 'live', 'arena'],
      admin: ['admin', 'live', 'arena']
    };

    document.querySelectorAll('.navlinks a').forEach(btn => {
      const page = btn.getAttribute('data-page');
      if (page) {
        const visible = isAuth && (visibleFor[role] || []).includes(page);
        btn.style.display = visible ? 'inline-flex' : 'none';
      }
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
