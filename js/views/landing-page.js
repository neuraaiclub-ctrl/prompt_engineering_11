/* ==========================================================================
   NEURA LANDING PAGE VIEW - GOOD PROMPT vs. BAD PROMPT
   Primary application entry view for the Prompt Engineering Hackathon
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';

export function renderLandingPage() {
  const container = document.getElementById('page-landing');
  if (!container) return;

  container.innerHTML = `
    <div class="landing-hero-container">
      
      <!-- Top Eyebrow & Brand Anchor -->
      <div class="landing-header">
        <div class="eyebrow" style="margin-bottom:12px;">NEURA HACKATHON PLATFORM // COMPETITION BRIEFING</div>
        <h1 class="landing-title">GOOD PROMPT <span class="vs-text">vs.</span> BAD PROMPT</h1>
      </div>

      <!-- Comparison Matrix Grid: 2 Column Side-by-Side -->
      <div class="comparison-grid">
        
        <!-- LEFT: BAD PROMPT CARD -->
        <div class="prompt-card bad glass bracket-frame">
          <span class="bl"></span><span class="br"></span>
          
          <div class="prompt-card-header">
            <div>
              <div class="card-eyebrow bad">AMBIGUOUS INPUT</div>
              <h2 class="card-heading bad">BAD PROMPT</h2>
            </div>
            <div class="status-badge bad" aria-label="Ineffective">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </div>
          </div>

          <!-- Prompt Quote Preview Box -->
          <div class="prompt-quote-box bad">
            <span class="quote-mark">“</span>
            <p class="quote-text">Write about marketing.</p>
            <span class="quote-mark end">”</span>
          </div>

          <!-- Supporting Analysis Points -->
          <ul class="prompt-points bad" role="list">
            <li>
              <span class="point-bullet bad">✕</span>
              <span><strong>Too vague</strong> — lacking defined objectives or angle</span>
            </li>
            <li>
              <span class="point-bullet bad">✕</span>
              <span><strong>No context or direction</strong> — model has to guess intent</span>
            </li>
            <li>
              <span class="point-bullet bad">✕</span>
              <span><strong>Output will be generic and uninspiring</strong> prose</span>
            </li>
          </ul>
        </div>

        <!-- RIGHT: GOOD PROMPT CARD -->
        <div class="prompt-card good glass bracket-frame">
          <span class="bl"></span><span class="br"></span>
          
          <div class="prompt-card-header">
            <div>
              <div class="card-eyebrow good">OPTIMIZED INPUT</div>
              <h2 class="card-heading good">GOOD PROMPT</h2>
            </div>
            <div class="status-badge good" aria-label="Effective">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
          </div>

          <!-- Prompt Quote Preview Box -->
          <div class="prompt-quote-box good">
            <span class="quote-mark">“</span>
            <p class="quote-text">Write a LinkedIn post about why storytelling in marketing works. Keep the tone professional yet engaging, add 3 bullet points, and end with a motivational one-liner.</p>
            <span class="quote-mark end">”</span>
          </div>

          <!-- Supporting Analysis Points -->
          <ul class="prompt-points good" role="list">
            <li>
              <span class="point-bullet good">✓</span>
              <span><strong>Clear instructions</strong> with explicit constraints & tone</span>
            </li>
            <li>
              <span class="point-bullet good">✓</span>
              <span><strong>Defined audience</strong> (LinkedIn professional readers)</span>
            </li>
            <li>
              <span class="point-bullet good">✓</span>
              <span><strong>Expected format is specified</strong> (3 bullets + one-liner)</span>
            </li>
            <li>
              <span class="point-bullet good">✓</span>
              <span><strong>Output becomes sharp, relevant, and engaging</strong></span>
            </li>
          </ul>
        </div>

      </div>

      <!-- Single Primary CTA Action -->
      <div class="landing-cta-wrap">
        <button class="btn btn-primary btn-landing-cta" id="btnLandingLogin">
          LOGIN TO PARTICIPATE →
        </button>
      </div>

    </div>
  `;

  // Attach single conversion action
  document.getElementById('btnLandingLogin')?.addEventListener('click', () => {
    if (store.isAuthenticated()) {
      const user = store.data.currentUser || {};
      Router.showToast(`Resuming active session: ${user.name || 'Team'}`, 'cyan');
      Router.navigate('arena-workspace');
    } else {
      Router.navigate('team-lobby');
      Router.showToast('Please sign in or confirm your team access code', 'cyan');
    }
  });
}
