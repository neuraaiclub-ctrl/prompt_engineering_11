/* ==========================================================================
   NEURA STORE & DATA MANAGEMENT
   Prompt Engineering Hackathon Platform
   ========================================================================== */

import { apiClient, API_BASE_URL } from './services/api-client.js';

const STORAGE_KEY = 'NEURA_HACKATHON_STATE_V3';

const INITIAL_SEED_DATA = {
  activeRole: 'participant',
  token: null,
  isAuthenticated: false,
  currentUser: null,
  hackathon: {
    id: 'hk-2026',
    title: 'NEURA Prompt Engineering Hackathon 2026',
    status: 'active',
    activeRound: 1,
    timerSeconds: 180,
    isTimerRunning: true
  },
  teams: [],
  round1Cases: [],
  round2Challenges: [],
  hiddenTestCases: [],
  promptVersions: [],
  submissions: [],
  evaluations: []
};

class Store {
  constructor() {
    this.data = this.loadState();
    apiClient.setTokenGetter(() => this.data?.token);
    apiClient.setOnUnauthorized(() => this.logout());
  }

  loadState() {
    const saved = localStorage.getItem(STORAGE_KEY) || localStorage.getItem('NEURA_HACKATHON_STATE_V1');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed.submissions)) {
          parsed.submissions = parsed.submissions.filter(s => s.id !== 'sub-r2-t1');
        }
        if (Array.isArray(parsed.evaluations)) {
          parsed.evaluations = parsed.evaluations.filter(e => e.submissionId !== 'sub-r2-t1');
        }
        return parsed;
      } catch (e) {
        console.error('Failed to parse saved state, resetting to initial seed data.', e);
      }
    }
    return JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  }

  saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
  }

  resetToDefaults() {
    this.data = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
    this.saveState();
  }

  // Getters
  getRole() { return this.data.activeRole || 'participant'; }
  setRole(role) { this.data.activeRole = role; this.saveState(); }

  isAuthenticated() { return !!this.data.isAuthenticated; }
  setAuthenticated(val) { this.data.isAuthenticated = !!val; this.saveState(); }

  getToken() { return this.data.token; }

  getAuthHeaders() {
    const token = this.getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async loginWithCredentials(email, password) {
    try {
      const resp = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password })
      });

      if (resp.ok) {
        const data = await resp.json();
        const roles = data.user?.roles || [];
        const role = roles.includes('admin') ? 'admin'
                   : roles.includes('judge') ? 'judge'
                   : 'participant';

        this.data.token = data.access_token;
        this.data.currentUser = data.user;
        this.data.activeRole = role;
        this.data.isAuthenticated = true;
        this.saveState();

        return { success: true, role, user: data.user, token: data.access_token };
      } else {
        const errData = await resp.json().catch(() => ({}));
        return { success: false, error: errData.detail || 'Invalid email or password' };
      }
    } catch (e) {
      console.warn('Backend offline or unreachable:', e);
      return { success: false, error: 'Could not connect to backend server. Please verify FastAPI is running.' };
    }
  }

  logout() {
    this.data.token = null;
    this.data.isAuthenticated = false;
    this.data.activeRole = 'participant';
    this.data.currentUser = {
      id: 'guest',
      name: 'Guest User',
      email: '',
      roles: ['participant']
    };
    this.saveState();
  }

  async adminRegisterTeam(payload) {
    try {
      const resp = await fetch(`${API_BASE_URL}/teams/admin/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': this.data.token ? `Bearer ${this.data.token}` : ''
        },
        body: JSON.stringify(payload)
      });

      if (resp.ok) {
        const resData = await resp.json();
        // Sync to local store teams
        const registered = resData.team;
        this.data.teams.unshift({
          id: registered.id,
          name: registered.name,
          college: registered.college,
          inviteCode: registered.invite_code,
          status: registered.status,
          members: registered.members,
          loginEmail: registered.login_email
        });
        this.saveState();
        return { success: true, data: resData };
      } else {
        const errData = await resp.json().catch(() => ({}));
        return { success: false, error: errData.detail || 'Team registration failed.' };
      }
    } catch (e) {
      console.warn('Backend unreachable during team registration, applying client-side fallback:', e);
      // Offline fallback
      const teamName = (payload.team_name || '').trim();
      const college = (payload.college || '').trim();
      const members = (payload.members || []).map(m => m.trim()).filter(Boolean);

      if (this.data.teams.some(t => t.name.toLowerCase() === teamName.toLowerCase())) {
        return { success: false, error: `The team name "${teamName}" is already registered.` };
      }

      const cleanSlug = teamName.toLowerCase().replace(/[^a-z0-9]+/g, '.').replace(/^\.+|\.+$/g, '');
      const genEmail = `${cleanSlug}@neura.io`;
      const genPass = 'Nr-' + Math.random().toString(36).slice(-8) + '!';
      const newTeam = {
        id: 'team-' + Date.now(),
        name: teamName,
        college,
        inviteCode: 'NR-' + Math.floor(1000 + Math.random() * 9000),
        status: 'forming',
        members,
        loginEmail: genEmail
      };
      this.data.teams.unshift(newTeam);
      this.saveState();

      return {
        success: true,
        data: {
          team: newTeam,
          credentials: { email: genEmail, password: genPass }
        }
      };
    }
  }

  async getAdminTeams() {
    try {
      const resp = await fetch(`${API_BASE_URL}/teams/admin/all`, {
        headers: {
          'Authorization': this.data.token ? `Bearer ${this.data.token}` : ''
        }
      });
      if (resp.ok) {
        const teams = await resp.json();
        return teams;
      }
    } catch (e) {
      // fallback to store
    }
    return (this.data.teams || []).map(t => ({
      id: t.id,
      name: t.name,
      college: t.college || 'MMCOE Pune',
      invite_code: t.inviteCode,
      status: t.status,
      members: t.members,
      members_count: t.members.length,
      login_email: t.loginEmail || `${t.name.toLowerCase().replace(/\s+/g, '.')}@neura.io`
    }));
  }

  getHackathon() { return this.data.hackathon; }
  getTeams() { return this.data.teams; }
  
  getRound1Cases() { return this.data.round1Cases; }
  getRound2Challenges() { return this.data.round2Challenges; }
  
  getVersionsForCase(caseId, teamId) {
    return this.data.promptVersions.filter(v => v.caseId === caseId && v.teamId === teamId);
  }

  getSubmission(caseOrChalId, teamId) {
    return this.data.submissions.find(s => (s.caseId === caseOrChalId || s.challengeId === caseOrChalId) && s.teamId === teamId);
  }

  // Mutations
  addPromptVersion(caseId, teamId, promptText, explanation) {
    const versions = this.getVersionsForCase(caseId, teamId);
    const nextVer = versions.length + 1;
    const newVer = {
      id: 'ver-' + Date.now(),
      caseId,
      teamId,
      versionNumber: nextVer,
      promptText,
      explanation,
      isFinal: false,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    this.data.promptVersions.push(newVer);
    this.saveState();
    return newVer;
  }

  markFinalVersion(verId) {
    this.data.promptVersions.forEach(v => {
      if (v.id === verId) v.isFinal = true;
    });
    this.saveState();
  }

  submitRound1(caseId, teamId, finalVersionId) {
    const ver = this.data.promptVersions.find(v => v.id === finalVersionId);
    if (!ver) return null;
    ver.isFinal = true;
    
    const sub = {
      id: 'sub-' + Date.now(),
      round: 1,
      caseId,
      teamId,
      finalPromptVersionId: finalVersionId,
      promptText: ver.promptText,
      explanation: ver.explanation,
      submittedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      status: 'locked'
    };
    this.data.submissions.push(sub);
    this.saveState();
    return sub;
  }

  submitRound2(challengeId, teamId, promptText, explanation, passCount, totalCount, constraintViolated) {
    const sub = {
      id: 'sub-' + Date.now(),
      round: 2,
      challengeId,
      teamId,
      promptText,
      explanation,
      submittedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      status: 'locked',
      passCount,
      totalCount,
      constraintViolated
    };
    this.data.submissions.push(sub);
    this.saveState();
    return sub;
  }

  submitEvaluation(submissionId, judgeId, judgeName, scores, comment) {
    const existingIdx = this.data.evaluations.findIndex(e => e.submissionId === submissionId && e.judgeId === judgeId);
    const evalObj = {
      id: existingIdx >= 0 ? this.data.evaluations[existingIdx].id : 'eval-' + Date.now(),
      submissionId,
      judgeId,
      judgeName,
      scores,
      comment,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    if (existingIdx >= 0) {
      this.data.evaluations[existingIdx] = evalObj;
    } else {
      this.data.evaluations.push(evalObj);
    }
    this.saveState();
    return evalObj;
  }


  getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.data.token) {
      headers['Authorization'] = `Bearer ${this.data.token}`;
    }
    return headers;
  }

  /* ==========================================================================
     PROMPT FIXING ARENA API CLIENT METHODS
     ========================================================================== */

  async getArenaStatus() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/status`, {
        headers: this.getAuthHeaders()
      });
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      return {
        success: false,
        error: 'Connection error. Ensure backend is reachable.'
      };
    }
  }

  async startArena(durationMinutes = 60) {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/start`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ duration_minutes: durationMinutes })
      });
      const data = await resp.json();
      if (resp.ok) {
        this.data.arenaStatus = 'live';
        this.saveState();
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to start arena' };
    } catch (e) {
      return { success: false, error: 'Connection error. Ensure backend is reachable.' };
    }
  }

  async endArena() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/end`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        this.data.arenaStatus = 'completed';
        this.saveState();
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to end arena' };
    } catch (e) {
      return { success: false, error: 'Connection error. Ensure backend is reachable.' };
    }
  }

  async releaseArenaResults() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/release-results`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        this.data.arenaResultsReleased = true;
        this.saveState();
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to release results' };
    } catch (e) {
      return { success: false, error: 'Connection error. Ensure backend is reachable.' };
    }
  }

  async getMyArenaChallenge() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/my-challenge`, {
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to fetch challenge' };
    } catch (e) {
      console.warn('Backend my-challenge offline, fallback challenge:', e);
      return {
        success: false,
        error: 'Backend is offline. Ensure FastAPI is running.'
      };
    }
  }

  async submitArenaChallenge(payload) {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/submit-challenge`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to submit challenge' };
    } catch (e) {
      return { success: false, error: 'Connection error while submitting challenge' };
    }
  }

  async logSecurityEvent(eventType, metadata = {}) {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/security-event`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ event_type: eventType, metadata })
      });
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      // Non-blocking anti-cheat log
      console.warn('Could not report security event:', e);
    }
    return { success: false };
  }

  async getArenaJudgeOverview() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/judge/overview`, {
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to load judge overview' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async scoreArenaSubmission(payload) {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/judge/score`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to score submission' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async getArenaReport() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/report`, {
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to fetch report' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async getArenaLeaderboard() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/leaderboard`, {
        headers: this.getAuthHeaders()
      });
      if (resp.ok) {
        const json = await resp.json();
        return Array.isArray(json) ? json : (json.standings || []);
      }
    } catch (e) {
      return { success: false, error: 'Connection error. Ensure backend is reachable.', standings: [] };
    }
  }

  async eliminateTeam(teamId, reason) {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/judge/eliminate`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ team_id: teamId, reason })
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to eliminate team' };
    } catch (e) {
      return { success: false, error: 'Connection error while eliminating team' };
    }
  }

  async getMyArenaResults() {
    try {
      const resp = await fetch(`${API_BASE_URL}/arena/my-results`, {
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Failed to fetch score dashboard' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  // =========================================================================
  // ADMIN LIVE REGISTRATION MANAGEMENT & SYNC API METHODS
  // =========================================================================

  async getAdminRegistrations(params = {}) {
    const query = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}/admin/registrations${query ? '?' + query : ''}`;
    try {
      const resp = await fetch(url, { headers: this.getAuthHeaders() });
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      console.warn('Backend registrations error:', e);
    }
    return [];
  }

  async getRegistrationStatusSummary() {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/summary`, { headers: this.getAuthHeaders() });
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      console.warn('Backend status summary error:', e);
    }
    return {
      google_sheets_connected: false,
      total_registrations: 0,
      verified: 0,
      pending: 0,
      rejected: 0,
      disabled: 0,
      active_accounts: 0,
      unprovisioned: 0,
      flagged_for_review: 0,
      last_synced_at: null
    };
  }

  async syncGoogleSheetsRegistrations() {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/sync`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Google Sheets sync failed' };
    } catch (e) {
      return { success: false, error: 'Connection error during sync' };
    }
  }

  async importRegistrationsFile(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const headers = {};
      const token = this.getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const resp = await fetch(`${API_BASE_URL}/admin/registrations/import`, {
        method: 'POST',
        headers,
        body: formData
      });
      const data = await resp.json();
      if (resp.ok) {
        return { success: true, ...data };
      }
      return { success: false, error: data.detail || 'Import failed' };
    } catch (e) {
      return { success: false, error: 'Connection error during import' };
    }
  }

  async verifyRegistration(regId, notes = '') {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/${regId}/verify`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ notes })
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Verification failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async rejectRegistration(regId, notes = '') {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/${regId}/reject`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ notes })
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Rejection failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async disableRegistration(regId, notes = '') {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/${regId}/disable`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ notes })
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Disabling failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async provisionRegistrationAccount(regId) {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/${regId}/provision`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Provisioning failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async provisionAllVerifiedRegistrations() {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/provision-all`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Bulk provisioning failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async resetRegistrationCredentials(regId) {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/registrations/${regId}/reset-credentials`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Reset failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async downloadRegistrationsCsv() {
    try {
      const token = this.getToken();
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const resp = await fetch(`${API_BASE_URL}/admin/registrations/export`, { headers });
      if (resp.ok) {
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'neura_registrations_export.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        return { success: true };
      }
      return { success: false, error: 'Export failed' };
    } catch (e) {
      return { success: false, error: 'Connection error during export' };
    }
  }
  // ==========================================
  // PROMPT BANK MANAGEMENT (ADMIN CRUD)
  // ==========================================
  async getPromptBank() {
    try {
      const resp = await fetch(`${API_BASE_URL}/prompt-bank/`, {
        headers: this.getAuthHeaders()
      });
      const data = await resp.json();
      return Array.isArray(data) ? data : [];
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async createPrompt(payload) {
    try {
      const resp = await fetch(`${API_BASE_URL}/prompt-bank/`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, item: data };
      return { success: false, error: data.detail || 'Failed to create prompt' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }

  async updatePrompt(id, payload) {
    try {
      const resp = await fetch(`${API_BASE_URL}/prompt-bank/${id}`, {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, item: data };
      return { success: false, error: data.detail || 'Failed to update prompt' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }
  // ==========================================
  // EXECUTION SANDBOX (PARTICIPANT)
  // ==========================================
  async runTestExecution(user_prompt, system_prompt = null, model = "gpt-4o-mini") {
    try {
      const resp = await fetch(`${API_BASE_URL}/executions/preview`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ user_prompt, system_prompt, model })
      });
      const data = await resp.json();
      if (resp.ok) return { success: true, ...data };
      return { success: false, error: data.detail || 'Execution failed' };
    } catch (e) {
      return { success: false, error: 'Connection error' };
    }
  }
}

export const store = new Store();
