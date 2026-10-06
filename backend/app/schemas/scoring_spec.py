from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional

class SpecCheck(BaseModel):
    type: str = Field(..., description="json_valid, schema_valid, equals_field, regex_match, regex_absent, max_words, min_items, contains_fact, no_new_facts, refuses, llm_check")
    path: Optional[str] = None
    value: Optional[Any] = None
    pattern: Optional[str] = None
    rule: Optional[str] = None

class SpecTestCase(BaseModel):
    id: str
    kind: str = Field(..., description="happy, edge, ambiguous, adversarial")
    input: str
    checks: List[SpecCheck] = []

class SpecExecution(BaseModel):
    mode: str = Field(default="system_prompt+user_input")

class SpecOutputContract(BaseModel):
    format: str = Field(default="json")
    json_schema: Optional[Dict[str, Any]] = None
    max_words: Optional[int] = None
    no_preamble: Optional[bool] = None

class SpecConstraint(BaseModel):
    id: str
    type: str = Field(default="assertion")
    rule: str

class SpecRubricAnchors(BaseModel):
    clarity: Optional[Dict[str, str]] = None
    specificity: Optional[Dict[str, str]] = None
    context: Optional[Dict[str, str]] = None
    output_format: Optional[Dict[str, str]] = None
    constraints: Optional[Dict[str, str]] = None

class SpecPublicExample(BaseModel):
    input: str

class ArenaChallengeSpecData(BaseModel):
    task_summary: str
    audience: str
    execution: SpecExecution
    public_examples: List[SpecPublicExample] = []
    test_cases: List[SpecTestCase] = []
    output_contract: SpecOutputContract
    constraints: List[SpecConstraint] = []
    rubric_anchors: SpecRubricAnchors
    reference_solutions: List[str] = []
    known_pitfalls: List[str] = []

class ArenaChallengeSpecUpdate(BaseModel):
    spec: ArenaChallengeSpecData
    
class ArenaChallengeSpecOut(BaseModel):
    id: str
    prompt_bank_item_id: str
    spec_version: int
    status: str
    spec: ArenaChallengeSpecData
    
    model_config = {"from_attributes": True}
