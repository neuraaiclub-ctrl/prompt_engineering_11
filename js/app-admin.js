import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderAdminDashboard } from './views/admin-dashboard.js';
import { initAppTimer } from './components/timer.js';

document.addEventListener('DOMContentLoaded', async () => {
  initWormhole();
  initAppTimer();
  Router.init('admin', 'calm');
  renderAdminDashboard();
});
