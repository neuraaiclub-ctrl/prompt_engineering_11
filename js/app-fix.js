import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderRound1Workspace } from './views/round1-workspace.js';
import { initAppTimer } from './components/timer.js';

document.addEventListener('DOMContentLoaded', async () => {
  initWormhole();
  initAppTimer();
  Router.init('fix', 'calm');
  renderRound1Workspace();
});
