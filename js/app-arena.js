import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderArenaWorkspace } from './views/arena-workspace.js';


document.addEventListener('DOMContentLoaded', async () => {
  initWormhole();
  
  Router.init('arena', 'calm');
  renderArenaWorkspace();
});
