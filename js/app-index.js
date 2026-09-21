import { store } from './store.js';
import { Router } from './router.js';
import { initWormhole } from './components/wormhole.js';
import { renderLandingPage } from './views/landing-page.js';

document.addEventListener('DOMContentLoaded', async () => {
  if (new URLSearchParams(window.location.search).has('demo')) {
    const { installArenaDemo } = await import('./demo/arena-demo.js');
    installArenaDemo(store);
  }

  initWormhole();
  Router.init('landing', 'calm');
  renderLandingPage();
});
