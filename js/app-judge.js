import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderJudgeDashboard } from './views/judge-dashboard.js';


document.addEventListener('DOMContentLoaded', async () => {
  initWormhole();
  
  Router.init('judge', 'calm');
  renderJudgeDashboard();
});
