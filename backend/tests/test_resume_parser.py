import pytest
from app.services.resume_service import resume_service

SAMPLE_RESUME_TEXT = """
Priya Sharma
Software Engineer | Full Stack Developer
Email: priya.sharma@example.com | Phone: +91 9876543210
Coding Profiles:
- GitHub: https://github.com/priyasharma
- LeetCode: https://leetcode.com/u/priya_coder
- Codeforces: https://codeforces.com/profile/priyacodes
- Kaggle: https://kaggle.com/priyadata

Skills: Python, FastAPI, React, PostgreSQL, Docker, Redis

Experience:
Software Engineer at TechCorp (2022 - Present)
- Designed real-time microservices using FastAPI and WebSockets.
- Optimized query execution plans reducing latency by 45%.

Projects:
CloudScale Distributed Cache
- Built an in-memory distributed key-value store in Python with Raft consensus.
"""

@pytest.mark.asyncio
async def test_detect_coding_profiles():
    profiles = resume_service.detect_coding_profiles(SAMPLE_RESUME_TEXT)
    assert profiles.github == "https://github.com/priyasharma"
    assert profiles.leetcode == "https://leetcode.com/u/priya_coder"
    assert profiles.codeforces == "https://codeforces.com/profile/priyacodes"
    assert profiles.kaggle == "https://kaggle.com/priyadata"
    assert profiles.codechef is None  # not in resume!

@pytest.mark.asyncio
async def test_parse_resume_content():
    parsed = await resume_service.parse_resume(SAMPLE_RESUME_TEXT.encode("utf-8"), "resume.txt")
    assert parsed.candidate_name is not None
    assert parsed.coding_profiles.github is not None
    assert parsed.coding_profiles.leetcode is not None
    assert len(parsed.skills) > 0 or len(parsed.projects) > 0
