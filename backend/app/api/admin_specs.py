from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.rbac import require_roles
from app.models.user import User
from app.models.arena import PromptBankItem
from app.models.arena_scoring import ArenaChallengeSpec
from app.schemas.scoring_spec import ArenaChallengeSpecOut, ArenaChallengeSpecUpdate
import datetime

router = APIRouter()

@router.get("/{item_id}", response_model=ArenaChallengeSpecOut)
def get_spec(item_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["admin", "judge"]))):
    """Get the current challenge spec for a prompt bank item."""
    spec = db.query(ArenaChallengeSpec).filter(ArenaChallengeSpec.prompt_bank_item_id == item_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found for this prompt bank item.")
    return spec

@router.put("/{item_id}", response_model=ArenaChallengeSpecOut)
def update_spec(item_id: str, payload: ArenaChallengeSpecUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["admin"]))):
    """Create or update a challenge spec. Increments version and resets status to draft."""
    bank_item = db.query(PromptBankItem).filter(PromptBankItem.id == item_id).first()
    if not bank_item:
        raise HTTPException(status_code=404, detail="Prompt bank item not found.")
        
    spec = db.query(ArenaChallengeSpec).filter(ArenaChallengeSpec.prompt_bank_item_id == item_id).first()
    if not spec:
        spec = ArenaChallengeSpec(
            prompt_bank_item_id=item_id,
            spec=payload.spec.model_dump(),
            spec_version=1,
            status="draft"
        )
        db.add(spec)
    else:
        spec.spec = payload.spec.model_dump()
        spec.spec_version += 1
        spec.status = "draft"
        spec.validated_at = None
        
    db.commit()
    db.refresh(spec)
    return spec

@router.post("/{item_id}/validate")
def validate_spec(item_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["admin"]))):
    """
    Acceptance gate for spec: 
    Run original_bad_prompt and reference_solutions through harness.
    For Phase 1 MVC, this just verifies the schema and marks it published,
    because the actual execution harness is built in Phase 2/3.
    """
    spec = db.query(ArenaChallengeSpec).filter(ArenaChallengeSpec.prompt_bank_item_id == item_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found.")
    
    # MVC stub: acceptance gate execution logic happens here
    # 1. execute original bad prompt -> must score low
    # 2. execute reference_solutions -> must score high
    # We will simulate success for Phase 1 MVP
    
    spec.status = "published"
    spec.validated_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True, "status": spec.status, "message": "Spec validated and published."}
