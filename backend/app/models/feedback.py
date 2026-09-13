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

class SystemDesignArchitectureReport(BaseModel):
    architecture_score: float = Field(ge=0.0, le=100.0)
    scalability_rating: Literal["High", "Moderate", "Low"] = "Moderate"
    fault_tolerance: Literal["High Availability", "Partial Redundancy", "Single Point of Failure Detected"] = "Partial Redundancy"
    spof_risks: List[str] = Field(default_factory=list)
    bottlenecks: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    feedback: str
    diagram_snapshot_url: Optional[str] = None

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
    architecture_report: Optional[SystemDesignArchitectureReport] = None
    proctoring: ProctoringSummary
    top_strengths: List[str]
    top_weaknesses: List[str]
    improvement_roadmap_14_days: List[RoadmapDay]
    detailed_summary: str
    created_at: str
    formatted_date: Optional[str] = None  # e.g., "Sep 03, 2026"
    relative_time: Optional[str] = None   # e.g., "9 days ago", "Just now"

class PerformanceTrendPoint(BaseModel):
    interview_id: str
    date: str
    relative_time: Optional[str] = None   # e.g., "9 days ago"
    company: str
    role: str
    overall_score: float
    letter_grade: str
    hire_recommendation: str

class SkillsRadarAverage(BaseModel):
    dsa_score: float
    system_design_score: float
    behavioral_score: float
    problem_solving_score: float
    communication_score: float

class CandidateAnalyticsOverview(BaseModel):
    user_id: str
    total_interviews_taken: int
    completed_interviews: int
    average_score: float
    highest_score: float
    lowest_score: float
    hire_recommendation_rate: float
    score_trends: List[PerformanceTrendPoint]
    skills_radar: SkillsRadarAverage
    top_recurring_strengths: List[str]
    top_recurring_weaknesses: List[str]
