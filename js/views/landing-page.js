/* ==========================================================================
   NEURA LANDING PAGE
   Instead of two static "good vs bad" cards, the hero shows the actual job:
   a vague prompt gets rewritten piece by piece while the model output
   changes from generic to precise. The loop runs until the visitor leaves.
   ========================================================================== */

import { store } from '../store.js';
import { Router } from '../router.js';
import { warpWormhole } from '../components/wormhole.js';

const BROKEN_PROMPT = 'Write about marketing.';

const BROKEN_OUTPUT =
  'Marketing is an important part of any business. It helps companies reach customers and grow. ' +
  'There are many types of marketing, such as digital and traditional marketing. ' +
  'Businesses should use marketing to succeed.';

/* Each segment of the repaired prompt carries the tag it teaches. */
const FIXED_SEGMENTS = [
  { tag: 'role',     text: 'You are a B2B content strategist. ' },
  { tag: null,       text: 'Write a LinkedIn post on why storytelling works in marketing. ' },
  { tag: 'audience', text: 'Audience: marketing managers. ' },
  { tag: 'format',   text: 'Format: three bullets, then a one-line closer. ' },
  { tag: 'limits',   text: 'Tone: professional, warm. Under 120 words.' }
];

const FIXED_OUTPUT = [
  'Most B2B posts list features. The ones people remember tell a story.',
  '• A customer’s before-and-after beats any chart on a slide.',
  '• Stories let buyers picture themselves inside the result.',
  '• A narrative is easier to repeat to the rest of the team.',
  'Lead with the customer, not the product.'
];

const TAGS = [
  { key: 'role', label: 'Role' },
  { key: 'audience', label: 'Audience' },
  { key: 'format', label: 'Format' },
  { key: 'limits', label: 'Limits' }
];

let runId = 0;

export function renderLandingPage() {
  const container = document.getElementById('page-landing');
  if (!container) return;

  const myRun = ++runId;

  container.innerHTML = `
    <div class="lp">
      <div class="lp-copy">
        <h1 class="heading-xl">Five broken prompts.<br>Make each one work.</h1>
        <p class="lp-lede">
          Every team gets its own set. Find what the model would have to guess,
          rewrite the prompt, and lock it in before you move on.
        </p>
        <div class="lp-actions">
          <button class="btn btn-primary btn-lg" id="btnLandingLogin">Enter the arena</button>
          <span class="lp-note">Credentials are sent once your registration is verified.</span>
        </div>
      </div>

      <div class="lab" id="lab" data-state="idle" aria-label="Live example of a prompt being repaired">
        <div class="lab-bar">
          <span class="lab-dot" aria-hidden="true"></span>
          <span class="lab-status" id="labStatus" aria-live="polite">Reading the prompt</span>
        </div>

        <div class="lab-block">
          <div class="lab-label">Prompt</div>
          <p class="lab-prompt" id="labPrompt"></p>
          <ul class="lab-tags" aria-label="What the rewrite adds">
            ${TAGS.map(t => `<li data-tag="${t.key}">${t.label}</li>`).join('')}
          </ul>
        </div>

        <div class="lab-block lab-out">
          <div class="lab-label">Model output</div>
          <div class="lab-output" id="labOutput"></div>
        </div>
      </div>
    </div>

    <section class="lp-round" aria-label="How a round works">
      <ol class="lp-steps">
        <li>
          <span class="lp-step-n">1</span>
          <h2>Wait for the start</h2>
          <p>Every team’s arena opens at the same moment, when the director starts the round.</p>
        </li>
        <li>
          <span class="lp-step-n">2</span>
          <h2>Fix five prompts, in order</h2>
          <p>Your set is unique to your team. Rewrite each prompt and add a note on what you changed.</p>
        </li>
        <li>
          <span class="lp-step-n">3</span>
          <h2>Lock each one</h2>
          <p>A locked prompt is final and timestamped. When scores tie, the earlier finish wins.</p>
        </li>
      </ol>
      <p class="lp-rubric">
        Judges score every prompt out of 100, with 20 points each for clarity, specificity,
        context, output format, and constraints.
      </p>
    </section>
  `;

  document.getElementById('btnLandingLogin')?.addEventListener('click', () => {
    if (store.isAuthenticated()) {
      warpWormhole(0.8);
      Router.navigate('arena-workspace');
    } else {
      Router.navigate('team-lobby');
    }
  });

  startLab(container, myRun);
}

