/* ==========================================================================
   NEURA WORMHOLE BACKGROUND
   A perspective grid tunnel in near-darkness. A single glowing cylinder
   sweeps through every ~4 seconds, illuminating the grid around it as it
   passes — like a searchlight revealing the tunnel geometry.

   Public API
     initWormhole(canvas?)        start the loop
     setWormholeMood(name)        'calm' | 'focus' | 'dim'
     warpWormhole(strength = 1)   one-shot speed/hyperspace surge
   ========================================================================== */

const TAU = Math.PI * 2;

const MOODS = {
  calm:  { alpha: 0.72, speed: 1.0,  core: 1.0 },
  focus: { alpha: 0.32, speed: 0.55, core: 0.5 },
  dim:   { alpha: 0.18, speed: 0.45, core: 0.4 }
};

const CFG = {
  rings:       28,
  railSamples: 36,
  flow:        0.14,
  minScale:    0.005,
  maxScale:    2.2,
  twistFar:    1.5,
  maroon: { far: [200, 120, 140], near: [110, 12, 38]  },
  purple: { far: [175, 115, 220], near: [55,  10, 135] }
};

const SIDES   = 36;
const RAILS   = SIDES;
const POLYGON = Array.from({ length: SIDES }, (_, i) => {
  const a = (i / SIDES) * TAU;
  const denom = 1 + Math.sin(a) * Math.sin(a);
  const x = (1.5 * Math.cos(a)) / denom;
  const y = (1.5 * Math.sin(a) * Math.cos(a)) / denom * 1.2; 
  return [x, y];
});

let canvas, ctx;
let W = 0, H = 0, dpr = 1;
let raf = 0, last = 0, t = 10;
let phase = 0, surge = 0;
let mood = { ...MOODS.calm }, moodTarget = MOODS.calm;
let px = 0, py = 0, tpx = 0, tpy = 0;
let reduceMotion = false;
let running = false;

const smooth = (a, b, x) => {
  const k = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return k * k * (3 - 2 * k);
};
const lerp   = (a, b, k) => a + (b - a) * k;
const fract  = (x) => x - Math.floor(x);
const sizeAt = (u) => CFG.minScale * Math.pow(CFG.maxScale / CFG.minScale, u);

/* ==========================================================================
   SINGLE CYLINDER PULSE — spawns every INTERVAL seconds, slides from
   deep in the tunnel toward the viewer, then resets.
   ========================================================================== */
const CYL = {
  DEPTH:        0.16,
  SPEED:        0.22,
  INTERVAL:     4.2,
  LIGHT_RADIUS: 0.26,

  FADE_IN_DUR:    0.95,  // seconds to fade in from spawn
  FADE_OUT_START: 0.30,  // u_front value at which fade-out begins
  FADE_OUT_DUR:   1.05,  // seconds to fade out

  active:    false,
  u_back:    0,
  cooldown:  1.5,
  bright:    1.0,
  opacity:   0,         // master fade multiplier — 0 (invisible) → 1 (full)
  fadingIn:  false,
  fadingOut: false,
};

function spawnCylinder() {
  CYL.active    = true;
  CYL.u_back    = 1.15;    // Spawn outside the screen (largest diameter)
  CYL.bright    = 0.82 + Math.random() * 0.18;
  CYL.opacity   = 0;
  CYL.fadingIn  = true;
  CYL.fadingOut = false;
}

/* ==========================================================================
   FRAME LOOP
   ========================================================================== */
function frame(now) {
  raf = requestAnimationFrame(frame);
  const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
  last = now;
  step(dt);
  draw();
}

function step(dt) {
  const k = 1 - Math.exp(-dt * 2.2);
  mood.alpha = lerp(mood.alpha, moodTarget.alpha, k);
  mood.speed = lerp(mood.speed, moodTarget.speed, k);
  mood.core  = lerp(mood.core,  moodTarget.core,  k);

  t     += dt * mood.speed;
  phase += (CFG.flow + surge * 1.5) * dt * (0.5 + 0.5 * mood.speed);

  surge *= Math.exp(-dt * 1.2);
  if (surge < 0.002) surge = 0;

  px = lerp(px, tpx, 1 - Math.exp(-dt * 3));
  py = lerp(py, tpy, 1 - Math.exp(-dt * 3));

  if (CYL.active) {
    // Travel INTO the screen (u decreases from 1.15 -> 0)
    CYL.u_back -= CYL.SPEED * dt * mood.speed;
    const u_front = CYL.u_back - CYL.DEPTH; // Front face is deeper inside

    // Phase 1 — Fade in: opacity ramps 0 → 1 as it enters the screen
    if (CYL.fadingIn) {
      CYL.opacity = Math.min(1, CYL.opacity + dt / CYL.FADE_IN_DUR);
      if (CYL.opacity >= 1) { CYL.opacity = 1; CYL.fadingIn = false; }
    }

    // Phase 3 — Fade out: begins when front face reaches deep tunnel
    if (!CYL.fadingOut && !CYL.fadingIn && u_front < 0.25) {
      CYL.fadingOut = true;
    }
    if (CYL.fadingOut) {
      CYL.opacity = Math.max(0, CYL.opacity - dt / CYL.FADE_OUT_DUR);
      if (CYL.opacity <= 0) {
        CYL.active   = false;
        CYL.cooldown = CYL.INTERVAL;
      }
    }
  } else {
    CYL.cooldown -= dt;
    if (CYL.cooldown <= 0) spawnCylinder();
  }
}

