from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.execution import Execution
from app.models.user import User
from app.core.rbac import get_current_user
from app.core.ai_adapter import AIProviderAdapter
from app.core.rate_limiter import enforce_rate_limit

router = APIRouter(prefix="/executions", tags=["AI Executions"])

ALLOWED_MODELS = {"gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "deepseek-r1"}

class PreviewExecutionSchema(BaseModel):
    user_prompt: str = Field(..., min_length=1, max_length=5000)
    system_prompt: Optional[str] = Field(None, max_length=5000)
    model: Optional[str] = "gpt-4o-mini"
    prompt_version_id: Optional[str] = None

@router.post("/preview")
def preview_execution(
    request: Request,
    payload: PreviewExecutionSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enforce_rate_limit(request, "executions_preview", limit=30, window_seconds=60, identifier=current_user.id)

    model_choice = payload.model or "gpt-4o-mini"
    if model_choice not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported model '{model_choice}'. Permitted models: {sorted(list(ALLOWED_MODELS))}"
        )

    if not payload.user_prompt or not payload.user_prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt text cannot be empty")

    res = AIProviderAdapter.execute(
        user_prompt=payload.user_prompt,
        system_prompt=payload.system_prompt,
        model=model_choice
    )

    execution_rec = Execution(
        prompt_version_id=payload.prompt_version_id,
        model=payload.model or "gpt-4o-mini",
        output_text=res["output_text"],
        status=res["status"],
        token_count_prompt=res["token_count_prompt"],
        token_count_output=res["token_count_output"],
        latency_ms=res["latency_ms"]
    )
    db.add(execution_rec)
    db.commit()

    return {
        "execution_id": execution_rec.id,
        "output_text": res["output_text"],
        "token_count_prompt": res["token_count_prompt"],
        "token_count_output": res["token_count_output"],
        "latency_ms": res["latency_ms"],
        "status": res["status"]
    }
