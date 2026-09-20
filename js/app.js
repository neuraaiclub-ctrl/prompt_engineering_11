/* ==========================================================================
   NEURA APPLICATION BOOTSTRAP
   ========================================================================== */

import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { initAppTimer } from './components/timer.js';
import { renderLandingPage } from './views/landing-page.js';
import { renderTeamLobby } from './views/auth-team.js';
import { renderArenaWorkspace } from './views/arena-workspace.js';
import { renderRound1Workspace } from './views/round1-workspace.js';
import { renderJudgeDashboard } from './views/judge-dashboard.js';
import { renderAdminDashboard } from './views/admin-dashboard.js';
import { renderSpectatorView } from './views/spectator-view.js';

document.addEventListener('DOMContentLoaded', async () => {
  // Preview mode (?demo) swaps the arena API for sample data. Loaded lazily so it costs nothing otherwise.
  if (new URLSearchParams(window.location.search).has('demo')) {
    const { installArenaDemo } = await import('./demo/arena-demo.js');
    installArenaDemo(store);
  }

  initWormhole();
  initAppTimer();

  Router.registerOnEnter('arena-workspace', renderArenaWorkspace);
  Router.registerOnEnter('team-lobby', renderTeamLobby);
  Router.registerOnEnter('round1-workspace', renderRound1Workspace);
  Router.registerOnEnter('judge-dashboard', renderJudgeDashboard);
  Router.registerOnEnter('admin-dashboard', renderAdminDashboard);
  Router.registerOnEnter('spectator-view', renderSpectatorView);

  Router.init();
  renderLandingPage();

  Router.applyRolePermissions(store.getRole());
});
