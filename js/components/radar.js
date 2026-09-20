/* ==========================================================================
   NEURA RADAR
   A five-axis chart for the five judging criteria. Used in two places:
     - the editor, as a live "coverage" read of the draft
     - the results report, as the team's average judge score
   Values are 0..1. Changes tween so the shape moves instead of snapping.
   ========================================================================== */

export const CRITERIA = [
  { key: 'clarity',      label: 'Clarity' },
  { key: 'specificity',  label: 'Specificity' },
  { key: 'context',      label: 'Context' },
  { key: 'output_format', label: 'Output format' },
  { key: 'constraints',  label: 'Constraints' }
];

const VB_W = 300, VB_H = 264;
const CX = 150, CY = 138, R = 86;

const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / 5;
const pt = (i, frac) => [CX + Math.cos(angle(i)) * R * frac, CY + Math.sin(angle(i)) * R * frac];
const poly = (fracs) => fracs.map((f, i) => pt(i, f).map(n => n.toFixed(1)).join(',')).join(' ');

/**
 * Mount a radar into `el`.
 * @param {HTMLElement} el
 * @param {{ values?: number[], tone?: 'cyan'|'green', title?: string }} opts
 * @returns {{ set(values:number[]): void }}
 */
export function mountRadar(el, opts = {}) {
  const tone = opts.tone || 'cyan';
  const start = opts.values || [0, 0, 0, 0, 0];
  const uid = 'rd' + Math.random().toString(36).slice(2, 7);

  const rings = [0.25, 0.5, 0.75, 1].map(f => `<polygon points="${poly([f, f, f, f, f])}" class="rd-ring"/>`).join('');
  const spokes = CRITERIA.map((_, i) => {
    const [x, y] = pt(i, 1);
    return `<line x1="${CX}" y1="${CY}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" class="rd-spoke"/>`;
  }).join('');

  const labels = CRITERIA.map((c, i) => {
    const [x, y] = pt(i, 1.2);
    const anchor = Math.abs(x - CX) < 6 ? 'middle' : x > CX ? 'start' : 'end';
    const dy = y > CY + 4 ? 10 : y < CY - 4 ? 0 : 4;
    return `<text x="${x.toFixed(1)}" y="${(y + dy).toFixed(1)}" text-anchor="${anchor}" class="rd-label" data-i="${i}">${c.label}</text>`;
  }).join('');

  el.innerHTML = `
    <svg class="radar radar-${tone}" viewBox="0 0 ${VB_W} ${VB_H}" role="img" aria-label="${opts.title || 'Coverage across the five judging criteria'}">
      <defs>
        <radialGradient id="${uid}-fill" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.08"/>
          <stop offset="100%" stop-color="currentColor" stop-opacity="0.34"/>
        </radialGradient>
      </defs>
      <g>${rings}${spokes}</g>
      <polygon class="rd-shape" points="${poly(start)}" fill="url(#${uid}-fill)"/>
      <g class="rd-dots">${start.map((f, i) => { const [x, y] = pt(i, f); return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" class="rd-dot"/>`; }).join('')}</g>
      ${labels}
    </svg>
  `;

  const shape = el.querySelector('.rd-shape');
  const dots = [...el.querySelectorAll('.rd-dot')];
  const labelEls = [...el.querySelectorAll('.rd-label')];

  let current = start.slice();
  let raf = 0;

  const paint = (vals) => {
    shape.setAttribute('points', poly(vals));
    vals.forEach((f, i) => {
      const [x, y] = pt(i, f);
      dots[i].setAttribute('cx', x.toFixed(1));
      dots[i].setAttribute('cy', y.toFixed(1));
    });
  };

  return {
    set(next) {
      const target = next.map(v => Math.max(0, Math.min(1, v)));
      labelEls.forEach((l, i) => l.classList.toggle('on', target[i] >= 0.6));

      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      cancelAnimationFrame(raf);
      if (reduce) { current = target; paint(current); return; }

      const from = current.slice();
      const t0 = performance.now();
      const dur = 420;
      const tick = (now) => {
        const k = Math.min(1, (now - t0) / dur);
        const e = 1 - Math.pow(1 - k, 3);
        current = from.map((f, i) => f + (target[i] - f) * e);
        paint(current);
        if (k < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    }
  };
}
