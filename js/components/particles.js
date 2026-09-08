/* ==========================================================================
   NEURA PARTICLE BACKGROUND COMPONENT
   Generates ambient floating cyber-particle elements
   ========================================================================== */

/**
 * Initializes floating ambient particle field inside target container
 * @param {string} containerId - DOM ID of particle container
 * @param {number} count - Number of particle divs to generate
 */
export function initParticles(containerId = 'particles', count = 40) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Clear existing particles if re-initializing
  container.innerHTML = '';

  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.left = (Math.random() * 100) + 'vw';
    p.style.top = (60 + Math.random() * 40) + 'vh';
    p.style.animationDuration = (10 + Math.random() * 14) + 's';
    p.style.animationDelay = (Math.random() * 10) + 's';
    container.appendChild(p);
  }
}
