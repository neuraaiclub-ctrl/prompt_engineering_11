import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderTeamLobby } from './views/auth-team.js';


document.addEventListener('DOMContentLoaded', async () => {
  initWormhole();
  
  Router.init('team', 'calm');
  renderTeamLobby();
});
