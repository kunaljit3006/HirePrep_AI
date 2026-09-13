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
    preferred_interviewer_gender: Optional[Literal["male", "female", "random"]] = "random"
    resume_id: Optional[str] = None
    custom_topics: List[str] = Field(default_factory=list)

class InterviewMessage(BaseModel):
    role: Literal["interviewer", "candidate", "system"]
    content: str
    timestamp: float
    round_type: Optional[str] = None
    question_idx: Optional[int] = None
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    interviewer_name: Optional[str] = None

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

class ArchitectureDiagramComponent(BaseModel):
    id: str
    type: str  # client, load_balancer, api_gateway, service, database, cache, message_queue, storage, cdn
    label: str
    x: Optional[float] = 0.0
    y: Optional[float] = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ArchitectureDiagramConnection(BaseModel):
    id: Optional[str] = None
    from_id: str
    to_id: str
    label: Optional[str] = None
    protocol: Optional[str] = "HTTP"  # HTTP, gRPC, WebSocket, Kafka, TCP

class ArchitectureDiagramData(BaseModel):
    components: List[ArchitectureDiagramComponent] = Field(default_factory=list)
    connections: List[ArchitectureDiagramConnection] = Field(default_factory=list)
    snapshot_url: Optional[str] = None
    notes: Optional[str] = None

class DiagramSubmissionRequest(BaseModel):
    diagram: ArchitectureDiagramData
    verbal_explanation: Optional[str] = None
    intent: Literal["present", "hint_request", "approach_check"] = "present"

class DiagramSubmissionResult(BaseModel):
    score: Optional[float] = None
    architecture_score: Optional[float] = None
    critique: Optional[str] = None
    detected_components: List[str] = Field(default_factory=list)
    spof_risks: List[str] = Field(default_factory=list)
    bottlenecks: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    interviewer_speech: Optional[str] = None
    suggested_follow_up: Optional[str] = None
    is_approach_check: bool = False
    track_status: Optional[str] = None
    is_hint: bool = False
    hint_tier: Optional[int] = None
    probed_topic: Optional[str] = None

class InterviewHistoryItem(BaseModel):
    id: str
    company: str
    role: str
    difficulty: str
    status: str
    duration_min: int
    created_at: str
    ended_at: Optional[str] = None
    formatted_date: Optional[str] = None  # e.g., "Sep 03, 2026"
    relative_time: Optional[str] = None   # e.g., "9 days ago", "Just now", "Yesterday"
    overall_score: Optional[float] = None
    letter_grade: Optional[str] = None
    hire_recommendation: Optional[str] = None
    feedback_id: Optional[str] = None

class InterviewSessionResponse(BaseModel):
    interview_id: str
    user_id: str
    company: str
    role: str
    status: InterviewStatus
    current_round: str
    current_question_idx: int
    total_questions: int
    resume_id: Optional[str] = None
    candidate_name: Optional[str] = None
    interviewer_persona: Optional[str] = "standard"
    interviewer_persona_profile: Optional[Dict[str, Any]] = None
    questions: List[QuestionItem] = Field(default_factory=list)
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None