/* ---------------------------------------------------------------------------
   The looping demo
   --------------------------------------------------------------------------- */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function startLab(container, myRun) {
  const lab = container.querySelector('#lab');
  const statusEl = container.querySelector('#labStatus');
  const promptEl = container.querySelector('#labPrompt');
  const outEl = container.querySelector('#labOutput');
  const tagEls = Object.fromEntries([...container.querySelectorAll('.lab-tags li')].map(li => [li.dataset.tag, li]));
  if (!lab) return;

  const alive = () => myRun === runId && container.isConnected;

  // Don't burn cycles while the visitor is on another page
  const waitVisible = async () => {
    while (alive() && !container.classList.contains('active')) await sleep(400);
  };

  const setState = (state, text) => {
    lab.dataset.state = state;
    statusEl.textContent = text;
  };

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) {
    // No animation: show the repaired result with every tag lit.
    promptEl.innerHTML = FIXED_SEGMENTS.map(segmentHtml).join('');
    outEl.innerHTML = FIXED_OUTPUT.map(l => `<p>${l}</p>`).join('');
    Object.values(tagEls).forEach(el => el.classList.add('on'));
    setState('fixed', 'Precise: the model knows the job');
    return;
  }

  while (alive()) {
    await waitVisible();
    if (!alive()) return;

    /* 1 — the broken prompt */
    Object.values(tagEls).forEach(el => el.classList.remove('on'));
    promptEl.textContent = '';
    outEl.textContent = '';
    outEl.className = 'lab-output';
    setState('idle', 'Reading the prompt');
    await sleep(500);

    for (const ch of BROKEN_PROMPT) {
      if (!alive()) return;
      promptEl.textContent += ch;
      await sleep(48);
    }
    await sleep(350);

    /* 2 — generic output */
    setState('broken', 'Vague: the model has to guess');
    outEl.classList.add('is-generic');
    for (const w of BROKEN_OUTPUT.split(' ')) {
      if (!alive()) return;
      outEl.textContent += (outEl.textContent ? ' ' : '') + w;
      await sleep(26);
    }
    await sleep(1800);

    /* 3 — rewrite, one segment at a time */
    setState('fixing', 'Rewriting');
    promptEl.classList.add('is-clearing');
    await sleep(380);
    promptEl.classList.remove('is-clearing');
    promptEl.innerHTML = '';
    outEl.classList.add('is-dim');

    for (const seg of FIXED_SEGMENTS) {
      const span = document.createElement('span');
      if (seg.tag) span.className = `seg seg-${seg.tag}`;
      promptEl.appendChild(span);
      for (const ch of seg.text) {
        if (!alive()) return;
        span.textContent += ch;
        await sleep(13);
      }
      if (seg.tag) tagEls[seg.tag]?.classList.add('on');
      await sleep(180);
    }
    await sleep(300);

    /* 4 — precise output */
    outEl.className = 'lab-output';
    outEl.textContent = '';
    for (const line of FIXED_OUTPUT) {
      const p = document.createElement('p');
      outEl.appendChild(p);
      for (const w of line.split(' ')) {
        if (!alive()) return;
        p.textContent += (p.textContent ? ' ' : '') + w;
        await sleep(30);
      }
    }
    setState('fixed', 'Precise: the model knows the job');
    await sleep(4200);
  }
}

function segmentHtml(seg) {
  return seg.tag ? `<span class="seg seg-${seg.tag}">${seg.text}</span>` : `<span>${seg.text}</span>`;
}
