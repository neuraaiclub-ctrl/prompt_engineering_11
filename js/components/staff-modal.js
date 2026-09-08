/* ==========================================================================
   NEURA STAFF PORTAL MODAL COMPONENT
   Discreet authentication overlay for hackathon directors and evaluation judges
   Triggered via Ctrl+Shift+S, Alt+A, or URL hash '#staff'
   ========================================================================== */

import { store } from '../store.js';

let modalInitialized = false;

/**
 * Open staff login modal
 */
export function openStaffModal() {
  const modal = document.getElementById('modalStaffLogin');
  const emailInput = document.getElementById('staffEmailInput');
  const passInput = document.getElementById('staffPasswordInput');
  const errBox = document.getElementById('staffLoginError');

  if (!modal) return;
  modal.style.display = 'flex';
  if (errBox) errBox.style.display = 'none';
  if (emailInput) {
    emailInput.value = '';
    setTimeout(() => emailInput.focus(), 100);
  }
  if (passInput) passInput.value = '';
}

/**
 * Close staff login modal
 */
export function closeStaffModal() {
  const modal = document.getElementById('modalStaffLogin');
  if (modal) modal.style.display = 'none';
  if (window.location.hash === '#staff') {
    history.replaceState(null, null, ' ');
  }
}

/**
 * Initialize staff modal event handlers and keyboard shortcuts
 * @param {Object} callbacks - Router callbacks { onLoginSuccess, showToast, navigate, applyRolePermissions }
 */
export function setupStaffModal(callbacks = {}) {
  if (modalInitialized) return;
  modalInitialized = true;

  const modal = document.getElementById('modalStaffLogin');
  const closeBtn = document.getElementById('btnCloseStaffModal');
  const emailInput = document.getElementById('staffEmailInput');
  const passInput = document.getElementById('staffPasswordInput');
  const submitBtn = document.getElementById('btnPerformStaffLogin');
  const errBox = document.getElementById('staffLoginError');

  // Discreet unadvertised keyboard shortcuts: Ctrl+Shift+S or Alt+A
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey && e.shiftKey && (e.key === 'S' || e.key === 's')) ||
        (e.altKey && (e.key === 'A' || e.key === 'a'))) {
      e.preventDefault();
      openStaffModal();
    }
    if (e.key === 'Escape' && modal && modal.style.display === 'flex') {
      closeStaffModal();
    }
  });

  // URL hash trigger
  if (window.location.hash === '#staff') {
    openStaffModal();
  }
  window.addEventListener('hashchange', () => {
    if (window.location.hash === '#staff') openStaffModal();
  });

  closeBtn?.addEventListener('click', closeStaffModal);
  modal?.addEventListener('click', (e) => {
    if (e.target === modal) closeStaffModal();
  });

  const handleStaffLogin = async () => {
    const email = emailInput?.value.trim();
    const password = passInput?.value.trim();

    if (!email || !password) {
      if (errBox) {
        errBox.textContent = 'Please enter both staff email and password.';
        errBox.style.display = 'block';
      }
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'AUTHENTICATING...';
    }

    const res = await store.loginWithCredentials(email, password);

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'AUTHENTICATE & ENTER →';
    }

    if (res.success) {
      closeStaffModal();
      if (callbacks.showToast) {
        callbacks.showToast(`Authenticated as ${res.role.toUpperCase()} (${res.user.name || res.user.email})!`, 'green');
      }
      if (callbacks.applyRolePermissions) {
        callbacks.applyRolePermissions(res.role);
      }

      if (callbacks.navigate) {
        if (res.role === 'admin') {
          callbacks.navigate('admin-dashboard');
        } else if (res.role === 'judge') {
          callbacks.navigate('judge-dashboard');
        } else {
          callbacks.navigate('arena-workspace');
        }
      }
    } else {
      if (errBox) {
        errBox.textContent = res.error || 'Invalid staff credentials or unauthorized account.';
        errBox.style.display = 'block';
      }
    }
  };

  submitBtn?.addEventListener('click', handleStaffLogin);
  passInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleStaffLogin();
  });
}
