from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserSyncRequest(BaseModel):
    """Payload sent by frontend after Supabase sign-in/up."""
    id: str = Field(..., description="Supabase Auth UUID (sub)")
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    github_handle: Optional[str] = None
    leetcode_handle: Optional[str] = None
    codeforces_handle: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class UserUpdateRequest(BaseModel):
    """Candidate profile update request."""
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    github_handle: Optional[str] = None
    leetcode_handle: Optional[str] = None
    codeforces_handle: Optional[str] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    target_location: Optional[str] = None
    experience_level: Optional[str] = None

class UserStats(BaseModel):
    total_interviews: int = 0
    completed_interviews: int = 0
    average_score: float = 0.0
    top_strengths: List[str] = []
    top_weaknesses: List[str] = []
    last_interview_at: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    github_handle: Optional[str] = None
    leetcode_handle: Optional[str] = None
    codeforces_handle: Optional[str] = None
    target_role: Optional[str] = "Full Stack Software Engineer"
    target_company: Optional[str] = "Google"
    target_location: Optional[str] = "India"
    experience_level: Optional[str] = "Mid"
    stats: Optional[UserStats] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
