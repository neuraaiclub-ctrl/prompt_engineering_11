/* ==========================================================================
   NEURA SPECTATOR & LIVE PROJECTOR VIEW
   ========================================================================== */

import { store } from '../store.js';

let runoffInterval = null;
let clockInterval = null;
let leaderboardPollInterval = null;

export async function renderSpectatorView() {
  const container = document.getElementById('page-spectator-view');
  if (!container) return;

  if (leaderboardPollInterval) clearInterval(leaderboardPollInterval);
  leaderboardPollInterval = setInterval(() => {
    if (document.getElementById('page-spectator-view')?.parentElement?.classList.contains('active') || document.body.dataset.page === 'live') {
      renderSpectatorView();
    } else {
      clearInterval(leaderboardPollInterval);
    }
  }, 5000);

  const leaderboard = await store.getArenaLeaderboard();
  const teams = await store.getAdminTeams();

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

      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
        ${leaderboard.map((row, idx) => {
          const rankStr = row.rank ? String(row.rank).padStart(2, '0') : '--';
          const rankClass = row.podium === 'winner' ? 'gold' : row.podium === 'runner_up' ? 'silver' : row.podium === 'second_runner_up' ? 'bronze' : '';
          
          // Separate color block for the first 10 teams
          const blockStyle = idx < 10 
            ? 'background: linear-gradient(135deg, rgba(71, 224, 255, 0.15) 0%, rgba(154, 123, 255, 0.1) 100%); border: 1px solid var(--cyan);' 
            : 'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);';

          return `
            <div style="padding: 12px; border-radius: 8px; display: flex; flex-direction: column; gap: 8px; ${blockStyle} ${row.is_eliminated ? 'opacity: 0.5;' : ''}">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="lb-rank ${rankClass}" style="font-size: 16px;">${rankStr} ${row.podium === 'winner' ? '👑' : ''}</span>
                  <span style="font-family:var(--disp); font-weight:700; font-size:15px; color:var(--text); ${row.is_eliminated ? 'text-decoration:line-through;' : ''}">
                    ${row.team_name} ${row.is_eliminated ? '<span style="color:var(--red); font-size:10px;">(ELIMINATED)</span>' : ''}
                  </span>
                </div>
                <div style="font-family:var(--disp); font-weight:700; font-size:16px; color:var(--cyan);">
                  ${row.total_score.toFixed(1)} PTS
                </div>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; font-family:var(--mono);">
                <span style="color:var(--muted);">Solved: ${row.completed_challenges}/5</span>
                <span style="color:var(--cyan); font-weight:600;">Score: ${row.average_score.toFixed(1)} avg</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
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

async function initRunoffSimulation(teamCount) {
  if (runoffInterval) clearInterval(runoffInterval);

  // Poll the backend endpoint every 3 seconds for live execution status
  const fetchAndRender = async () => {
    try {
      const resp = await fetch('/api/v1/spectator/runoff-stream', {
        headers: { 'Authorization': `Bearer ${store.getToken()}` }
      });
      if (!resp.ok) return;
      const data = await resp.json();
      
      const stream = data.stream || [];
      stream.forEach((teamData, r) => {
        for (let c = 0; c < 3; c++) {
          const cell = document.getElementById(`spec-cell-${r}-${c}`);
          if (!cell) continue;

          if (teamData.status === 'idle') {
            cell.innerHTML = `<span class="status-dot idle"></span><span style="color:var(--muted);">IDLE</span>`;
          } else if (teamData.status === 'testing') {
            cell.innerHTML = `<span class="status-dot running"></span><span style="color:var(--amber);">TESTING...</span>`;
          } else if (teamData.status === 'completed') {
            // Check if this case index falls under pass_count
            const isPass = c < teamData.pass_count;
            if (isPass) {
              cell.innerHTML = `<span class="status-dot pass"></span><span style="color:var(--green);">PASSED</span>`;
            } else {
              cell.innerHTML = `<span class="status-dot fail"></span><span style="color:var(--red);">FAILED</span>`;
            }
          }
        }
      });
    } catch (e) {
      console.error('Runoff stream error', e);
    }
  };

  // Initial fetch
  await fetchAndRender();

  // Poll interval
  runoffInterval = setInterval(fetchAndRender, 3000);
}
