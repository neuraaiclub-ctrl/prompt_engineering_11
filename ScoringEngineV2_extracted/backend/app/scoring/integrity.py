from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.arena import ArenaSubmission

class IntegrityScanner:
    def __init__(self):
        pass

    def _normalize(self, text: str) -> str:
        return text.lower().strip()

    def _jaccard_similarity(self, a: str, b: str) -> float:
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a or not set_b:
            return 0.0
        return len(set_a.intersection(set_b)) / len(set_a.union(set_b))

    def scan_submission(self, db: Session, submission_text: str, original_bad_prompt: str) -> List[Dict[str, Any]]:
        """
        Scans a submission for integrity flags.
        For MVC, we implement a simple Jaccard similarity check against the original bad prompt.
        """
        flags = []
        
        norm_sub = self._normalize(submission_text)
        norm_orig = self._normalize(original_bad_prompt)
        
        sim = self._jaccard_similarity(norm_sub, norm_orig)
        if sim >= 0.85:
            flags.append({
                "flag_type": "copy_of_bad_prompt",
                "severity": "high",
                "description": f"Submission is highly similar to the original bad prompt (similarity: {sim:.2f})."
            })
            
        # In a full system, we would also fetch other teams' submissions and compare for near-duplicates
        # and run language ID or gibberish detection.
        
        return flags
