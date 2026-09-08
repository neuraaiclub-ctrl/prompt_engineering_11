/* ==========================================================================
   NEURA ABSTRACTED AI PROVIDER & AUTOMATED EVALUATOR ENGINE
   ========================================================================== */

export class AIProviderAdapter {
  /**
   * Estimates token count based on words & punctuation (matching standard LLM tokenizers)
   */
  static countTokens(text) {
    if (!text || !text.trim()) return 0;
    const words = text.trim().split(/\s+/).length;
    // Approximates token count (avg ~1.3 tokens per English word + special tokens)
    const punctuationMatches = (text.match(/[{}[\](),.:;"'<>?!#]/g) || []).length;
    return Math.ceil(words * 1.25) + punctuationMatches;
  }

  /**
   * Simulates server-side execution against an abstracted LLM API
   */
  static async executePrompt(promptText, systemPrompt = '', caseOrChalObj = null) {
    const startTime = performance.now();
    
    // Simulate network latency (400ms to 900ms)
    await new Promise(resolve => setTimeout(resolve, 600 + Math.random() * 300));
    
    const endTime = performance.now();
    const latencyMs = Math.round(endTime - startTime);
    const tokenCountPrompt = this.countTokens(promptText) + this.countTokens(systemPrompt);

    let outputText = '';
    
    // Intelligent Output Simulation based on prompt structure
    const lowerPrompt = promptText.toLowerCase();

    if (lowerPrompt.includes('json') || lowerPrompt.includes('keys:') || lowerPrompt.includes('{')) {
      outputText = JSON.stringify({
        orderId: "#84920",
        customerRequest: "Refund requested if not delivered by Tuesday",
        sentiment: "NEGATIVE",
        confidenceScore: 0.96
      }, null, 2);
    } else if (lowerPrompt.includes('one word') || lowerPrompt.includes('only the single classification')) {
      outputText = lowerPrompt.includes('sarcasm') || lowerPrompt.includes('upset') || lowerPrompt.includes('wiped') ? 'NEGATIVE' : 'POSITIVE';
    } else if (lowerPrompt.includes('bullet points') || lowerPrompt.includes('extract:')) {
      outputText = `• Order ID: #84920\n• Customer Request: Refund on delay\n• Overall Sentiment: Highly Negative`;
    } else {
      // Default verbose unformatted narrative output
      outputText = `Analysis result: The customer expressed frustration regarding shipping delays for order #84920. They requested a full refund if delivery is delayed beyond Tuesday. Overall tone is negative.`;
    }

    const tokenCountOutput = this.countTokens(outputText);

    return {
      outputText,
      tokenCountPrompt,
      tokenCountOutput,
      latencyMs,
      status: 'success'
    };
  }

  /**
   * Server-side Automated Evaluator for Round 2 Hidden Test Cases
   * Produces disclosure-limited summary result ("Passed: 4/5")
   */
  static async evaluateHiddenTests(challengeId, promptText, hiddenTestCases) {
    const tests = hiddenTestCases.filter(tc => tc.challengeId === challengeId);
    let passCount = 0;
    const lowerPrompt = (promptText || '').toLowerCase();

    for (const test of tests) {
      // Simulate running prompt against hidden test input
      await new Promise(r => setTimeout(r, 60)); // simulated execution pulse
      
      const lowerInput = test.input.toLowerCase();

      if (challengeId === 'r2-chal-02' || test.evalRule?.type === 'json') {
        // Challenge 02: JSON Structured Extraction
        const hasJsonEnforcement = lowerPrompt.includes('json') || lowerPrompt.includes('valid json');
        const hasSchemaEnforcement = (lowerPrompt.includes('name') && lowerPrompt.includes('date')) || lowerPrompt.includes('schema') || lowerPrompt.includes('amount');
        
        if (hasJsonEnforcement && (hasSchemaEnforcement || lowerPrompt.includes('extract'))) {
          try {
            JSON.parse(test.expectedOutput);
            passCount++;
          } catch (e) {
            // invalid json expected
          }
        }
      } else {
        // Challenge 01: Sentiment Classification
        let simulatedOutput = '';
        if (lowerInput.includes('wiped') || lowerInput.includes('hold') || lowerInput.includes('upset') || lowerInput.includes('patch')) {
          simulatedOutput = 'NEGATIVE';
        } else if (lowerInput.includes('crushed') || lowerInput.includes('works great') || lowerInput.includes('early') || lowerInput.includes('specified')) {
          simulatedOutput = 'POSITIVE';
        } else {
          simulatedOutput = 'NEUTRAL';
        }

        // Check against expected output
        if (simulatedOutput.trim() === test.expectedOutput.trim()) {
          passCount++;
        }
      }
    }

    const totalCount = tests.length > 0 ? tests.length : 5;
    return {
      passCount,
      totalCount,
      passRatio: (passCount / totalCount).toFixed(2)
    };
  }
}
