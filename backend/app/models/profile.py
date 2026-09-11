from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class GitHubRepo(BaseModel):
    name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    url: str
    readme_content: Optional[str] = None
    file_tree: List[str] = Field(default_factory=list)

class GitHubData(BaseModel):
    username: str
    avatar_url: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    top_languages: List[str] = Field(default_factory=list)
    top_repositories: List[GitHubRepo] = Field(default_factory=list)
    total_stars: int = 0
    bio: Optional[str] = None

class LeetCodeData(BaseModel):
    username: str
    total_solved: int = 0
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    ranking: Optional[int] = None
    contest_rating: Optional[float] = None
    top_tags: List[str] = Field(default_factory=list)

class CodeforcesData(BaseModel):
    handle: str
    rating: Optional[int] = None
    max_rating: Optional[int] = None
    rank: Optional[str] = None
    max_rank: Optional[str] = None
    solved_count: Optional[int] = None

class CodeChefData(BaseModel):
    handle: str
    stars: Optional[str] = None
    rating: Optional[int] = None
    global_rank: Optional[int] = None

class KaggleData(BaseModel):
    username: str
    tier: Optional[str] = None
    competitions_count: Optional[int] = None
    notebooks_count: Optional[int] = None

class ScrapedProfilesData(BaseModel):
    user_id: str
    scanned_profiles: List[str] = Field(default_factory=list) # e.g. ["github", "leetcode"]
    github: Optional[GitHubData] = None
    leetcode: Optional[LeetCodeData] = None
    codeforces: Optional[CodeforcesData] = None
    codechef: Optional[CodeChefData] = None
    kaggle: Optional[KaggleData] = None
    summary_for_interviewer: Optional[str] = None
