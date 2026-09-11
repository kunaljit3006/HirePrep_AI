from typing import TypedDict, Literal, List, Dict, Any, Optional

class InterviewState(TypedDict):
    # Core identifiers & User Context (Modular for Auth integration)
    interview_id: str
    user_id: str

    # Resume & Profile extraction
    resume_bytes: Optional[bytes]
    resume_filename: Optional[str]
    resume_data: Optional[Dict[str, Any]]
    detected_profile_links: Optional[Dict[str, str]]
    scraped_profiles: Optional[Dict[str, Any]]

    # Target role configuration
    company: str
    role: str
    location: str
    duration_min: int
    interviewer_persona: Optional[Literal["amazon_bar_raiser", "google_staff", "startup_cto", "standard"]]

    # Question Bank & Round Management
    questions: List[Dict[str, Any]]
    current_question_idx: int
    current_round: Literal["behavioral", "resume", "coding", "system_design", "cs_fundamentals", "hr"]

    # Live Dialogue & Scoring
    transcript: List[Dict[str, Any]]  # [{"role": "interviewer"|"candidate"|"system", "content": str, "timestamp": float}]
    latest_candidate_response: Optional[str]
    latest_interviewer_response: Optional[str]
    current_score: float
    difficulty_level: Literal["easy", "medium", "hard"]
    follow_up_count: int  # Number of probing follow-ups asked on current question
    active_follow_up_topic: Optional[str]  # e.g., "Redis caching choice", "time complexity trade-off"
    is_clarification: Optional[bool]  # True if candidate asked a clarifying question
    is_hint: Optional[bool]  # True if candidate requested a hint
    hint_tier: Optional[int]  # Tier level of the hint provided (1, 2, or 3)
    hint_count: int  # Number of hints provided on current question
    hints_given: List[str]  # History of hints provided to the candidate

    # Anti-Cheat, Camera Body Language & Speech Clarity Telemetry
    violations: List[Dict[str, Any]]
    body_language_samples: List[Dict[str, Any]]
    speech_clarity_metrics: Optional[Dict[str, Any]]  # Filler word counts, pacing, WPM
    code_submissions: List[Dict[str, Any]]

    # Pipeline Phase & Report Output
    phase: Literal["setup", "scrape", "prep", "interview", "awaiting_candidate", "evaluate", "feedback", "done"]
    feedback_report: Optional[Dict[str, Any]]
