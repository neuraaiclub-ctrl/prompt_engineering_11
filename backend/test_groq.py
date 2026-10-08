import asyncio, httpx, json, os

groq_key = os.environ.get('GROQ_API_KEY')
if not groq_key:
    # Need to read the .env file
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('GROQ_API_KEY='):
                groq_key = line.strip().split('=', 1)[1]
                break
if groq_key.startswith('"'): groq_key = groq_key[1:-1]

original = 'Write a mystery opening chapter. Make it good, clear and not too long.'
expected = 'Task: Write the opening 500 words of a mystery novel... '
submitted = 'System role: Award-winning B2B SaaS copywriter... Task: Draft a 200-word product brief for TaskForge. Audience: CTOs at 100-500 person companies. Paragraph 1 (40 words): Data-backed pain point. Paragraph 2 (120 words): 3 features with quantified outcomes. Paragraph 3 (40 words): CTA with social proof. Constraints: Under 200 words, plain prose only. Banned words: revolutionary, seamless, game-changer.'
title = 'Question 5: Write a mystery opening chapter'
cat = 'Creative Writing'

_GROQ_EVAL_PROMPT = """You are an expert prompt engineering judge. Your job is to evaluate whether a student correctly fixed a specific broken prompt.

## THE BROKEN PROMPT THE STUDENT HAD TO FIX
Challenge Title: {challenge_title}
Category: {category}

<broken_prompt>
{original_bad_prompt}
</broken_prompt>

## EXPERT REFERENCE FIX (for calibration only)
<reference_fix>
{expected_good_prompt}
</reference_fix>

## STUDENT'S SUBMITTED ANSWER
<student_submission>
{submitted_prompt}
</student_submission>

---

## STEP 1 — MANDATORY RELEVANCE GATE

First, decide: Is the student's submission a genuine attempt to fix THIS specific broken prompt about "{challenge_title}"?

AUTOMATIC ZERO (all 5 scores = 0) if ANY of the following are true:
- The submission is about a completely different topic or domain than the broken prompt
- The submission addresses a different task goal than what the broken prompt was trying to accomplish
- The submission appears to be a generic, pre-written, or copy-pasted prompt for a different use case
- Example: broken prompt is about computing expected value of a probability game -> student submits a business earnings-call summarization prompt -> AUTOMATIC ZERO

If ANY of the above are true, output EXACTLY this and stop:
{{"clarity_score": 0, "specificity_score": 0, "context_score": 0, "output_format_score": 0, "constraints_score": 0, "relevance_note": "FAIL relevance gate: <one-line reason why it is off-topic>"}}

## STEP 2 — RUBRIC SCORING (only if the submission passed the relevance gate)

Score each dimension 0, 10, or 20. Scores must be one of those three values only.

- clarity_score: Is the prompt's intent clear and unambiguous for this specific task?
- specificity_score: Does it add task-specific details that directly improve the broken prompt?
- context_score: Does it provide sufficient context so an AI can execute the task correctly?
- output_format_score: Does it define a clear, appropriate output format for this task?
- constraints_score: Does it add boundaries/rules/constraints suited to this specific task?

Scale: 0=missing or wrong, 10=partial, 20=strong and directly applicable.

Output valid JSON only, no markdown:
{{"clarity_score": <0|10|20>, "specificity_score": <0|10|20>, "context_score": <0|10|20>, "output_format_score": <0|10|20>, "constraints_score": <0|10|20>, "relevance_note": "<one sentence on relevance and scoring rationale>"}}"""

prompt_text = _GROQ_EVAL_PROMPT.format(
    challenge_title=title,
    category=cat,
    original_bad_prompt=original,
    expected_good_prompt=expected,
    submitted_prompt=submitted
)

payload = {
    'model': 'llama3-70b-8192',
    'messages': [{'role': 'user', 'content': prompt_text}],
    'temperature': 0.0,
    'max_tokens': 256,
    'response_format': {'type': 'json_object'}
}
headers = {
    'Authorization': f'Bearer {groq_key}',
    'Content-Type': 'application/json'
}
resp = httpx.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload, timeout=30.0)
print(resp.json()['choices'][0]['message']['content'])
