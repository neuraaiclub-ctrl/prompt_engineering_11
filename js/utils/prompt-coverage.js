/* ==========================================================================
   PROMPT COVERAGE
   A rough, client-side read of which of the five judging criteria a draft
   touches. It looks for signals (a role, a format, a limit...) — it does not
   judge quality, and it is NOT the score. Judges score the locked prompt.

   Returns values 0..1 in the same order as CRITERIA in radar.js.
   ========================================================================== */

const has = (re, text) => re.test(text);
const count = (re, text) => (text.match(re) || []).length;
const cap = (n) => Math.max(0, Math.min(1, n));

export function analyzePrompt(raw) {
  const text = (raw || '').trim();
  if (text.length < 8) return [0, 0, 0, 0, 0];

  const lower = text.toLowerCase();
  const words = text.split(/\s+/).filter(Boolean).length;
  const lines = text.split(/\n+/).filter(l => l.trim()).length;
  const sentences = count(/[.!?](\s|$)/g, text);

  /* Clarity: a stated task, enough words to say it, and a reason for it */
  let clarity = 0;
  if (has(/\b(write|draft|extract|classify|summari[sz]e|generate|return|list|convert|translate|identify|analy[sz]e|produce|create|answer|rewrite|turn|respond|reply|explain|compare|decide|output)\b/, lower)) clarity += 0.4;
  clarity += words >= 30 ? 0.3 : words >= 14 ? 0.18 : 0.06;
  if (sentences >= 2 || lines >= 3) clarity += 0.15;
  if (has(/\b(so that|in order to|goal|objective|purpose|because|to help|used for|will be used)\b/, lower)) clarity += 0.15;

  /* Specificity: numbers, explicit bounds, examples, enumerations */
  let specificity = 0;
  if (has(/\d/, text)) specificity += 0.3;
  if (has(/\b(exactly|at most|at least|no more than|no fewer than|maximum|minimum|under|between|within|up to)\b/, lower)) specificity += 0.25;
  if (has(/\b(e\.g\.|for example|such as|like:)\b|"[^"]{3,}"/i, text)) specificity += 0.25;
  if (has(/^\s*([-*•]|\d+[.)])\s+/m, text)) specificity += 0.2;

  /* Context: who the model is, who it's for, what it's working from */
  let context = 0;
  if (has(/\b(you are|act as|your role|as an? [a-z-]+ (?:expert|analyst|engineer|assistant|editor|writer|strategist|agent|reviewer))\b/, lower)) context += 0.4;
  if (has(/\b(audience|reader|readers|customer|customers|user|users|manager|managers|student|students|beginner|team)\b/, lower)) context += 0.3;
  if (has(/\b(context|background|scenario|given|input|the following|below|based on|using only)\b/, lower)) context += 0.3;

  /* Output format: named structure and "only that" language */
  let format = 0;
  if (has(/\b(json|xml|yaml|csv|markdown|table|schema|sql)\b/, lower)) format += 0.45;
  if (has(/\b(keys?|fields?|columns?|headings?|bullets?|numbered|sections?|one-line|one sentence|paragraphs?|format)\b/, lower)) format += 0.35;
  if (has(/\b(return only|output only|respond only|only return|no extra|no preamble|nothing else)\b/, lower)) format += 0.2;

  /* Constraints: rules, edge-case handling, tone/length guardrails */
  let constraints = 0;
  if (has(/\b(must|never|do not|don't|avoid|only|always|forbid)\b/, lower)) constraints += 0.3;
  if (has(/\b(if .{0,40}(missing|unknown|not found|empty|unclear|ambiguous|invalid)|otherwise|fallback|null|n\/a|edge case|when .{0,30}not)\b/, lower)) constraints += 0.4;
  if (has(/\b(tone|style|length|words|characters|tokens|sentences|limit)\b/, lower)) constraints += 0.3;

  return [clarity, specificity, context, format, constraints].map(cap);
}
