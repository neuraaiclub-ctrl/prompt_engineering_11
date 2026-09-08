"""
NEURA Prompt Fixing Arena - Seed Prompt Bank Data
20 Diverse, Real-World Flawed Prompts for Controlled Dynamic Assignment
"""

ARENA_PROMPT_BANK = [
    {
        "code": "P001",
        "category": "marketing",
        "title": "Vague Marketing Copy Request",
        "difficulty": "easy",
        "original_bad_prompt": "Write about marketing.",
        "bad_output_evidence": "Marketing is very important for businesses today. Companies use marketing to reach people through advertisements, social media, and billboards. If you want to grow sales, you need marketing.",
        "flawed_reasons": [
            "Extremely vague with no defined objective, channel, or angle",
            "No specified target audience or industry context",
            "No structural constraints, word count, or expected format"
        ],
        "expected_improvements": [
            "Specify the platform (e.g. LinkedIn, Email, Twitter)",
            "Define the target audience and value proposition",
            "Establish tone and explicit structural constraints (e.g., hook, 3 bullet points, CTA)"
        ]
    },
    {
        "code": "P002",
        "category": "summarization",
        "title": "Contradictory Length and Completeness Bounds",
        "difficulty": "medium",
        "original_bad_prompt": "Summarize the history of artificial intelligence in exactly 3 bullet points. Include all 10 major historical milestones from 1950 to 2026. Do not exceed 15 words total.",
        "bad_output_evidence": "Error: Cannot include 10 milestones across 3 bullets in under 15 words without severe truncation. 1. 1950 Turing Test. 2. 1997 Deep Blue. 3. 2026 LLMs.",
        "flawed_reasons": [
            "Contradictory constraints: 10 milestones cannot physically fit into 15 words across 3 bullets",
            "Forced hallucinations or refusal from the model due to impossible boundaries",
            "Lack of realistic prioritization criteria"
        ],
        "expected_improvements": [
            "Align token and word limits with the informational depth requested",
            "Specify the top 3 watershed eras or relax the word boundary to 80-100 words",
            "Clarify bullet format and milestone selection criteria"
        ]
    },
    {
        "code": "P003",
        "category": "extraction",
        "title": "Missing JSON Schema Definition",
        "difficulty": "easy",
        "original_bad_prompt": "Extract the customer information and sentiment from this support email transcript. Give it to me in json format.",
        "bad_output_evidence": "Here is your JSON!\n```json\n{\n  \"info\": \"John called about broken order 992. He is quite furious with the delay.\",\n  \"sentiment\": \"bad\"\n}\n```\nHope this helps you parse the data!",
        "flawed_reasons": [
            "Does not specify JSON keys, data types, or required fields",
            "Includes conversational wrapper markdown instead of raw JSON",
            "Sentiment is ambiguous ('bad' instead of enum POSITIVE/NEGATIVE/NEUTRAL)"
        ],
        "expected_improvements": [
            "Provide an explicit JSON schema with exact keys (e.g. customer_name, order_id, sentiment, urgency)",
            "Enforce strict raw JSON output with no markdown conversational intro or outro",
            "Define enumerated valid values for sentiment classification"
        ]
    },
    {
        "code": "P004",
        "category": "role_context",
        "title": "Missing Persona & Target Audience Context",
        "difficulty": "medium",
        "original_bad_prompt": "Explain quantum computing.",
        "bad_output_evidence": "Quantum computing is a type of computation that harnesses the collective properties of quantum states, such as superposition, interference, and entanglement, to perform calculations. Mathematical formulations involve qubits represented as vectors in a complex Hilbert space with unitary matrix operators.",
        "flawed_reasons": [
            "No persona defined for the AI or background level for the reader",
            "Lacks pedagogical framing, resulting in an unhelpful Wikipedia-style dump",
            "No relatable analogy or application examples requested"
        ],
        "expected_improvements": [
            "Assign a specific role (e.g. 'Senior Physics Professor' or 'Tech Educator')",
            "Identify the audience (e.g., high school student, business executive, software developer)",
            "Request a clear real-world analogy followed by practical implications"
        ]
    },
    {
        "code": "P005",
        "category": "coding",
        "title": "Unspecified Edge Cases & Language Specs",
        "difficulty": "medium",
        "original_bad_prompt": "Write a python function to divide two numbers.",
        "bad_output_evidence": "def divide(a, b):\n    return a / b",
        "flawed_reasons": [
            "Zero division error handling completely absent",
            "No type hinting, docstrings, or return type specifications",
            "Missing handling for non-numeric types, infinity, or float precision"
        ],
        "expected_improvements": [
            "Require type annotations (`float`, `Union`, etc.) and Python 3.10+ standards",
            "Demand explicit exception handling for `ZeroDivisionError` and invalid inputs",
            "Include comprehensive docstrings with doctest examples"
        ]
    },
    {
        "code": "P006",
        "category": "customer_support",
        "title": "Vague Customer Escalation Response",
        "difficulty": "easy",
        "original_bad_prompt": "Reply to this angry customer whose order was lost.",
        "bad_output_evidence": "Dear customer,\nWe saw your order was lost. We are very sorry about that. Mistakes happen sometimes in shipping. Please wait a few more days or let us know if you want another one.\nRegards,\nSupport",
        "flawed_reasons": [
            "Defensive, unprofessional, and non-committal tone ('Mistakes happen')",
            "No brand guidelines, escalation policy, or concrete resolution steps",
            "Does not collect verification details (tracking number, order ID)"
        ],
        "expected_improvements": [
            "Adopt an empathetic, accountable, brand-aligned customer service persona",
            "Provide immediate actionable next steps (expedited reshipment or instant refund)",
            "Include placeholder tags for customer name, order number, and direct representative contact"
        ]
    },
    {
        "code": "P007",
        "category": "technical_writing",
        "title": "Unfocused Technical Documentation Guide",
        "difficulty": "medium",
        "original_bad_prompt": "Explain Docker containers for developers.",
        "bad_output_evidence": "Docker is a tool that lets you run containers. Containers are like mini computers on your computer. You install Docker, write a Dockerfile, and run `docker build`.",
        "flawed_reasons": [
            "Superficial and misses core technical architectural components (cgroups, namespaces, image layers)",
            "Lacks structured prerequisites, CLI syntax, and practical examples",
            "Does not contrast containers with virtual machines"
        ],
        "expected_improvements": [
            "Structure into sections: Architecture, Container vs VM comparison, Step-by-Step workflow",
            "Provide a concrete reproducible `Dockerfile` snippet with best practices",
            "Target junior-to-mid software engineers with clear CLI commands and explanations"
        ]
    },
    {
        "code": "P008",
        "category": "hallucination_guard",
        "title": "Hallucination Bait Without Source Constraints",
        "difficulty": "hard",
        "original_bad_prompt": "What happened during the secret internal emergency board meeting yesterday at TechCorp? Give me the full minutes and who voted for the CEO change.",
        "bad_output_evidence": "At yesterday's emergency board meeting at TechCorp, board member Sarah Jenkins moved to replace CEO John Miller with interim leader Mark Davis. The vote passed 7-2 after heated discussion regarding quarterly losses.",
        "flawed_reasons": [
            "Asks for private, non-public, unverifiable information with no grounding data",
            "Model hallucinates convincing fake minutes and voter counts",
            "Fails to instruct the model on handling lack of verifiable context"
        ],
        "expected_improvements": [
            "Provide explicit source text or mandate grounding ONLY in provided documents",
            "Add a strict negative constraint: 'If the information is not present in the provided text, state: [DATA UNAVAILABLE]'",
            "Prohibit speculative inference or fictionalized minutes"
        ]
    },
    {
        "code": "P009",
        "category": "database",
        "title": "Ambiguous SQL Query Generation",
        "difficulty": "medium",
        "original_bad_prompt": "Write a SQL query to get our best customers.",
        "bad_output_evidence": "SELECT * FROM customers WHERE best = true;",
        "flawed_reasons": [
            "No schema, table names, or column definitions provided",
            "Definition of 'best' is completely undefined (highest total spend? most orders? highest retention?)",
            "No SQL dialect specified (PostgreSQL, MySQL, SQLite, BigQuery)"
        ],
        "expected_improvements": [
            "Provide explicit table schemas (`customers`, `orders`, `order_items`) and keys",
            "Define 'best' mathematically (e.g. top 10% by lifetime spend in past 12 months)",
            "Specify SQL dialect and require aggregation, joins, and indexing considerations"
        ]
    },
    {
        "code": "P010",
        "category": "localization",
        "title": "Idiomatic Translation Trap",
        "difficulty": "medium",
        "original_bad_prompt": "Translate 'bite the bullet' and 'break a leg' to German and Spanish.",
        "bad_output_evidence": "German: In die Kugel beißen / Ein Bein brechen.\nSpanish: Morder la bala / Romper una pierna.",
        "flawed_reasons": [
            "Translates cultural idioms literally, losing intended figurative meaning",
            "Does not request idiomatic cultural equivalents",
            "Lacks contextual usage sentences or explanations"
        ],
        "expected_improvements": [
            "Instruct model to translate for conceptual & cultural equivalence, not literal word-for-word",
            "Require both the nearest natural cultural idiom and a literal explanation in the target language",
            "Provide example context in a business or conversational scenario"
        ]
    },
    {
        "code": "P011",
        "category": "brainstorming",
        "title": "Unbounded Creative Ideation",
        "difficulty": "easy",
        "original_bad_prompt": "Give me some startup ideas in artificial intelligence.",
        "bad_output_evidence": "1. AI for healthcare diagnosis.\n2. AI for self-driving cars.\n3. AI chatbot for customer service.\n4. AI for legal documents.\n5. AI for creating art.",
        "flawed_reasons": [
            "Produces generic, oversaturated, unvalidated ideas",
            "No constraints on budget, founder skill set, B2B vs B2C, or timeline",
            "Missing evaluation metrics (tam, moat, monetization model)"
        ],
        "expected_improvements": [
            "Narrow to a specific vertical (e.g. B2B SaaS for veterinary clinic operations)",
            "Define constraints: bootstrap-friendly, under $10k MVP, solvable with LLM APIs",
            "Format with Problem, Proposed Solution, Ideal Customer Profile, and Unfair Advantage"
        ]
    },
    {
        "code": "P012",
        "category": "classification",
        "title": "Ambiguous Multi-Class Sentiment Parsing",
        "difficulty": "easy",
        "original_bad_prompt": "Is this tweet good or bad? 'Oh fantastic, another mandatory update right in the middle of my client presentation.'",
        "bad_output_evidence": "The tweet contains the word 'fantastic', which is generally positive, but describes an update interruption, so it might be mixed or bad.",
        "flawed_reasons": [
            "Fails to instruct model on recognizing sarcasm and tone nuance",
            "Binary classification ('good or bad') doesn't cover sarcasm or neutral operational status",
            "Produces rambling reasoning instead of a clean, parseable tag"
        ],
        "expected_improvements": [
            "Instruct model to account for sarcasm, irony, and conversational context",
            "Define explicit classification categories: [POSITIVE, NEGATIVE, NEUTRAL, SARCASTIC]",
            "Demand strict output format: `Classification: <CATEGORY>` with one-sentence rationale"
        ]
    },
    {
        "code": "P013",
        "category": "extraction",
        "title": "Address & Entity Extraction Without Normalization",
        "difficulty": "medium",
        "original_bad_prompt": "Find the address in this email: 'Meet me at 450 Lexington near Grand Central next Friday.'",
        "bad_output_evidence": "The address mentioned is 450 Lexington near Grand Central.",
        "flawed_reasons": [
            "Extracts raw snippet without parsing postal components (street, city, state, zip)",
            "Does not flag missing critical components (city/state inferred, no zip code)",
            "Unusable for automated geocoding or downstream CRM ingestion"
        ],
        "expected_improvements": [
            "Specify structured output with fields: street_number, street_name, landmark, city, state, postal_code",
            "Require explicit `confidence_score` and `missing_fields` list",
            "Enforce standardized postal normalization rules"
        ]
    },
    {
        "code": "P014",
        "category": "career",
        "title": "Unfocused Resume Critique",
        "difficulty": "medium",
        "original_bad_prompt": "Critique my resume and tell me what you think.",
        "bad_output_evidence": "Your resume looks pretty nice! Good fonts and clean bullet points. You have good experience at your previous jobs. Maybe add a hobbies section.",
        "flawed_reasons": [
            "Generic flattery with no actionable impact or substantive metrics critique",
            "Does not evaluate against ATS readability, STAR methodology, or target roles",
            "Recommends counterproductive advice ('add a hobbies section')"
        ],
        "expected_improvements": [
            "Assign a 'Senior Technical Recruiter' persona evaluating for Staff Software Engineer roles",
            "Require critique across 4 pillars: Impact quantification (STAR), ATS keyword density, Conciseness, Red flags",
            "Provide concrete 'Before vs After' rewritten bullet points"
        ]
    },
    {
        "code": "P015",
        "category": "tone_style",
        "title": "Contradictory Tone Requirements",
        "difficulty": "hard",
        "original_bad_prompt": "Write a formal email to our enterprise banking client explaining a security breach. Keep it super chill, funny, and use modern teenage slang so they don't freak out.",
        "bad_output_evidence": "Yo fam! Big yikes moment here at SafeBank. Some hackers took an L and slid into our databases, no cap! But don't stress bestie, we're working on that rizz right now!",
        "flawed_reasons": [
            "Humorous/slang tone in a security breach communication is irresponsible, unprofessional, and legally dangerous",
            "Fails to balance client reassurance with rigorous regulatory compliance",
            "Creates unacceptable enterprise risk"
        ],
        "expected_improvements": [
            "Eliminate contradictory, inappropriate tone requests in sensitive contexts",
            "Establish a clear, sober, professional, and accountable crisis communication tone",
            "Include required incident response components: What happened, What data was affected, Containment measures, Next steps"
        ]
    },
    {
        "code": "P016",
        "category": "legal",
        "title": "Ambiguous Legal Terms Synthesis",
        "difficulty": "hard",
        "original_bad_prompt": "Summarize this 30-page terms of service agreement.",
        "bad_output_evidence": "This agreement sets terms between the user and the company. By using the service you agree to follow the rules, pay subscription fees, and not violate intellectual property laws.",
        "flawed_reasons": [
            "Superficial summary that hides high-risk clauses (mandatory arbitration, class action waivers, data monetization)",
            "No risk assessment or key rights comparison for consumers",
            "Does not separate governing law, liability limitations, and termination rights"
        ],
        "expected_improvements": [
            "Require structured synthesis: 1. Data Collection & Sharing, 2. Dispute Resolution & Arbitration, 3. Subscription & Cancellation Rights",
            "Highlight high-impact 'Gotcha' clauses that significantly impact user privacy or liability",
            "Add a clear legal disclaimer: 'For informational purposes only; not legal advice'"
        ]
    },
    {
        "code": "P017",
        "category": "education",
        "title": "Unconstrained Educational Quiz Generator",
        "difficulty": "easy",
        "original_bad_prompt": "Make a quiz about history.",
        "bad_output_evidence": "1. Who was the first US president?\n2. What year did World War II end?\n3. Who built the pyramids?\n4. What was the Roman Empire?",
        "flawed_reasons": [
            "Trivial trivia questions with no target grade level or historical era",
            "Missing answer keys, multiple-choice options, and pedagogical explanations",
            "No learning objective or difficulty calibration"
        ],
        "expected_improvements": [
            "Define target level (e.g. AP World History / 10th grade) and topic (The Industrial Revolution)",
            "Specify format: 4 multiple-choice questions (A-D) with exactly one correct answer",
            "Require an answer key with detailed conceptual explanations for why wrong choices are incorrect"
        ]
    },
    {
        "code": "P018",
        "category": "workflow",
        "title": "Unbroken Multi-Step Composite Request",
        "difficulty": "hard",
        "original_bad_prompt": "Analyze our company's Q3 financial results, predict our stock price for next quarter, write the CEO keynote address, and format a 10-slide PowerPoint outline right now.",
        "bad_output_evidence": "Q3 revenue grew 5%. Stock might go up to $150 next quarter. Hello everyone, welcome to our annual summit! Slide 1: Welcome. Slide 2: Numbers. Slide 3: Future.",
        "flawed_reasons": [
            "Asks for multiple complex, disparate deliverables in a single prompt without sequencing",
            "Requests prohibited financial predictions (stock price speculation)",
            "Results in rushed, low-quality fragments across all four tasks"
        ],
        "expected_improvements": [
            "Decompose into a structured step-by-step chain of thought or distinct prompt modules",
            "Focus specifically on the financial synthesis and slide deck outline with explicit slide templates",
            "Remove speculative stock forecasting and replace with scenario-based operational drivers"
        ]
    },
    {
        "code": "P019",
        "category": "recommendation",
        "title": "Missing Negative Constraints & User Criteria",
        "difficulty": "easy",
        "original_bad_prompt": "Recommend some good laptops for gaming.",
        "bad_output_evidence": "Here are some good laptops:\n1. ASUS ROG Zephyrus ($2,500)\n2. Razer Blade 16 ($3,200)\n3. Alienware m16 ($2,800)\nThey all have great graphics cards!",
        "flawed_reasons": [
            "Recommends only ultra-expensive models without asking for budget or portability needs",
            "No negative constraints (e.g. weight, battery life, refurbished vs new)",
            "Does not justify recommendations with benchmark or spec comparisons"
        ],
        "expected_improvements": [
            "Define explicit budget tiers (Under $800, $800-$1500, Enthusiast)",
            "Add negative constraints: 'Exclude laptops heavier than 2.3kg or with under 4 hours non-gaming battery life'",
            "Include spec table with GPU, CPU, Display refresh rate, RAM, and thermals"
        ]
    },
    {
        "code": "P020",
        "category": "debugging",
        "title": "Vague Stack Trace & Bug Analysis",
        "difficulty": "medium",
        "original_bad_prompt": "Fix this error: TypeError: cannot read properties of undefined (reading 'map').",
        "bad_output_evidence": "This error happens when you try to call `.map()` on something that isn't an array. Check your variable and make sure it is an array before calling map.",
        "flawed_reasons": [
            "Offers generic textbook definition without seeing the actual codebase or data flow",
            "Does not provide defensive programming patterns (optional chaining, fallback arrays, async loading states)",
            "Lacks concrete React/JavaScript code snippets showing how to fix it"
        ],
        "expected_improvements": [
            "Instruct the model to provide 3 progressive solutions: Optional chaining (`data?.map`), Default props/fallback (`(data || []).map`), and Loading/Guard clauses",
            "Provide sample JSX/React code demonstrating safe async state handling",
            "Explain the root cause in JavaScript runtime evaluation"
        ]
    }
]
