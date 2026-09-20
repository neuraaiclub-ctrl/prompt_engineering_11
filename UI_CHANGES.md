# NEURA Platform — UI Overhaul & Fixes

## 1. Theme Overhaul (Maroon & Purple)
The entire platform's color palette has been transitioned from the default blue/cyan cyber-theme to a **Cyber-Technical Maroon and Purple** aesthetic.
- Global CSS variables in `styles/neura-core.css` and `styles/neura-shell.css` were updated to reflect deep maroon backgrounds, vibrant purple highlights, and harmonious dark tones.
- Replaced harsh stark white and generic cyan accents with nuanced, rich gradients that feel premium and modern.
- All buttons, chips, and interactive states now utilize this unified `Maroon/Purple` palette.

## 2. Dynamic 3D Wormhole Background
The original static particle background was entirely replaced with a **high-performance, dynamic 3D Wormhole Engine** (`js/components/wormhole.js`).
- Features a mathematically accurate 3D perspective projection of a deep cyber-tunnel.
- The tunnel rings oscillate between maroon and purple, creating a dynamic flow.
- Replaced the "meteor trails" with a **Cylindrical Pulse** effect that spawns behind the camera (at its largest diameter) and travels deep into the vanishing point, naturally condensing as it fades out.
- The screen remains dark (80% opacity overlay) until the cylinder passes through, revealing the glowing wireframe grid via cubic proximity glow.
- **Extreme Optimization:** Engineered to run flawlessly by forcing `dpr = 1` (letting the GPU hardware handle scaling) and pre-calculating expensive math per depth-tier rather than per-vertex. This completely eliminated all lag and FPS drops on high-DPI screens.

## 3. Dynamic Dashboard Fixes
The dashboards were updated to successfully pull and render live dynamic data from the backend rather than static mock fallbacks.
- **Crash Fix:** Patched a `TypeError` in the Arena Workspace that crashed the UI when switching views.
- **Judge Dashboard Alignment:** Fixed the `judge-dashboard.js` frontend to correctly map to the backend's `get_judge_overview` JSON schema. 
  - Aligned `challenge_title` -> `prompt_title`
  - Aligned `flawed_prompt` -> `original_bad_prompt`
  - Aligned `fixed_prompt` -> `submitted_prompt`
  - Aligned `is_evaluated` -> `has_evaluated`
- **Timestamp Parsing Bug:** Fixed an issue where the backend returned a time string (`"HH:MM:SS"`) but the frontend attempted to instantiate a full `new Date()`, resulting in `Invalid Date` and breaking the render cycle.
- **Cache Busting:** Hardcoded the asset requests in `index.html` to append `?v=15` to ensure the browser strictly fetches the latest frontend changes and prevents stale caching.

## How to Run

1. **Start the Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   python run.py
   ```
2. **Start the Frontend:**
   Open a new terminal in the root directory:
   ```bash
   python -m http.server 5500
   ```
3. **Access the App:**
   Open your browser to `http://localhost:5500`.

*(Alternatively, you can run the entire stack using `docker-compose up --build`)*
