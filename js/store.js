/* ==========================================================================
   NEURA STORE & DATA MANAGEMENT
   Prompt Engineering Hackathon Platform
   ========================================================================== */

import { apiClient, API_BASE_URL } from './services/api-client.js';

const STORAGE_KEY = 'NEURA_HACKATHON_STATE_V2';

const INITIAL_SEED_DATA = {
  activeRole: 'participant', // 'participant' | 'team_leader' | 'judge' | 'admin' | 'spectator'
  token: null,
  isAuthenticated: false,
  currentUser: {
    id: 'usr-001',
    name: 'Alex Mercer',
    email: 'alex@neuralninjas.io',
    teamId: 'team-01',
    role: 'team_leader'
  },
  hackathon: {
    id: 'hk-2026',
    title: 'NEURA Prompt Engineering Hackathon 2026',
    status: 'active',
    activeRound: 1, // 1 or 2
    timerSeconds: 180, // 3 minutes
    isTimerRunning: true
  },
  teams: [
    { id: 'team-01', name: 'Neural Ninjas', inviteCode: 'NR-4827', status: 'locked', members: ['Alex Mercer', 'Elena Rostova', 'Kaelen Vance', 'Sora T.'] },
    { id: 'team-02', name: 'Code Warriors', inviteCode: 'CW-1029', status: 'locked', members: ['David Kim', 'Sarah L.', 'Marcus V.'] },
    { id: 'team-03', name: 'Byte Force', inviteCode: 'BF-3049', status: 'locked', members: ['Priya Nair', 'Jonah H.'] },
    { id: 'team-04', name: 'Ghost Protocol', inviteCode: 'GP-9912', status: 'locked', members: ['Aria Stark', 'Chen Wei'] }
  ],
  round1Cases: [
    {
      id: 'r1-case-01',
      title: 'Case 01 — Signal // Archive',
      difficulty: 'medium',
      brokenReason: 'no_format_specified',
      originalPrompt: `Extract the customer key details and sentiment from this feedback transcript immediately. Return it fast.`,
      badOutput: `The customer seems really upset about the delay in shipping. They mentioned their order ID #84920 and said they want a refund if it doesn't arrive by Tuesday. Overall sentiment is very negative.`,
      badOutputScreenshot: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80',
      description: 'The model returns unformatted prose narrative instead of structured, key-value data required by downstream parsers.'
    },
    {
      id: 'r1-case-02',
      title: 'Case 02 — Shattered Circuit',
      difficulty: 'hard',
      brokenReason: 'contradictory',
      originalPrompt: `Summarize the article in exactly 3 bullet points. Be extremely comprehensive and include all 10 historical background events mentioned. Do not exceed 20 words total.`,
      badOutput: `Error: Unable to synthesize 10 historical events in under 20 words across 3 bullet points. Here is a partial summary...`,
      description: 'The prompt sets impossible contradictory length and completeness bounds, causing model failure.'
    }
  ],
  round2Challenges: [
    {
      id: 'r2-chal-01',
      title: 'Challenge 01 — Sentiment Classification under 50 Tokens',
      constraintType: 'max_tokens_50',
      maxTokens: 50,
      taskDescription: 'Classify sarcastic or complex customer product reviews into POSITIVE, NEGATIVE, or NEUTRAL.',
      formatRule: 'Must return exactly one word: POSITIVE, NEGATIVE, or NEUTRAL.'
    },
    {
      id: 'r2-chal-02',
      title: 'Challenge 02 — Structured Extraction with Valid JSON',
      constraintType: 'valid_json_always',
      maxTokens: 120,
      taskDescription: 'Extract entity names, dates, and currency values from unstructured email signatures into JSON format.',
      formatRule: 'Output MUST be valid JSON matching schema: { "name": string, "date": string, "amount": string }'
    }
  ],
  hiddenTestCases: [
    {
      id: 'tc-01',
      challengeId: 'r2-chal-01',
      input: 'Review: "Oh brilliant! Another software patch that completely wiped my settings. Pure genius design."',
      expectedOutput: 'NEGATIVE',
      evalRule: { type: 'exact' }
    },
    {
      id: 'tc-02',
      challengeId: 'r2-chal-01',
      input: 'Review: "Package arrived 2 days early. Packaging was a bit crushed but the device works great."',
      expectedOutput: 'POSITIVE',
      evalRule: { type: 'exact' }
    },
    {
      id: 'tc-03',
      challengeId: 'r2-chal-01',
      input: 'Review: "The colors are fine. Delivery took standard time. Nothing special."',
      expectedOutput: 'NEUTRAL',
      evalRule: { type: 'exact' }
    },
    {
      id: 'tc-04',
      challengeId: 'r2-chal-01',
      input: 'Review: "I loved waiting on hold for 45 minutes just to be disconnected!"',
      expectedOutput: 'NEGATIVE',
      evalRule: { type: 'exact' }
    },
    {
      id: 'tc-05',
      challengeId: 'r2-chal-01',
      input: 'Review: "Item functions exactly as specified in the manual."',
      expectedOutput: 'POSITIVE',
      evalRule: { type: 'exact' }
    },
    {
      id: 'tc-06',
      challengeId: 'r2-chal-02',
      input: 'Signed, John Doe. Sent on October 14, 2026. Total invoice due: $450.00.',
      expectedOutput: '{"name":"John Doe","date":"October 14, 2026","amount":"$450.00"}',
      evalRule: { type: 'json' }
    },
    {
      id: 'tc-07',
      challengeId: 'r2-chal-02',
      input: 'Best regards, Dr. Alice Smith | Timestamp: 11/05/2026 | Wire transfer sent: EUR 1,200',
      expectedOutput: '{"name":"Dr. Alice Smith","date":"11/05/2026","amount":"EUR 1,200"}',
      evalRule: { type: 'json' }
    },
    {
      id: 'tc-08',
      challengeId: 'r2-chal-02',
      input: 'Thanks, Marcus Aurelius - Date: Jan 1st 2026. Refund requested: 75 USD.',
      expectedOutput: '{"name":"Marcus Aurelius","date":"Jan 1st 2026","amount":"75 USD"}',
      evalRule: { type: 'json' }
    },
    {
      id: 'tc-09',
      challengeId: 'r2-chal-02',
      input: 'Warmly, Sarah Connor. Confirmed on 09-07-2026. Balance remaining: $0.00',
      expectedOutput: '{"name":"Sarah Connor","date":"09-07-2026","amount":"$0.00"}',
      evalRule: { type: 'json' }
    },
    {
      id: 'tc-10',
      challengeId: 'r2-chal-02',
      input: 'From: Wayne Enterprises Inc (Bruce Wayne) - Date of service: Dec 25, 2025 - Bill: $5,000',
      expectedOutput: '{"name":"Bruce Wayne","date":"Dec 25, 2025","amount":"$5,000"}',
      evalRule: { type: 'json' }
    }
  ],
  promptVersions: [
    {
      id: 'ver-01',
      caseId: 'r1-case-01',
      teamId: 'team-01',
      versionNumber: 1,
      promptText: `Extract the customer key details and sentiment from this feedback transcript immediately. Return it fast.`,
      explanation: `Original baseline prompt provided by organizers.`,
      isFinal: false,
      timestamp: '10:14:02'
    },
    {
      id: 'ver-02',
      caseId: 'r1-case-01',
      teamId: 'team-01',
      versionNumber: 2,
      promptText: `Analyze the customer feedback transcript. Extract: 1. Order ID 2. Customer Request 3. Overall Sentiment (Positive/Negative/Neutral). Return as bullet points.`,
      explanation: `Added explicit numbered field list to eliminate rambling narrative prose.`,
      isFinal: false,
      timestamp: '10:22:15'
    },
    {
      id: 'ver-03',
      caseId: 'r1-case-01',
      teamId: 'team-01',
      versionNumber: 3,
      promptText: `You are an automated customer analytics parser. Read the feedback below and output ONLY a valid JSON object with keys: "orderId", "customerRequest", "sentiment". Do not include Markdown or extra commentary.`,
      explanation: `Assigned role context and enforced strict JSON output schema for API integration.`,
      isFinal: true,
      timestamp: '10:35:40'
    }
  ],
  submissions: [
    {
      id: 'sub-r1-t1',
      round: 1,
      caseId: 'r1-case-01',
      teamId: 'team-01',
      finalPromptVersionId: 'ver-03',
      promptText: `You are an automated customer analytics parser. Read the feedback below and output ONLY a valid JSON object with keys: "orderId", "customerRequest", "sentiment". Do not include Markdown or extra commentary.`,
      explanation: `Assigned role context and enforced strict JSON output schema for API integration.`,
      submittedAt: '10:35:40',
      status: 'locked'
    }
  ],
  evaluations: [
    {
      id: 'eval-r1-t1',
      submissionId: 'sub-r1-t1',
      judgeId: 'judge-vance',
      judgeName: 'Dr. Vance',
      scores: {
        diagnosisQuality: 5,
        improvementQuality: 4,
        finalOutputQuality: 5,
        documentationClarity: 5
      },
      comment: 'Excellent diagnosis of missing format specification. The step-by-step iteration was methodical and clearly documented.',
      timestamp: '10:48:00'
    }
  ]
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
      // Offline fallback: Check against seeded mock identities for offline dev resilience
      console.warn('Backend offline or unreachable, using local fallback:', e);
      const lower = email.trim().toLowerCase();
      if (lower.includes('admin')) {
        this.data.activeRole = 'admin';
        this.data.currentUser = { id: 'usr-admin', name: 'Director Vance (Admin)', email: lower, roles: ['admin'] };
        this.data.isAuthenticated = true;
        this.saveState();
        return { success: true, role: 'admin', user: this.data.currentUser };
      } else if (lower.includes('judge')) {
        this.data.activeRole = 'judge';
        this.data.currentUser = { id: 'usr-judge', name: 'Dr. Vance (Judge)', email: lower, roles: ['judge'] };
        this.data.isAuthenticated = true;
        this.saveState();
        return { success: true, role: 'judge', user: this.data.currentUser };
      } else {
        const team = this.data.teams.find(t => t.inviteCode.toUpperCase() === email.toUpperCase() || t.name.toLowerCase() === lower);
        if (team) {
          this.data.activeRole = 'participant';
          this.data.currentUser = { id: 'usr-team', name: team.name, email: `${team.name.toLowerCase().replace(/\s+/g, '.')}@neura.io`, teamId: team.id, roles: ['participant'] };
          this.data.isAuthenticated = true;
          this.saveState();
          return { success: true, role: 'participant', user: this.data.currentUser };
        }
      }
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
    return this.data.teams.map(t => ({
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

  calculateLeaderboard() {
    return this.data.teams.map(team => {
      const teamSubs = this.data.submissions.filter(s => s.teamId === team.id && s.id !== 'sub-r2-t1');

      let caseScore = 0;

      if (teamSubs.length > 0) {
        let totalCaseScores = 0;
        for (const sub of teamSubs) {
          const evals = this.data.evaluations.filter(e => e.submissionId === sub.id);
          if (evals.length > 0) {
            const sum = evals.reduce((acc, ev) => acc + (
              (ev.scores?.diagnosisQuality || 0) +
              (ev.scores?.improvementQuality || 0) +
              (ev.scores?.finalOutputQuality || 0) +
              (ev.scores?.documentationClarity || 0)
            ), 0);
            totalCaseScores += (sum / evals.length);
          } else {
            totalCaseScores += 15; // default benchmark
          }
        }
        caseScore = totalCaseScores / teamSubs.length;
      }

      const totalScore = caseScore;
      const solved = teamSubs.length;
      const totalChallenges = (this.data.round1Cases?.length || 2);

      return {
        teamId: team.id,
        teamName: team.name,
        caseScore: caseScore.toFixed(1),
        r1Score: caseScore.toFixed(1),
        r2Score: '0.0',
        totalScore: totalScore.toFixed(1),
        solved: `${solved}/${totalChallenges}`,
        r2Passed: `${solved}/${totalChallenges}`
      };
    }).sort((a, b) => parseFloat(b.totalScore) - parseFloat(a.totalScore));
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
      console.warn('Backend arena/status unavailable, using fallback:', e);
    }
    return {
      status: this.data.arenaStatus || 'waiting',
      active_round: 1,
      total_challenges: 5,
      is_results_released: false
    };
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
      this.data.arenaStatus = 'live';
      this.saveState();
      return { success: true, status: 'live' };
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
      this.data.arenaStatus = 'completed';
      this.saveState();
      return { success: true, status: 'completed' };
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
      this.data.arenaResultsReleased = true;
      this.saveState();
      return { success: true, status: 'results_available' };
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
        return await resp.json();
      }
    } catch (e) {
      console.warn('Backend leaderboard unreachable:', e);
    }
    return [];
  }
}

export const store = new Store();