// 0→1→0 oscillation — maroon→purple→maroon every ~22 s
function colorCycle() {
  return 0.5 - 0.5 * Math.cos(t * 0.285);
}

/* ==========================================================================
   DRAW
   ========================================================================== */
function draw() {
  ctx.clearRect(0, 0, W, H);

  const boost = 1 + surge * 1.2;
  const A     = mood.alpha * boost;

  const cxBase = W / 2 + px * W * 0.04;
  const cyBase = H / 2 + py * H * 0.04;
  const pulse  = 1 + surge * 0.15;
  const spin   = t * 0.12;

  const angleAt = (u) => {
    const far = Math.pow(1 - u, 1.5);
    return spin + far * CFG.twistFar * (1 + 0.2 * Math.sin(t * 0.4));
  };

  const getCenterOffset = (u) => {
    const z = 1 - u;
    return [
      cxBase + Math.sin(z * 3.5 + t * 0.6) * W * 0.35 * Math.pow(z, 1.2),
      cyBase + Math.cos(z * 2.8 + t * 0.5) * H * 0.35 * Math.pow(z, 1.2),
    ];
  };

  const projectRing = (u, scale = 1.0) => {
    const k  = sizeAt(u) * pulse * scale;
    const a  = angleAt(u);
    const ca = Math.cos(a), sa = Math.sin(a);
    const [ccx, ccy] = getCenterOffset(u);
    const hw = W / 2, hh = H / 2;
    return POLYGON.map(([x, y]) => {
      const rx = x * hw * k;
      const ry = y * hh * k;
      return [ccx + rx * ca - ry * sa, ccy + rx * sa + ry * ca];
    });
  };

  const envelope = (u) => smooth(0.01, 0.15, u) * (1 - smooth(0.70, 1.0, u));

  // Live palette
  const cp        = colorCycle();
  const colorFar  = CFG.maroon.far.map((v, i)  => Math.round(lerp(v, CFG.purple.far[i],  cp)));
  const colorNear = CFG.maroon.near.map((v, i) => Math.round(lerp(v, CFG.purple.near[i], cp)));

  const color = (u, a) => {
    const r = Math.round(lerp(colorFar[0], colorNear[0], u));
    const g = Math.round(lerp(colorFar[1], colorNear[1], u));
    const b = Math.round(lerp(colorFar[2], colorNear[2], u));
    return `rgba(${r},${g},${b},${a.toFixed(3)})`;
  };

  /* -------------------------------------------------------------------
     CYLINDER LIGHT FUNCTION
     Returns 0→1 based on how close depth u is to the cylinder's zone.
     Uses a cubic falloff so the illumination is hottest at the cylinder
     walls and tapers out smoothly beyond its edges.
  ------------------------------------------------------------------- */
  const u_front = CYL.active ? CYL.u_back - CYL.DEPTH : -1;
  const u_back  = CYL.active ? CYL.u_back : -1;
  const cylCenter = (u_front + u_back) * 0.5;

  const cylGlow = (u) => {
    if (!CYL.active || CYL.opacity <= 0) return 0;
    const dist = Math.abs(u - cylCenter);
    const radius = CYL.DEPTH * 0.5 + CYL.LIGHT_RADIUS;
    const t_ = Math.max(0, 1 - dist / radius);
    return t_ * t_ * t_ * CYL.opacity; // cubic falloff × fade state
  };

  /* -------------------------------------------------------------------
     DARKNESS VIGNETTE — keeps the overall scene near-black.
     A dark overlay that dims proportionally to how far the cylinder
     is from center. When cylinder isn't active it's fully dark;
     when cylinder is crossing screen-center it lightens slightly.
  ------------------------------------------------------------------- */
  // How close is the cylinder to mid-depth (u≈0.4)? More "screen-filling" there.
  const screenFillFactor = (CYL.active && CYL.opacity > 0)
    ? Math.max(0, 1 - Math.abs(cylCenter - 0.38) / 0.4) * CYL.opacity
    : 0;
  const darknessAlpha = 0.80 - screenFillFactor * 0.28;
  ctx.fillStyle = `rgba(8,5,9,${darknessAlpha.toFixed(3)})`;
  ctx.fillRect(0, 0, W, H);

  ctx.lineCap  = 'round';
  ctx.lineJoin = 'round';

  /* -------------------------------------------------------------------
     RAILS — longitudinal grid lines.
     Base opacity is ZERO so the infinity shape is only created by the glowing snake!
  ------------------------------------------------------------------- */
  const BASE_RAIL = 0.00; // completely invisible in darkness
  const CYL_RAIL  = 0.90;  // full brightness inside cylinder light cone

  const S    = CFG.railSamples;
  const prev = projectRing(0);
  for (let i = 1; i <= S; i++) {
    const u    = i / S;
    const e    = envelope(u);
    const glow = cylGlow(u);
    const a    = e * (BASE_RAIL + glow * CYL_RAIL * CYL.bright) * A;
    const next = projectRing(u);
    if (a > 0.004) {
      ctx.beginPath();
      for (let j = 0; j < RAILS; j++) {
        ctx.moveTo(prev[j][0], prev[j][1]);
        ctx.lineTo(next[j][0], next[j][1]);
      }
      ctx.strokeStyle = color(u, a);
      ctx.lineWidth   = dpr * (0.8 + u * 1.2) * (1 + glow * 0.8); // lines thicken inside cylinder
      ctx.stroke();
    }
    for (let j = 0; j < RAILS; j++) prev[j] = next[j];
  }

  /* -------------------------------------------------------------------
     RINGS — latitudinal polygons.
     Same darkness-with-illumination treatment. Base is 0.
  ------------------------------------------------------------------- */
  const BASE_RING = 0.00;
  const CYL_RING  = 1.00;

  for (let i = 0; i < CFG.rings; i++) {
    const u    = fract(i / CFG.rings + phase);
    const e    = envelope(u);
    if (e < 0.005) continue;

    const glow = cylGlow(u);
    const ringA = e * (BASE_RING + glow * CYL_RING * CYL.bright) * A;
    if (ringA < 0.004) continue;

    const pts = projectRing(u);
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let j = 1; j < SIDES; j++) ctx.lineTo(pts[j][0], pts[j][1]);
    ctx.closePath();

    const wBase = dpr * (0.8 + Math.pow(u, 1.8) * 1.5) * (1 + glow * 0.6);
    // Outer diffuse
    ctx.lineWidth   = wBase * 3.5;
    ctx.strokeStyle = color(u, ringA * 0.10);
    ctx.stroke();
    // Solid core
    ctx.lineWidth   = wBase;
    ctx.strokeStyle = color(u, ringA);
    ctx.stroke();
  }

  /* -------------------------------------------------------------------
     CYLINDER SHELL
     Four render layers: lit rails inside → interior volume rings →
     leading face (bright) → trailing face (dimmer).
  ------------------------------------------------------------------- */
  if (CYL.active && CYL.opacity > 0) {
    const op  = CYL.opacity;

    const u_f = Math.max(u_front, 0.01);
    const u_b = Math.min(u_back, 1.20);
    if (u_b <= u_f) return;
    if (u_f > 1.05) return; // Entirely behind camera, avoid massive overdraw

    const ef = envelope(u_f);
    const eb = envelope(u_b);

    // Layer 1: Illuminated rails inside the cylinder
    const CYL_SEGS = 16;
    const cylPrev  = projectRing(u_f);
    for (let i = 1; i <= CYL_SEGS; i++) {
      const u       = lerp(u_f, u_b, i / CYL_SEGS);
      const cylNext = projectRing(u);
      if (u > 1.05) {
        for (let j = 0; j < RAILS; j++) cylPrev[j] = cylNext[j];
        continue;
      }
      const t_      = i / CYL_SEGS;
      const edgeness = 1 - Math.sin(t_ * Math.PI) * 0.40;
      const a = CYL.bright * A * op * lerp(ef, eb, t_) * edgeness * 0.68;
      if (a > 0.005) {
        ctx.beginPath();
        for (let j = 0; j < RAILS; j++) {
          ctx.moveTo(cylPrev[j][0], cylPrev[j][1]);
          ctx.lineTo(cylNext[j][0], cylNext[j][1]);
        }
        ctx.strokeStyle = color(u, a);
        ctx.lineWidth   = dpr * (0.8 + u * 1.2) * 2.4;
        ctx.stroke();
      }
      for (let j = 0; j < RAILS; j++) cylPrev[j] = cylNext[j];
    }

    // Layer 2: Interior volume rings
    const INT = 8;
    for (let i = 0; i <= INT; i++) {
      const u   = lerp(u_f, u_b, i / INT);
      if (u > 1.05) continue;
      const e   = envelope(u);
      const pts = projectRing(u);
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let j = 1; j < SIDES; j++) ctx.lineTo(pts[j][0], pts[j][1]);
      ctx.closePath();
      const wBase = dpr * (0.9 + Math.pow(u, 1.8) * 1.5);
      ctx.lineWidth   = wBase * 4;
      ctx.strokeStyle = color(u, e * CYL.bright * A * op * 0.10);
      ctx.stroke();
      ctx.lineWidth   = wBase * 1.1;
      ctx.strokeStyle = color(u, e * CYL.bright * A * op * 0.32);
      ctx.stroke();
    }

    // Layer 3: Leading face — 3-pass (halo / bloom / hot core)
    if (u_f <= 1.05) {
      const ptsF = projectRing(u_f);
      ctx.beginPath();
      ctx.moveTo(ptsF[0][0], ptsF[0][1]);
      for (let j = 1; j < SIDES; j++) ctx.lineTo(ptsF[j][0], ptsF[j][1]);
      ctx.closePath();
      const wF = dpr * (1.2 + Math.pow(u_f, 1.8) * 2.2);
      ctx.lineWidth   = wF * 9;
      ctx.strokeStyle = color(u_f, ef * CYL.bright * A * op * 0.10);
      ctx.stroke();
      ctx.lineWidth   = wF * 4;
      ctx.strokeStyle = color(u_f, ef * CYL.bright * A * op * 0.30);
      ctx.stroke();
      ctx.lineWidth   = wF * 0.9;
      ctx.strokeStyle = color(u_f, ef * CYL.bright * A * op * 0.88);
      ctx.stroke();
    }

    // Layer 4: Trailing face — 2-pass (diffuse + solid)
    if (u_b <= 1.05) {
      const ptsB = projectRing(u_b);
      ctx.beginPath();
      ctx.moveTo(ptsB[0][0], ptsB[0][1]);
      for (let j = 1; j < SIDES; j++) ctx.lineTo(ptsB[j][0], ptsB[j][1]);
      ctx.closePath();
      const wB = dpr * (1.2 + Math.pow(u_b, 1.8) * 2.2);
      ctx.lineWidth   = wB * 5;
      ctx.strokeStyle = color(u_b, eb * CYL.bright * A * op * 0.12);
      ctx.stroke();
      ctx.lineWidth   = wB * 0.9;
      ctx.strokeStyle = color(u_b, eb * CYL.bright * A * op * 0.50);
      ctx.stroke();
    }
  }
  ctx.restore();
}

