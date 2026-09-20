/* ==========================================================================
   NEURA ARENA — DEMO MODE
   Lets designers, organisers and QA walk through every arena state without the
   backend running. Nothing here is loaded unless the URL has ?demo.

     ?demo                       live challenge 1
     ?demo=live&q=3              live challenge 3
     ?demo=waiting               stand-by lobby   (add &autostart to see the 3-2-1 start)
     ?demo=done                  all five locked, waiting on judges
     ?demo=results               released score report
     ?demo=eliminated            disqualified screen

   Demo mode never writes to localStorage and never touches the API.
   ========================================================================== */

const CHALLENGES = [
  {
    id: 'demo-1',
    title: 'Support ticket triage',
    category: 'Structured output',
    difficulty: 'medium',
    scenario:
      'A support tool sends every incoming customer message to a model. The result is parsed by code that routes the ticket to the right queue, so the reply has to be machine-readable every single time.',
    flawed_prompt: 'Read this customer message and tell me what’s going on with it and what we should do.'
  },
  {
    id: 'demo-2',
    title: 'Contract clause summary',
    category: 'Contradictory constraints',
    difficulty: 'hard',
    scenario:
      'Legal wants a one-glance summary of each contract. The current prompt asks for two things that cannot both be true, and the model quietly drops whichever it likes.',
    flawed_prompt: 'Summarize this contract in one sentence, but include every obligation, date, and penalty. Keep it under 20 words.'
  },
  {
    id: 'demo-3',
    title: 'Water bottle product page',
    category: 'Vague instructions',
    difficulty: 'easy',
    scenario:
      'An online shop wants a product description for a new insulated bottle. Every run comes back different in length, tone, and claims.',
    flawed_prompt: 'Write something good about our new water bottle.'
  },
  {
    id: 'demo-4',
    title: 'Meeting notes to action items',
    category: 'Missing context',
    difficulty: 'medium',
    scenario:
      'A team pastes raw meeting notes and expects a clean task list for the project board. Owners and deadlines keep getting invented.',
    flawed_prompt: 'Turn these notes into tasks.'
  },
  {
    id: 'demo-5',
    title: 'Top customers query',
    category: 'Missing edge cases',
    difficulty: 'hard',
    scenario:
      'Analysts ask for SQL in plain English. The model has no schema, no dialect, and no idea what “top” means, and it never says so.',
    flawed_prompt: 'Write a query to get top customers.'
  }
];

const RESULT_CHALLENGES = CHALLENGES.map((c, i) => {
  const scores = [
    [16, 14, 12, 18, 14],
    [12, 14, 10, 8, 16],
    [18, 16, 14, 12, 10],
    [14, 12, 16, 16, 12],
    [16, 18, 14, 14, 18]
  ][i];
  const [clarity, specificity, context, output_format, constraints] = scores;
  return {
    challenge_index: i + 1,
    code: `PF-0${i + 1}`,
    title: c.title,
    category: c.category,
    score: scores.reduce((a, b) => a + b, 0),
    submitted_prompt: [
      'You are a support triage assistant. Read the customer message below and return only JSON with the keys "category" (billing | shipping | technical | other), "urgency" (low | medium | high), and "summary" (one sentence). If the message is unclear, use "other" and say why in the summary.',
      'Write a one-paragraph summary of the contract for a non-lawyer. Cover parties, term, payment, and penalties in plain language. If a section is missing, write "not specified" for it. Do not exceed 80 words.',
      'You are a copywriter for an outdoor brand. Write a 60-word product description for an insulated steel bottle for hikers. Mention keeping drinks cold for 24 hours and hot for 12. Friendly tone. No superlatives.',
      'From the meeting notes below, list action items as "Owner — task — due date". If an owner or date was not stated, write "unassigned" or "no date". Do not invent either.',
      'You are a SQL analyst. Using the schema below, write a PostgreSQL query for the 10 customers with the highest total order value in the last 12 months. If two customers tie, order by name. Return only the query.'
    ][i],
    server_timestamp: new Date(Date.now() - (5 - i) * 6 * 60 * 1000).toISOString(),
    characteristics: { clarity, specificity, context, output_format, constraints },
    judge_feedback: [
      'Strong output contract. The unclear-message rule is what lifted this above the average.',
      'Good catch on the contradiction. You resolved it by dropping the one-sentence limit, which is the right call.',
      'Clear and specific, but there is no output format beyond word count.',
      'The “do not invent” rule is excellent. A required output template would make this near perfect.',
      'Precise and safe. Naming the dialect and the tie-break is what most teams missed.'
    ][i]
  };
});

export function installArenaDemo(store) {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('demo') || 'live';
  const startIndex = Math.min(5, Math.max(1, parseInt(params.get('q') || '1', 10) || 1));

  const state = {
    mode: ['waiting', 'live', 'done', 'results', 'eliminated'].includes(mode) ? mode : 'live',
    index: startIndex,
    endsAt: Date.now() + (47 * 60 + 12) * 1000
  };
  if (params.has('autostart') && state.mode === 'waiting') {
    setTimeout(() => { state.mode = 'live'; state.endsAt = Date.now() + 50 * 60 * 1000; }, 9000);
  }

  // Never persist demo sessions
  store.saveState = () => {};
  store.data.token = null;
  store.data.isAuthenticated = true;
  store.data.activeRole = 'participant';
  store.data.currentUser = {
    id: 'demo-team', name: 'Neural Ninjas', email: 'neural.ninjas@neura.io',
    teamId: 'team-01', roles: ['participant']
  };

  const remaining = () => Math.max(0, Math.round((state.endsAt - Date.now()) / 1000));

  store.getArenaStatus = async () => {
    const map = { waiting: 'waiting', live: 'live', done: 'live', results: 'results_available', eliminated: 'eliminated' };
    return {
      status: map[state.mode],
      active_round: 1,
      total_challenges: 5,
      is_results_released: state.mode === 'results',
      remaining_seconds: state.mode === 'live' ? remaining() : null,
      elimination_reason: 'Repeated tab switches during a live prompt were logged and reviewed by the panel.'
    };
  };

  store.getMyArenaChallenge = async () => {
    if (state.mode === 'eliminated') return { success: false, status: 'eliminated', error: 'eliminated' };
    if (state.mode === 'done') {
      return { success: true, is_arena_completed: true, challenge_index: 5, completed_at: new Date().toISOString() };
    }
    return {
      success: true,
      is_arena_completed: false,
      challenge_index: state.index,
      challenge: CHALLENGES[state.index - 1]
    };
  };

  store.submitArenaChallenge = async (payload) => {
    await new Promise(r => setTimeout(r, 700));
    if (state.index >= 5) { state.mode = 'done'; return { success: true, is_arena_completed: true }; }
    state.index += 1;
    return { success: true, is_arena_completed: false };
  };

  store.getMyArenaResults = async () => {
    const total = RESULT_CHALLENGES.reduce((a, c) => a + c.score, 0);
    return {
      success: true,
      team_name: 'Neural Ninjas',
      college: 'MMCOE Pune',
      total_score: total,
      average_score: (total / 5).toFixed(1),
      rank: 2,
      completion_time: new Date().toISOString(),
      challenges: RESULT_CHALLENGES
    };
  };

  store.getArenaReport = async () => ({ success: false });
  store.logSecurityEvent = async () => ({ success: true });

  // Small banner so nobody mistakes a preview for the live event
  const tag = document.createElement('div');
  tag.className = 'demo-flag';
  tag.textContent = 'Preview mode · sample data';
  document.body.appendChild(tag);
}
