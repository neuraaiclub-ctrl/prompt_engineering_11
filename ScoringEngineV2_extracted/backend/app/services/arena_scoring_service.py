from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.config import settings

class ArenaScoringService:
    @classmethod
    def get_preflight_check(cls, db: Session) -> Dict[str, Any]:
        """
        Phase 2 Preflight Check.
        Computes the target capacity and warns if limits are insufficient.
        Formula: max_calls = floor(safety_factor * RPM * Wave_Time / Teams)
        """
        # Assumptions for preflight
        N_teams = 25
        wave_target_minutes = 10
        safety_factor = 0.7
        
        # Hardcoded limits based on plan for now. Ideally drawn from config.
        rpm_lane = 20
        tpm_lane = 100000 
        
        max_calls = int(safety_factor * rpm_lane * wave_target_minutes / N_teams)
        calls_needed_L2 = 5
        
        # Determine binding limit
        binding = "RPM"
        chosen_level = "L2"
        if max_calls < calls_needed_L2:
            chosen_level = "L3"
            
        verdict = "GO"
        if chosen_level == "L3":
            verdict = "DEGRADED-GO"
            
        return {
            "status": verdict,
            "timestamp": "2026-10-04T12:50:00Z", # Should use datetime.now
            "lanes": [
                {
                    "lane_id": "P1-A",
                    "rpm_limit": rpm_lane,
                    "tpm_limit": tpm_lane,
                    "binding_constraint": binding,
                    "chosen_level": chosen_level
                },
                {
                    "lane_id": "P1-B",
                    "rpm_limit": rpm_lane,
                    "tpm_limit": tpm_lane,
                    "binding_constraint": binding,
                    "chosen_level": chosen_level
                }
            ],
            "metrics": {
                "teams_per_wave": N_teams,
                "target_minutes": wave_target_minutes,
                "safety_factor": safety_factor
            },
            "warnings": [
                "Lane quota shared risk: Both keys might share the same org."
            ]
        }
