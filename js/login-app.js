/* ==========================================================================
   NEURA LOGIN PAGE APPLICATION BOOTSTRAP (login.html)
   ========================================================================== */

import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderLoginPage } from './views/login-page.js';

document.addEventListener('DOMContentLoaded', () => {
  initWormhole();
  Router.setupStaffModal();

  // If already authenticated, redirect to main application
  if (store.isAuthenticated()) {
    window.location.href = 'index.html';
    return;
  }

  const container = document.getElementById('page-login');
  if (container) {
    renderLoginPage(container);
  }
});
