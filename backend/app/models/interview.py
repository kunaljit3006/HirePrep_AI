from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from app.models.question import QuestionItem
from app.models.proctoring import ProctoringViolation, BodyLanguageSample

InterviewStatus = Literal["scheduled", "in_progress", "completed", "cancelled", "disconnected"]

class CreateInterviewRequest(BaseModel):
    company: str
    role: str
    location: str = "India"
    duration_min: int = 30
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    interviewer_persona: Literal["amazon_bar_raiser", "google_staff", "startup_cto", "standard"] = "standard"
    resume_id: Optional[str] = None
    custom_topics: List[str] = Field(default_factory=list)

class InterviewMessage(BaseModel):
    role: Literal["interviewer", "candidate", "system"]
    content: str
    timestamp: float
    round_type: Optional[str] = None
    question_idx: Optional[int] = None
    audio_url: Optional[str] = None

class CodeSubmissionRequest(BaseModel):
    code: str
    language: str = "python"
    question_id: str

class CodeSubmissionResult(BaseModel):
    passed: bool
    total_tests: int
    passed_tests: int
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

class InterviewSessionResponse(BaseModel):
    interview_id: str
    user_id: str
    company: str
    role: str
    status: InterviewStatus
    current_round: str
    current_question_idx: int
    total_questions: int
    interviewer_persona: Optional[str] = "standard"
    questions: List[QuestionItem] = Field(default_factory=list)
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
