from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum

class BehaviorStrategy(str, Enum):
    SIMPLIFY = "SIMPLIFY"
    CHALLENGE = "CHALLENGE"
    PROBE_DEEPER = "PROBE_DEEPER"
    ENCOURAGE = "ENCOURAGE"
    REVISIT = "REVISIT"
    NO_SPECIAL_BEHAVIOR = "NO_SPECIAL_BEHAVIOR"

class ConversationalStateSummary(BaseModel):
    current_topic: Optional[str] = Field(None, description="The current main topic being discussed.")
    current_mastery: Optional[str] = Field(None, description="The candidate's apparent mastery of the current topic (e.g., struggling, adequate, excelling).")
    confidence: Optional[str] = Field(None, description="The candidate's confidence level.")
    recent_performance_trend: Optional[str] = Field(None, description="Trend over recent questions (e.g., improving, declining, stable).")
    current_difficulty: Optional[str] = Field(None, description="The current difficulty level.")
    follow_up_needed: Optional[bool] = Field(False, description="Whether a follow-up is immediately needed.")
    relevant_weak_areas: List[str] = Field(default_factory=list, description="Weak areas relevant to the current state.")
    relevant_topics_to_revisit: List[str] = Field(default_factory=list, description="Deferred topics to revisit.")
    current_answer_score: Optional[float] = Field(None, description="Score of the immediate current answer.")

class MemoryType(str, Enum):
    TECHNICAL_CLAIM = "TECHNICAL_CLAIM"
    PROJECT_DECISION = "PROJECT_DECISION"
    TECH_USED = "TECH_USED"
    CANDIDATE_EXPERIENCE = "CANDIDATE_EXPERIENCE"
    UNCERTAIN_CLAIM = "UNCERTAIN_CLAIM"
    FOLLOW_UP_GENERATOR = "FOLLOW_UP_GENERATOR"
    GENERAL = "GENERAL"

class ConversationMemoryItem(BaseModel):
    id: str
    memory_type: MemoryType
    content: str
    turn_index: int
    topic: Optional[str] = None
    value_score: int = Field(default=1, description="Score 1-10 indicating the importance of this memory.")