/* ==========================================================================
   RESIZE / INIT / LIFECYCLE
   ========================================================================== */
function resize() {
  dpr           = 1; // Force 1x resolution to prevent massive lag on high-DPI screens
  W             = Math.floor(window.innerWidth);
  H             = Math.floor(window.innerHeight);
  canvas.width  = W;
  canvas.height = H;
  if (reduceMotion || !running) draw();
}

function start() {
  if (running) return;
  running = true;
  last = performance.now();
  raf  = requestAnimationFrame(frame);
}

function stop() {
  running = false;
  cancelAnimationFrame(raf);
}

export function initWormhole(target) {
  canvas = target || document.getElementById('wormhole');
  if (!canvas) return;
  ctx = canvas.getContext('2d');

  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  reduceMotion = mq.matches;
  mq.addEventListener?.('change', (e) => {
    reduceMotion = e.matches;
    reduceMotion ? (stop(), draw()) : start();
  });

  window.addEventListener('resize', resize);
  window.addEventListener('pointermove', (e) => {
    tpx = (e.clientX / window.innerWidth  - 0.5) * 2;
    tpy = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop();
    else if (!reduceMotion) start();
  });

  resize();
  if (reduceMotion) draw();
  else start();
}

export function setWormholeMood(name = 'calm') {
  moodTarget = MOODS[name] || MOODS.calm;
  if (reduceMotion && ctx) { mood = { ...moodTarget }; draw(); }
}

export function warpWormhole(strength = 1) {
  if (reduceMotion) return;
  surge = Math.max(surge, Math.min(2, strength));
}
