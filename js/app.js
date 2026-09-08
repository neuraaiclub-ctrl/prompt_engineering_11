/* ==========================================================================
   NEURA APPLICATION INITIALIZATION MODULE
   Single Page Application bootstrapping, components & view mounting
   ========================================================================== */

import { store } from './store.js';
import { Router } from './router.js';
import { initParticles } from './components/particles.js';
import { initAppTimer } from './components/timer.js';
import { renderLandingPage } from './views/landing-page.js';
import { renderTeamLobby } from './views/auth-team.js';
import { renderArenaWorkspace } from './views/arena-workspace.js';
import { renderRound1Workspace } from './views/round1-workspace.js';
import { renderJudgeDashboard } from './views/judge-dashboard.js';
import { renderAdminDashboard } from './views/admin-dashboard.js';
import { renderSpectatorView } from './views/spectator-view.js';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize ambient visual components
  initParticles('particles', 40);
  
  // Initialize server-authoritative countdown loop
  initAppTimer();
  
  // Initialize role-based navigation router and staff portal
  Router.init();
  
  // Mount Single Page Application view modules
  renderLandingPage();
  renderTeamLobby();
  renderArenaWorkspace();
  renderRound1Workspace();
  renderJudgeDashboard();
  renderAdminDashboard();
  renderSpectatorView();

  // Apply default role state permissions and view bounds
  Router.applyRolePermissions(store.getRole());
});
