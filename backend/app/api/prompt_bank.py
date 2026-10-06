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
    dataset_tag: Optional[str] = "default"
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
    admin_user: User = Depends(require_roles(["admin", "judge"]))
):
    """Fetch all prompt bank items for the Admin Dashboard."""
    items = db.query(PromptBankItem).all()
    return items

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_prompt_bank_item(
    payload: PromptBankItemSchema,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin", "judge"]))
):
    """Create a new prompt bank item."""
    existing = db.query(PromptBankItem).filter(PromptBankItem.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Prompt with code {payload.code} already exists.")
        
    item = PromptBankItem(
        code=payload.code,
        dataset_tag=payload.dataset_tag,
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

from fastapi import UploadFile, File
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@router.get("/demo-csv")
def get_demo_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["code", "dataset_tag", "category", "title", "difficulty", "original_bad_prompt", "bad_output_evidence", "flawed_reasons", "expected_improvements"])
    writer.writerow(["DEMO01", "default", "Coding", "SQL Query Fix", "medium", "write me a sql for users", "It returns everything without limits", "Lack of constraints|Vague", "Add LIMIT|Specify columns"])
    writer.writerow(["DEMO02", "default", "Writing", "Blog Post", "easy", "write a blog about AI", "Too short and generic", "No target audience|Too broad", "Specify word count|Define audience"])
    writer.writerow(["DEMO03", "default", "Logic", "Math Problem", "hard", "solve 2+2", "Too simple", "No steps requested", "Ask for reasoning steps"])
    writer.writerow(["DEMO04", "default", "Data", "Extract JSON", "medium", "extract names", "Returns unstructured text", "No format specified", "Demand valid JSON schema"])
    writer.writerow(["DEMO05", "default", "Creative", "Poem", "easy", "write poem", "Boring style", "No tone specified", "Specify tone and structure"])
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=demo_prompts.csv"
    return response

@router.post("/upload-csv")
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin", "judge"]))
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    
    added_count = 0
    for row in reader:
        if not row.get("code") or not row.get("title"): continue
        existing = db.query(PromptBankItem).filter(PromptBankItem.code == row["code"]).first()
        
        flawed = row.get("flawed_reasons", "").split("|") if row.get("flawed_reasons") else []
        expected = row.get("expected_improvements", "").split("|") if row.get("expected_improvements") else []
        
        if existing:
            existing.dataset_tag = row.get("dataset_tag", existing.dataset_tag)
            existing.category = row.get("category", existing.category)
            existing.title = row.get("title", existing.title)
            existing.difficulty = row.get("difficulty", existing.difficulty)
            existing.original_bad_prompt = row.get("original_bad_prompt", existing.original_bad_prompt)
            existing.bad_output_evidence = row.get("bad_output_evidence", existing.bad_output_evidence)
            existing.flawed_reasons = flawed
            existing.expected_improvements = expected
        else:
            new_item = PromptBankItem(
                code=row["code"],
                dataset_tag=row.get("dataset_tag", "default"),
                category=row.get("category", "General"),
                title=row["title"],
                difficulty=row.get("difficulty", "medium"),
                original_bad_prompt=row.get("original_bad_prompt", ""),
                bad_output_evidence=row.get("bad_output_evidence", ""),
                flawed_reasons=flawed,
                expected_improvements=expected
            )
            db.add(new_item)
        added_count += 1
        
    db.commit()
    return {"success": True, "message": f"Successfully processed {added_count} items."}

@router.post("/seed")
def seed_prompt_bank(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin", "judge"]))
):
    from app.core.arena_seed_data import ARENA_PROMPT_BANK
    added = 0
    for p_data in ARENA_PROMPT_BANK:
        existing = db.query(PromptBankItem).filter(PromptBankItem.code == p_data["code"]).first()
        if not existing:
            item = PromptBankItem(
                code=p_data["code"],
                category=p_data["category"],
                title=p_data["title"],
                difficulty=p_data["difficulty"],
                original_bad_prompt=p_data.get("original_bad_prompt", ""),
                bad_output_evidence=p_data.get("bad_output_evidence", ""),
                flawed_reasons=p_data.get("flawed_reasons", []),
                expected_improvements=p_data.get("expected_improvements", [])
            )
            db.add(item)
            added += 1
    db.commit()
    return {"success": True, "message": f"Successfully seeded {added} default questions."}


@router.put("/{item_id}")
def update_prompt_bank_item(
    item_id: str,
    payload: PromptBankItemSchema,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin", "judge"]))
):
    """Update an existing prompt bank item."""
    item = db.query(PromptBankItem).filter(PromptBankItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Prompt Bank Item not found.")
        
    existing_code = db.query(PromptBankItem).filter(PromptBankItem.code == payload.code, PromptBankItem.id != item_id).first()
    if existing_code:
        raise HTTPException(status_code=400, detail=f"Code {payload.code} is used by another prompt.")

    item.code = payload.code
    item.dataset_tag = payload.dataset_tag
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

@router.delete("/{item_id}")
def delete_prompt_bank_item(
    item_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(["admin", "judge"]))
):
    item = db.query(PromptBankItem).filter(PromptBankItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Prompt Bank Item not found.")
    db.delete(item)
    db.commit()
    return {"success": True, "message": "Deleted successfully."}

