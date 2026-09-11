from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from app.models.proctoring import ProctoringSummary

class SectionScore(BaseModel):
    section_name: str  # e.g., "DSA & Problem Solving", "Behavioral & Leadership", "System Design"
    score: float = Field(ge=0.0, le=100.0)
    weight: float = 1.0
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str

class CommunicationMetrics(BaseModel):
    clarity_score: float = Field(ge=0.0, le=100.0)
    conciseness_score: float = Field(ge=0.0, le=100.0)
    structure_score: float = Field(ge=0.0, le=100.0)
    confidence_score: float = Field(ge=0.0, le=100.0)
    filler_words_detected: List[str] = Field(default_factory=list)
    feedback: str

class CameraBodyLanguageReport(BaseModel):
    overall_confidence_score: float = Field(ge=0.0, le=100.0)
    eye_contact_percentage: float = Field(ge=0.0, le=100.0)
    posture_stability_score: float = Field(ge=0.0, le=100.0)
    fidgeting_detected: bool = False
    notes: List[str] = Field(default_factory=list)

class CodeQualityReport(BaseModel):
    correctness_score: float = Field(ge=0.0, le=100.0)
    time_complexity_optimal: bool = True
    space_complexity_optimal: bool = True
    clean_code_score: float = Field(ge=0.0, le=100.0)
    feedback: str

class RoadmapDay(BaseModel):
    day: int
    focus_topic: str
    action_items: List[str]
    curated_resources: List[Dict[str, str]] = Field(default_factory=list) # [{"title": "...", "url": "..."}]

class FeedbackReportResponse(BaseModel):
    feedback_id: str
    interview_id: str
    user_id: str
    overall_score: float = Field(ge=0.0, le=100.0)
    letter_grade: Literal["A+", "A", "B+", "B", "C", "D", "F"]
    hire_recommendation: Literal["Strong Hire", "Hire", "Leaning Hire", "Leaning No Hire", "No Hire"]
    section_scores: List[SectionScore]
    communication: CommunicationMetrics
    body_language: CameraBodyLanguageReport
    code_quality: Optional[CodeQualityReport] = None
    proctoring: ProctoringSummary
    top_strengths: List[str]
    top_weaknesses: List[str]
    improvement_roadmap_14_days: List[RoadmapDay]
    detailed_summary: str
    created_at: str
