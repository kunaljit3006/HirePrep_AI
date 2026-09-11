import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.connection import init_db

@pytest.mark.asyncio
async def test_api_root_and_health():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Root System Info
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "operational"
        assert "Resume Parser (Agent 1)" in data["agents"]

        # 2. Health
        h_res = await client.get("/health")
        assert h_res.status_code == 200

@pytest.mark.asyncio
async def test_api_resume_and_interview_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload Resume
        resume_content = b"Priya Sharma\nEmail: priya@test.com\nGitHub: https://github.com/priyasharma\nLeetCode: https://leetcode.com/u/priya"
        files = {"file": ("resume.txt", resume_content, "text/plain")}
        res_upload = await client.post("/api/resume/upload", files=files)
        assert res_upload.status_code == 200
        resume_json = res_upload.json()
        resume_id = resume_json["resume_id"]
        assert resume_id is not None
        assert "github" in resume_json["detected_profiles"]

        # 2. Selective Profile Scrape from Resume
        res_scrape = await client.post(f"/api/profile/scrape-from-resume/{resume_id}")
        assert res_scrape.status_code == 200
        profile_json = res_scrape.json()
        assert "github" in profile_json["scanned_profiles"]

        # 3. Question Bank Generation
        q_payload = {
            "company": "Uber",
            "role": "Backend Engineer",
            "location": "India",
            "experience_level": "Mid",
            "tech_stack": ["Python", "Golang", "Kafka"]
        }
        res_q = await client.post(f"/api/question/generate?resume_id={resume_id}", json=q_payload)
        assert res_q.status_code == 200
        q_json = res_q.json()
        assert len(q_json["questions"]) > 0

        # 4. Start Interview
        intv_payload = {
            "company": "Uber",
            "role": "Backend Engineer",
            "location": "India",
            "duration_min": 30,
            "difficulty": "medium",
            "resume_id": resume_id
        }
        res_intv = await client.post("/api/interview/start", json=intv_payload)
        assert res_intv.status_code == 200
        intv_json = res_intv.json()
        interview_id = intv_json["interview_id"]
        assert interview_id is not None
        assert intv_json["status"] == "in_progress"

        # 5. Code Submission in Monaco Editor
        first_q_id = intv_json["questions"][0]["id"]
        code_payload = {
            "code": "def solution(): return True",
            "language": "python",
            "question_id": first_q_id
        }
        res_code = await client.post(f"/api/interview/{interview_id}/code", json=code_payload)
        assert res_code.status_code == 200

        # 6. Generate and Retrieve Feedback
        res_fb = await client.post(f"/api/feedback/{interview_id}/generate")
        assert res_fb.status_code == 200
        fb_json = res_fb.json()
        assert fb_json["overall_score"] > 0
        assert fb_json["letter_grade"] in ["A+", "A", "B+", "B", "C", "D", "F"]
        assert len(fb_json["section_scores"]) > 0
