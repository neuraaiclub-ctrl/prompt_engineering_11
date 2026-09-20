# NEURA UI redesign — what changed

## Try it without the backend
Serve the folder (`python -m http.server 5500`) and open:

| URL | Shows |
|---|---|
| `/index.html` | Landing (live prompt-repair demo) |
| `/index.html?demo` or `?demo=live&q=3` | Live challenge (q = 1–5) |
| `/index.html?demo=waiting&autostart` | Stand-by, then the 3‑2‑1 start after ~9s |
| `/index.html?demo=done` | All five locked |
| `/index.html?demo=results` | Released score report |
| `/index.html?demo=eliminated` | Disqualified screen |

Preview mode uses sample data, never touches the API, never writes localStorage.

## New files
- `js/components/wormhole.js` — background tunnel. `setWormholeMood('calm'|'focus'|'dim')`, `warpWormhole(strength)`.
- `js/components/radar.js` — five-axis chart (draft coverage + results).
- `js/utils/prompt-coverage.js` — heuristic behind the coverage radar. Not a score.
- `js/demo/arena-demo.js` — preview data.
- `styles/neura-shell.css`, `neura-gateway.css`, `neura-arena.css`.

## Rewritten
`index.html`, `styles/neura-core.css`, `js/app.js`, `js/router.js`,
`js/views/landing-page.js`, `js/views/auth-team.js`, `js/views/arena-workspace.js`.

## Removed
`js/components/particles.js`, and the dead landing/hourglass/nav blocks in `neura-components.css`.

## Knobs
- `ARENA_UI.showCoverage` in `arena-workspace.js` — set `false` to remove the radar and hints.
- Wormhole speed/density/twist: `CFG` at the top of `wormhole.js`.

## Bugs fixed along the way
- After sign-in the arena still said "access restricted" until refresh (it rendered once at boot). It now re-renders on every entry.
- Signed-out visitors saw another team's roster on the login page.
- Arena rebuilt its DOM every 2.5 s while waiting/completed; each state now renders once.
- `var(--blue)` was undefined; `.btn-red` had no style.

## Not redesigned yet
Judge, Admin, Spectator and legacy Round 1 workspaces inherit the new background, nav, buttons and panels, but their layouts and ALL-CAPS copy are unchanged.

## Worth a look on your side
- `auth-team.js` still passes `'Pass123!'` when the password box is empty (carried over from the original).
- The arena clock reads `remaining_seconds` (or `ends_at`) from `/arena/status`. If the backend doesn't send either, the clock stays hidden rather than guessing.
- `assets/neura-logo.jpg` wasn't in the zip; a letter mark shows if it's missing.
