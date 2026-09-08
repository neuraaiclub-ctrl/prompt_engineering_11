/* ==========================================================================
   NEURA SPECTATOR & LIVE PROJECTOR VIEW
   ========================================================================== */

import { store } from '../store.js';

let runoffInterval = null;
let clockInterval = null;

export function renderSpectatorView() {
  const container = document.getElementById('page-spectator-view');
  if (!container) return;

  const leaderboard = store.calculateLeaderboard();
  const teams = store.getTeams();

  container.innerHTML = `
    <div style="text-align:center; margin-bottom:28px;">
      <div class="eyebrow" style="justify-content:center;">Live Spectator Stream // Projector Display</div>
      <h1 class="heading-lg" style="font-size:38px; margin-top:6px; color:var(--text);">HUNT LEADERBOARD & LIVE RUN-OFF</h1>
      <p class="sub-text">Real-time team standings and automated evaluation stream projected live for the hackathon room.</p>
    </div>

    <!-- Live Leaderboard Table -->
    <div class="glass bracket-frame mb-4" style="padding:20px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center;" class="mb-3">
        <div class="eyebrow">Official Standings</div>
        <div class="chip chip-cyan">LIVE SCORE REFRESH</div>
      </div>

      <table class="lb-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Team Name</th>
            <th>Solved</th>
            <th>Case Score</th>
            <th>Total Points</th>
          </tr>
        </thead>
        <tbody>
          ${leaderboard.map((row, idx) => {
            const rankStr = String(idx + 1).padStart(2, '0');
            const rankClass = idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : '';
            return `
              <tr class="${idx === 0 ? 'highlight-team' : ''}">
                <td class="lb-rank ${rankClass}">${rankStr} ${idx === 0 ? '👑' : ''}</td>
                <td style="font-family:var(--disp); font-weight:700; font-size:15px; color:var(--text);">${row.teamName}</td>
                <td style="font-family:var(--mono); color:var(--muted);">${row.solved}</td>
                <td style="font-family:var(--mono); color:var(--cyan); font-weight:600;">${row.caseScore || row.r1Score} pts</td>
                <td style="font-family:var(--disp); font-weight:700; font-size:18px; color:var(--cyan);">${row.totalScore} PTS</td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>

    <!-- Live Run-Off Simulation Matrix -->
    <div class="glass bracket-frame" style="padding:24px;">
      <span class="bl"></span><span class="br"></span>
      <div style="display:flex; justify-content:space-between; align-items:center;" class="mb-3">
        <div>
          <div class="eyebrow">Live Run-Off Evaluation Stream</div>
          <div class="heading-md" style="margin-top:2px;">Prompt Case Test Execution</div>
        </div>
        <button class="btn btn-sm btn-violet" id="btnTriggerRunoffSim">⚡ RE-RUN SPECTATOR RUN-OFF</button>
      </div>

      <div class="runoff-frame">
        <div class="runoff-head">
          <span>SPECTATOR STREAM MATRIX</span>
          <span id="spectatorClock">00:00:00</span>
        </div>
        <div class="runoff-grid" id="spectatorRunoffGrid">
          <div class="runoff-corner">TEAM</div>
          <div class="runoff-col-head">CASE 01 (Format)</div>
          <div class="runoff-col-head">CASE 02 (Contradiction)</div>
          <div class="runoff-col-head">CASE 03 (Clarity)</div>

          ${teams.map((t, rowIdx) => `
            <div class="runoff-row-label">${t.name}</div>
            <div class="runoff-cell" id="spec-cell-${rowIdx}-0"></div>
            <div class="runoff-cell" id="spec-cell-${rowIdx}-1"></div>
            <div class="runoff-cell" id="spec-cell-${rowIdx}-2"></div>
          `).join('')}
        </div>
      </div>
    </div>
  `;

  // Live ticking digital clock
  if (clockInterval) clearInterval(clockInterval);
  const updateClock = () => {
    const clockElem = document.getElementById('spectatorClock');
    if (clockElem) {
      const now = new Date();
      clockElem.textContent = now.toTimeString().split(' ')[0];
    }
  };
  updateClock();
  clockInterval = setInterval(updateClock, 1000);

  // Start animated runoff matrix simulation
  initRunoffSimulation(teams.length);

  document.getElementById('btnTriggerRunoffSim')?.addEventListener('click', () => {
    initRunoffSimulation(teams.length);
  });
}

function initRunoffSimulation(teamCount) {
  if (runoffInterval) clearInterval(runoffInterval);

  // Render initial idle
  for (let r = 0; r < teamCount; r++) {
    for (let c = 0; c < 3; c++) {
      const cell = document.getElementById(`spec-cell-${r}-${c}`);
      if (cell) {
        cell.innerHTML = `<span class="status-dot idle"></span><span style="color:var(--muted);">IDLE</span>`;
      }
    }
  }

  // Staggered simulation run
  let delay = 0;
  for (let r = 0; r < teamCount; r++) {
    for (let c = 0; c < 3; c++) {
      const row = r;
      const col = c;
      const cell = document.getElementById(`spec-cell-${row}-${col}`);
      
      setTimeout(() => {
        if (cell) cell.innerHTML = `<span class="status-dot running"></span><span style="color:var(--amber);">TESTING...</span>`;
      }, delay);

      setTimeout(() => {
        if (cell) {
          const isPass = Math.random() > 0.15; // 85% pass rate
          if (isPass) {
            cell.innerHTML = `<span class="status-dot pass"></span><span style="color:var(--green);">PASSED</span>`;
          } else {
            cell.innerHTML = `<span class="status-dot fail"></span><span style="color:var(--red);">FAILED</span>`;
          }
        }
      }, delay + 600);

      delay += 140;
    }
  }
}
