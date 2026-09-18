/* ==========================================================================
   NEURA ROUTER & VIEW CONTROLLER
   Server-Authoritative Role-Based Access Control & Navigation Routing
   ========================================================================== */

import { store } from './store.js';
import { setupStaffModal, openStaffModal, closeStaffModal } from './components/staff-modal.js';
import { renderLandingPage } from './views/landing-page.js';
import { renderTeamLobby } from './views/auth-team.js';

export const ROLE_PERMISSIONS = {
  participant: ['arena-workspace', 'r1-workspace', 'team-lobby', 'landing'],
  judge: ['judge-dashboard', 'arena-workspace', 'spectator-view', 'landing'],
  admin: ['admin-dashboard', 'arena-workspace', 'spectator-view', 'landing']
};

export class Router {
  static init() {
    this.setupNavigation();
    this.setupLogout();
    this.setupStaffModal();
    this.applyRolePermissions(store.getRole());

    // Direct authenticated users to their active workspace instead of landing briefing
    if (store.isAuthenticated()) {
      const role = store.getRole();
      const defaultView = role === 'admin' ? 'admin-dashboard' 
                        : role === 'judge' ? 'judge-dashboard' 
                        : 'arena-workspace';
      this.navigate(defaultView);
    } else {
      this.navigate('landing');
    }
  }

