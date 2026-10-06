from typing import Dict, Any

def aggregate_scores(behavioral: Dict[str, float], rubric: Dict[str, float]) -> Dict[str, float]:
    """
    Aggregates behavioral (B) and rubric (R) scores into final dimension scores.
    Both inputs should be on a 0-20 scale.
    """
    dimensions = ["clarity", "specificity", "context", "output_format", "constraints"]
    final_scores = {}
    
    w_b = 0.6
    w_r = 0.4
    
    for dim in dimensions:
        b_score = behavioral.get(dim, 0.0)
        r_score = rubric.get(dim, 0.0)
        
        # R_eff = min(R, B + 5) for a 0-20 scale (equivalent to B + 0.25 on a 0-1 scale)
        r_eff = min(r_score, b_score + 5.0)
        
        raw_score = (w_b * b_score) + (w_r * r_eff)
        final_scores[dim] = max(0.0, min(20.0, round(raw_score, 1)))
        
    return final_scores
