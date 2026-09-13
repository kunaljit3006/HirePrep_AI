from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ProfileLinks(BaseModel):
    github: Optional[str] = None
    leetcode: Optional[str] = None
    codeforces: Optional[str] = None
    codechef: Optional[str] = None
    hackerrank: Optional[str] = None
    kaggle: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None

class ExperienceItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)

class ProjectItem(BaseModel):
    name: str
    description: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)

class EducationItem(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None

class ParsedResume(BaseModel):
    candidate_name: Optional[str] = None
    experience_level: Optional[str] = "Mid"
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: Dict[str, List[str]] = Field(default_factory=dict)  # {"Languages": [...], "Frameworks": [...], "Tools": [...]}
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    coding_profiles: ProfileLinks = Field(default_factory=ProfileLinks)
    raw_text: Optional[str] = None

class ResumeParseResponse(BaseModel):
    resume_id: str
    user_id: str
    data: ParsedResume
    detected_profiles: List[str] = Field(default_factory=list)
    created_at: str
