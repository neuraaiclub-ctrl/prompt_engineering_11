import logging
from typing import Dict, Any, List
from .providers.adapter import AIProviderAdapter
from .checks import run_deterministic_check

logger = logging.getLogger(__name__)

class ScoringHarness:
    def __init__(self, provider: AIProviderAdapter, model: str = "llama3-8b-8192"):
        self.provider = provider
        self.model = model

    def evaluate_test_case(self, system_prompt: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single test case using the provider and evaluates its checks.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_case.get("input", "")}
        ]
        
        try:
            completion = self.provider.complete(messages, self.model)
            
            check_results = []
            all_passed = True
            for check in test_case.get("checks", []):
                passed = run_deterministic_check(check, completion.content)
                check_results.append({
                    "type": check.get("type"),
                    "passed": passed
                })
                if not passed:
                    all_passed = False
                    
            return {
                "success": True,
                "passed": all_passed,
                "check_results": check_results,
                "output": completion.content,
                "tokens_in": completion.tokens_in,
                "tokens_out": completion.tokens_out,
                "cost_usd": completion.cost_usd
            }
        except Exception as e:
            logger.error(f"Error evaluating test case {test_case.get('id', 'unknown')}: {e}")
            return {
                "success": False,
                "passed": False,
                "error": str(e)
            }

    def evaluate_submission_l2(self, system_prompt: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        L2 execution: behavior-only evaluation (no LLM judge panel).
        Calculates score by running test cases.
        """
        results = []
        test_cases = spec.get("test_cases", [])
        
        for tc in test_cases:
            # We do 1 sample for simplicity in L2 mock
            res = self.evaluate_test_case(system_prompt, tc)
            results.append({
                "test_case_id": tc.get("id"),
                "result": res
            })
            
        # Simplified L2 dimension mapping
        # In a full system, this would map specific tests to dimensions via score_map.
        # For this MVC, we average pass rates.
        if not results:
            overall = 0.0
        else:
            passed_count = sum(1 for r in results if r["result"].get("passed", False))
            overall = (passed_count / len(results)) * 20.0
            
        return {
            "dimension_scores": {
                "clarity": overall,
                "specificity": overall,
                "context": overall,
                "output_format": overall,
                "constraints": overall
            },
            "test_results": results,
            "confidence": 0.8
        }
