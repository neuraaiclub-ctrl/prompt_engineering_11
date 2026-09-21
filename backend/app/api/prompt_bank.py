from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.arena import PromptBankItem
from app.core.rbac import require_roles
from app.core.audit import log_audit_event

router = APIRouter(prefix="/prompt-bank", tags=["Admin Content Management"])

class PromptBankItemSchema(BaseModel):
    code: str
    category: str
    title: str
    difficulty: Optional[str] = "medium"
    original_bad_prompt: str
    bad_output_evidence: str
    flawed_reasons: Optional[List[str]] = []
    expected_improvements: Optional[List[str]] = []

@router.get("/")
def get_prompt_bank(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin"]))
):
    """Fetch all prompt bank items for the Admin Dashboard."""
    items = db.query(PromptBankItem).all()
    return items

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_prompt_bank_item(
    payload: PromptBankItemSchema,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin"]))
):
    """Create a new prompt bank item."""
    existing = db.query(PromptBankItem).filter(PromptBankItem.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Prompt with code {payload.code} already exists.")
        
    item = PromptBankItem(
        code=payload.code,
        category=payload.category,
        title=payload.title,
        difficulty=payload.difficulty,
        original_bad_prompt=payload.original_bad_prompt,
        bad_output_evidence=payload.bad_output_evidence,
        flawed_reasons=payload.flawed_reasons,
        expected_improvements=payload.expected_improvements
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    
    log_audit_event(
        db,
        action="prompt_bank.create",
        target_type="PromptBankItem",
        target_id=item.id,
        actor_user_id=admin_user.id
    )
    return item

@router.put("/{item_id}")
def update_prompt_bank_item(
    item_id: str,
    payload: PromptBankItemSchema,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin"]))
):
    """Update an existing prompt bank item."""
    item = db.query(PromptBankItem).filter(PromptBankItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Prompt Bank Item not found.")
        
    existing_code = db.query(PromptBankItem).filter(PromptBankItem.code == payload.code, PromptBankItem.id != item_id).first()
    if existing_code:
        raise HTTPException(status_code=400, detail=f"Code {payload.code} is used by another prompt.")

    item.code = payload.code
    item.category = payload.category
    item.title = payload.title
    item.difficulty = payload.difficulty
    item.original_bad_prompt = payload.original_bad_prompt
    item.bad_output_evidence = payload.bad_output_evidence
    item.flawed_reasons = payload.flawed_reasons
    item.expected_improvements = payload.expected_improvements
    
    db.commit()
    db.refresh(item)
    
    log_audit_event(
        db,
        action="prompt_bank.update",
        target_type="PromptBankItem",
        target_id=item.id,
        actor_user_id=admin_user.id
    )
    return item
