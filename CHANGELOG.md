# Changelog & Fixes (Last Session)

## 1. Dynamic Datasets & Questions (Backend)
- Added dataset_tag to PromptBankItem (Questions).
- Added ctive_dataset_tag to ArenaConfig.
- Configured prompt assignments to filter questions by ctive_dataset_tag if it's set.
- Ensured a guaranteed **1 Easy, 3 Medium, 1 Hard** prompt distribution per team.
- Added API endpoints for Admin to switch datasets (PUT /arena/config).
- Made the DB migration automatic and backwards compatible via ackend/migrate_db.py and database.py.

## 2. Arena Reset Feature (Backend & Frontend)
- **Problem**: When a test arena was marked 'completed', it caused subsequent player logins to show the 'All 5 prompts locked' completion screen incorrectly.
- **Solution**: Built a complete 'Reset Arena' flow.
- Added POST /arena/reset to the backend. It clears all team sessions, submissions, evaluations, and score data, returning the arena to 'waiting' mode.
- Added a **↺ RESET ARENA** button to the Judge dashboard (js/views/judge-dashboard.js) with a safety confirmation prompt.

## 3. Results / Leaderboard Bug Fixes (Frontend)
- **Problem 1**: Clicking 'View Leaderboard' caused Router.navigate is not a function error.
- **Fix**: Replaced with standard MPA navigation window.location.href = 'live.html'.
- **Problem 2**: Releasing results after a full reset caused the UI to crash trying to display 'undefined of 5 prompts scored'.
- **Fix**: Updated rena-workspace.js to gracefully fall back to a 'No prompts were scored for your team' message if a team has no completed challenges when results are released.

## How to Deploy
1. The frontend (Vercel) automatically deploys when you push to main. (Wait for Vercel to finish).
2. The backend (Render) automatically deploys. (Ensure Render gets the latest).
3. The database schema changes run automatically on startup (database.py issues ALTER TABLE IF EXISTS).
