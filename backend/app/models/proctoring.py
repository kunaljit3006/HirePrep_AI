from pydantic import BaseModel, Field
from typing import List, Optional, Literal

ViolationType = Literal[
    "copy_paste_attempt",
    "external_paste",
    "tab_switch",
    "window_blur",
    "devtools_attempt",
    "abnormal_typing_burst",
    "face_not_detected",
    "multiple_faces_detected"
]

class ProctoringViolation(BaseModel):
    violation_type: ViolationType
    details: Optional[str] = None
    timestamp: float
    question_idx: Optional[int] = None

class BodyLanguageSample(BaseModel):
    timestamp: float
    eye_contact_score: float = Field(ge=0.0, le=100.0) # 0 to 100%
    confidence_score: float = Field(ge=0.0, le=100.0)   # 0 to 100%
    head_stability_score: float = Field(ge=0.0, le=100.0)
    face_in_frame: bool = True

class ProctoringSummary(BaseModel):
    integrity_score: float = 100.0  # Starts at 100, deducted per violation
    total_violations: int = 0
    tab_switches: int = 0
    paste_attempts: int = 0
    devtools_attempts: int = 0
    avg_eye_contact: float = 85.0
    avg_confidence: float = 80.0
    flags: List[str] = Field(default_factory=list)
