import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderSpectatorView } from './views/spectator-view.js';


document.addEventListener('DOMContentLoaded', async () => {
  initWormhole();
  
  Router.init('live', 'calm');
  renderSpectatorView();
});
