from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

RoundType = Literal[
    "behavioral",
    "resume",
    "coding",
    "system_design",
    "cs_fundamentals",
    "hr"
]

DifficultyLevel = Literal["easy", "medium", "hard"]

class TestCase(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False

class QuestionItem(BaseModel):
    id: str
    round_type: RoundType
    topic: str
    title: str
    description: str
    difficulty: DifficultyLevel = "medium"
    hints: List[str] = Field(default_factory=list)
    expected_key_points: List[str] = Field(default_factory=list)
    starter_code: Optional[Dict[str, str]] = None  # e.g. {"python": "def solve()...", "javascript": "..."}
    test_cases: List[TestCase] = Field(default_factory=list)
    requires_whiteboard: bool = False
    whiteboard_mode: Optional[Literal["none", "optional", "required"]] = "none"
    company_context: Optional[str] = None
    source_attribution: Optional[str] = None  # e.g., "LeetCode Discuss Google India 2024"
    round_focus: Optional[str] = None  # e.g., "LP - Customer Obsession", "Frontend Architecture", "SQL Analytics"

class QuestionBankRequest(BaseModel):
    company: str
    role: str
    location: str = "India"
    experience_level: str = "Mid"
    tech_stack: List[str] = Field(default_factory=list)
    include_resume_questions: bool = True

class QuestionBankResponse(BaseModel):
    bank_id: str
    company: str
    role: str
    location: str
    total_questions: int
    questions: List[QuestionItem]
    created_at: str
