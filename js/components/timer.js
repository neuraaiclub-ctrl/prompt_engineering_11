/* ==========================================================================
   NEURA SERVER-AUTHORITATIVE TIMER COMPONENT
   Controls SVG circular countdown display and timer intervals
   ========================================================================== */

import { store } from '../store.js';

let timerIntervalId = null;

/**
 * Initializes countdown loop synchronized with store hackathon timer state
 */
export function initAppTimer() {
  if (timerIntervalId) {
    clearInterval(timerIntervalId);
  }

  // Initial render
  const initialHackathon = store.getHackathon();
  if (initialHackathon && typeof initialHackathon.timerSeconds === 'number') {
    updateNavTimerUI(initialHackathon.timerSeconds);
  }

  timerIntervalId = setInterval(() => {
    const hackathon = store.getHackathon();
    if (hackathon && hackathon.isTimerRunning && hackathon.timerSeconds > 0) {
      hackathon.timerSeconds--;
      store.saveState();
      updateNavTimerUI(hackathon.timerSeconds);
    }
  }, 1000);
}

/**
 * Updates top navigation SVG circular progress ring and numerical readout
 * @param {number} totalSecs - Total remaining seconds
 */
export function updateNavTimerUI(totalSecs) {
  const m = Math.floor(totalSecs / 60).toString().padStart(2, '0');
  const s = (totalSecs % 60).toString().padStart(2, '0');

  const timerNum = document.getElementById('navTimerNum');
  const timerCircle = document.getElementById('navTimerCircle');
  const adminTimer = document.getElementById('adminTimerReadout');

  if (timerNum) timerNum.textContent = `${m}:${s}`;
  if (adminTimer) adminTimer.textContent = `${m}:${s}`;

  if (timerCircle) {
    const circ = parseFloat(timerCircle.getAttribute('stroke-dasharray')) || 113.1; // 2 * PI * r
    const frac = Math.max(totalSecs / 180, 0);
    timerCircle.style.strokeDashoffset = circ * (1 - frac);
  }
}
