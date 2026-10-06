import os
import zipfile
import shutil

BASE_DIR = r"d:\NEURA\prompt_engineering_11"
OUTPUT_ZIP = os.path.join(BASE_DIR, "ScoringEngineV2.zip")

FILES_TO_INCLUDE = [
    ("backend/app/api/arena.py", "backend/app/api/arena.py"),
    ("backend/app/models/arena_scoring.py", "backend/app/models/arena_scoring.py"),
    ("backend/app/models/arena.py", "backend/app/models/arena.py"),
    ("backend/app/services/arena_scoring_service.py", "backend/app/services/arena_scoring_service.py"),
    ("backend/app/services/arena_service.py", "backend/app/services/arena_service.py"),
    ("backend/app/workers/scoring_worker.py", "backend/app/workers/scoring_worker.py"),
    ("backend/app/scoring/providers/adapter.py", "backend/app/scoring/providers/adapter.py"),
    ("backend/app/scoring/providers/groq_adapter.py", "backend/app/scoring/providers/groq_adapter.py"),
    ("backend/app/scoring/rate_limiter.py", "backend/app/scoring/rate_limiter.py"),
    ("backend/app/scoring/checks.py", "backend/app/scoring/checks.py"),
    ("backend/app/scoring/harness.py", "backend/app/scoring/harness.py"),
    ("backend/app/scoring/judges.py", "backend/app/scoring/judges.py"),
    ("backend/app/scoring/aggregate.py", "backend/app/scoring/aggregate.py"),
    ("backend/app/scoring/integrity.py", "backend/app/scoring/integrity.py"),
    ("backend/app/scoring/calibration.py", "backend/app/scoring/calibration.py"),
    ("backend/app/tests/test_phase2_worker_and_limiter.py", "backend/app/tests/test_phase2_worker_and_limiter.py"),
    ("backend/app/tests/test_phase3_harness_and_checks.py", "backend/app/tests/test_phase3_harness_and_checks.py"),
    ("backend/app/tests/test_phase4_judges_and_aggregate.py", "backend/app/tests/test_phase4_judges_and_aggregate.py"),
    ("backend/app/tests/test_phase5_integrity_and_e2e.py", "backend/app/tests/test_phase5_integrity_and_e2e.py"),
    ("backend/app/tests/test_phase6_calibration.py", "backend/app/tests/test_phase6_calibration.py"),
    ("render.yaml", "render.yaml"),
    ("scoring-engine-master-prompt (1).md", "docs/scoring-engine-master-prompt.md"),
    ("scoring-engine-v2-plan (1).md", "docs/scoring-engine-v2-plan.md")
]

def create_archive():
    with zipfile.ZipFile(OUTPUT_ZIP, 'w') as zf:
        # Add detailed readme
        if os.path.exists(os.path.join(BASE_DIR, "readme_detailed.md")):
            zf.write(os.path.join(BASE_DIR, "readme_detailed.md"), "readme.md")
        
        for src, dest in FILES_TO_INCLUDE:
            abs_src = os.path.join(BASE_DIR, src)
            if os.path.exists(abs_src):
                zf.write(abs_src, dest)
            else:
                print(f"Warning: File not found {abs_src}")

    print(f"Zip created at: {OUTPUT_ZIP}")

if __name__ == "__main__":
    create_archive()