  static setupNavigation() {
    document.querySelectorAll('.navlinks button').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const page = e.currentTarget.getAttribute('data-page');
        this.navigate(page);
      });
    });

    document.getElementById('brandLogo')?.addEventListener('click', () => {
      if (store.isAuthenticated()) {
        const role = store.getRole();
        const defaultView = role === 'admin' ? 'admin-dashboard' 
                          : role === 'judge' ? 'judge-dashboard' 
                          : 'arena-workspace';
        this.navigate(defaultView);
      } else {
        this.navigate('landing');
      }
    });
  }

  static setupLogout() {
    document.getElementById('btnNavLogout')?.addEventListener('click', () => {
      this.confirmLogout();
    });
  }

  /**
   * Universal customized logout confirmation dialog
   */
  static confirmLogout(message = 'Your active session will be terminated. You will need to re-authenticate with your credentials or team code to resume.') {
    const modalWrap = document.getElementById('customModalContainer') || document.body;
    const existing = document.getElementById('modalLogoutConfirm');
    if (existing) existing.remove();

    const role = store.getRole();
    const user = store.data.currentUser || {};
    const roleBadge = role === 'admin' ? '<span class="chip chip-red">ADMIN SESSION</span>'
                    : role === 'judge' ? '<span class="chip chip-violet">JUDGE SESSION</span>'
                    : '<span class="chip chip-cyan">PARTICIPANT SESSION</span>';

    const modalDiv = document.createElement('div');
    modalDiv.id = 'modalLogoutConfirm';
    modalDiv.className = 'neura-modal-overlay';
    modalDiv.style.display = 'flex';
    modalDiv.innerHTML = `
      <div class="neura-modal glass bracket-frame" style="max-width:440px; width:90%; padding:28px;">
        <span class="bl"></span><span class="br"></span>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          ${roleBadge}
          <button class="btn-modal-close" id="btnCloseLogoutModal" style="background:none; border:none; color:var(--muted); font-size:22px; cursor:pointer; line-height:1;">&times;</button>
        </div>
        <h3 class="heading-md" style="margin-bottom:8px; font-size:18px;">ARE YOU SURE YOU WANT TO LOG OUT?</h3>
        <p class="sub-text" style="font-size:12.5px; line-height:1.5; margin-bottom:24px; color:var(--text-dim);">
          Logging out will terminate the session for <strong>${user.name || user.email || 'Current User'}</strong>. ${message}
        </p>
        <div style="display:flex; justify-content:flex-end; gap:12px;">
          <button class="btn btn-sm" id="btnCancelLogoutModal" style="padding:7px 16px;">CANCEL</button>
          <button class="btn btn-sm btn-red" id="btnConfirmLogoutModal" style="padding:7px 18px; font-weight:700;">YES, LOG OUT →</button>
        </div>
      </div>
    `;

    modalWrap.appendChild(modalDiv);

    const closeModal = () => modalDiv.remove();

    modalDiv.querySelector('#btnCloseLogoutModal')?.addEventListener('click', closeModal);
    modalDiv.querySelector('#btnCancelLogoutModal')?.addEventListener('click', closeModal);
    modalDiv.addEventListener('click', (e) => {
      if (e.target === modalDiv) closeModal();
    });

    modalDiv.querySelector('#btnConfirmLogoutModal')?.addEventListener('click', () => {
      closeModal();
      store.logout();
      Router.showToast('Successfully signed out of session', 'cyan');
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

  /**
   * Centralized Route Guard and Navigation Controller
   */
  static navigate(pageId) {
    const isAuth = store.isAuthenticated();
    const role = store.getRole();

    // Direct authenticated users away from landing briefing page to their workspace
    if (isAuth && pageId === 'landing') {
      const defaultView = role === 'admin' ? 'admin-dashboard' 
                        : role === 'judge' ? 'judge-dashboard' 
                        : 'arena-workspace';
      this.navigate(defaultView);
      return;
    }
    const allowedPages = ROLE_PERMISSIONS[role] || ['landing'];

    // Route Guard: Unauthenticated access protection
    const protectedPages = ['arena-workspace', 'r1-workspace', 'judge-dashboard', 'admin-dashboard'];
    if (!isAuth && protectedPages.includes(pageId)) {
      this.showToast('Please sign in to access this workspace', 'amber');
      this.navigate('team-lobby');
      return;
    }

    // Route Guard: Role-based authorization protection
    if (isAuth && !allowedPages.includes(pageId)) {
      this.showToast(`Access Denied: Your role (${role.toUpperCase()}) cannot access this view`, 'red');
      // Redirect to user's permitted default view
      const defaultView = role === 'admin' ? 'admin-dashboard' 
                        : role === 'judge' ? 'judge-dashboard' 
                        : 'arena-workspace';
      this.navigate(defaultView);
      return;
    }

    // Hide all view sections
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

    // Highlight nav link
    document.querySelectorAll('.navlinks button').forEach(btn => btn.classList.remove('on'));
    const targetNav = document.querySelector(`.navlinks button[data-page="${pageId}"]`);
    if (targetNav) targetNav.classList.add('on');

    // Show target section
    const targetSection = document.getElementById(`page-${pageId}`);
    if (targetSection) {
      targetSection.classList.add('active');
      window.scrollTo(0, 0);
    }
  }

  /**
   * Dynamically filters navigation links based on authenticated server role
   */
  static applyRolePermissions(role) {
    const isAuth = store.isAuthenticated();
    const navButtons = document.querySelectorAll('.navlinks button');

    // Visibility Matrix:
    // PARTICIPANT sees: Prompt Arena, Team Lobby
    // JUDGE sees: Judge Dashboard, Live Spectator, Prompt Arena
    // ADMIN sees: Admin Panel, Live Spectator, Prompt Arena
    navButtons.forEach(btn => {
      const page = btn.getAttribute('data-page');
      let visible = false;

      if (!isAuth) {
        visible = (page === 'arena-workspace' || page === 'team-lobby');
      } else if (role === 'participant') {
        visible = (page === 'arena-workspace' || page === 'team-lobby');
      } else if (role === 'judge') {
        visible = (page === 'judge-dashboard' || page === 'spectator-view' || page === 'arena-workspace');
      } else if (role === 'admin') {
        visible = (page === 'admin-dashboard' || page === 'spectator-view' || page === 'arena-workspace');
      }

      btn.style.display = visible ? 'inline-block' : 'none';
    });

    // Update Authenticated User Session display in top navigation
    const sessionWrap = document.getElementById('userSessionWrap');
    const roleBadge = document.getElementById('navRoleBadge');
    const userName = document.getElementById('navUserName');

    if (sessionWrap && roleBadge && userName) {
      if (isAuth) {
        sessionWrap.style.display = 'flex';
        roleBadge.textContent = role.toUpperCase();
        roleBadge.className = role === 'admin' ? 'chip chip-red'
                            : role === 'judge' ? 'chip chip-violet'
                            : 'chip chip-cyan';
        const userObj = store.data.currentUser;
        userName.textContent = userObj?.name || userObj?.email || role;
      } else {
        sessionWrap.style.display = 'none';
      }
    }
  }

  static showToast(message, type = 'cyan') {
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toastContainer';
      toastContainer.style.cssText = 'position:fixed; bottom:24px; right:24px; z-index:9999; display:flex; flex-direction:column; gap:10px; pointer-events:none;';
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `glass bracket-frame chip-${type}`;
    toast.style.cssText = 'padding:12px 18px; font-family:var(--mono); font-size:12px; border-radius:4px; box-shadow:0 6px 24px rgba(0,0,0,0.5); pointer-events:auto; animation:fadein 0.3s ease;';
    
    const bl = document.createElement('span');
    bl.className = 'bl';
    const br = document.createElement('span');
    br.className = 'br';
    const textSpan = document.createElement('span');
    textSpan.textContent = message;
    
    toast.appendChild(bl);
    toast.appendChild(br);
    toast.appendChild(textSpan);

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}
