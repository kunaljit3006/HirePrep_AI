import pytest
from app.models.resume import ParsedResume, ProjectItem, ExperienceItem
from app.services.question_service import question_service
from app.routes.interview import generate_dynamic_interview_intro
from app.graph.nodes.interview_conductor import interview_conductor_node

@pytest.mark.asyncio
async def test_dynamic_intro_cites_resume_project_and_name():
    persona = {"name": "Vikram Sharma", "title": "Staff Engineer", "voice": "en-IN-PrabhatNeural", "style": "encouraging"}
    resume_data = {
        "candidate_name": "Kunal Jit",
        "skills": {"Languages": ["Python", "SQL"], "Frameworks": ["Kafka", "Spark", "FastAPI"]},
        "projects": [
            {
                "name": "Realtime ClickStream Lakehouse",
                "tech_stack": ["Kafka", "Spark", "Delta Lake"],
                "description": "Ingested 50k events per second into Delta Lake."
            }
        ],
        "experience": [
            {"company": "Fintech Global", "title": "Senior Data Engineer"}
        ]
    }

    intro_text = await generate_dynamic_interview_intro(
        persona=persona,
        company="Stripe",
        role="Data Engineer",
        resume_data=resume_data,
        candidate_name="Kunal Jit"
    )

    assert "Kunal" in intro_text
    assert "Realtime ClickStream Lakehouse" in intro_text
    assert "Stripe" in intro_text
    assert len(intro_text.split()) >= 15


@pytest.mark.asyncio
async def test_question_service_interpolates_resume_project_in_warmup():
    resume = ParsedResume(
        candidate_name="Kunal Jit",
        email="kunal@example.com",
        skills={"Languages": ["Python", "SQL"], "Tools": ["Kafka"]},
        projects=[
            ProjectItem(
                name="Telemetry Ingestion Engine",
                tech_stack=["Kafka", "FastAPI", "PostgreSQL"],
                description="Built high-throughput telemetry ingestion."
            )
        ],
        experience=[
            ExperienceItem(company="CloudTech", title="Data Engineer")
        ]
    )

    questions = question_service._get_default_questions(
        company="Uber",
        role="Data Engineer",
        resume=resume,
        experience_level="Senior"
    )

    q1 = questions[0]
    assert q1.round_type == "behavioral"
    assert "Telemetry Ingestion Engine" in q1.title
    assert "Telemetry Ingestion Engine" in q1.description
    assert "Kunal" in q1.description


@pytest.mark.asyncio
async def test_interview_conductor_injects_resume_context():
    resume_data = {
        "candidate_name": "Kunal",
        "skills": {"Languages": ["Python"], "Tools": ["Kafka", "Spark"]},
        "projects": [
            {"name": "Distributed Fraud Detector", "tech_stack": ["Kafka", "Flink"]}
        ],
        "experience": [{"company": "AlphaBank"}]
    }

    state = {
        "interview_id": "test-cv-grounding-001",
        "user_id": "user-001",
        "resume_data": resume_data,
        "candidate_name": "Kunal",
        "company": "Netflix",
        "role": "Data Engineer",
        "questions": [
            {
                "id": "q1",
                "round_type": "behavioral",
                "topic": "Architecture",
                "title": "Architecture of Distributed Fraud Detector",
                "description": "Walk me through the architecture of Distributed Fraud Detector.",
            }
        ],
        "current_question_idx": 0,
        "current_round": "behavioral",
        "transcript": [],
        "latest_candidate_response": None,
        "latest_interviewer_response": None,
        "current_score": 75.0,
        "difficulty_level": "easy",
        "follow_up_count": 0,
        "active_follow_up_topic": None,
        "preferred_coding_language": None,
        "awaiting_language_preference": False,
        "violations": [],
        "body_language_samples": [],
        "code_submissions": [],
        "phase": "interview",
        "feedback_report": None
    }

    result = await interview_conductor_node(state)
    assert result["phase"] == "awaiting_candidate"
    response_text = result["latest_interviewer_response"]
    assert response_text is not None
    assert len(response_text.strip()) > 10


@pytest.mark.asyncio
async def test_auto_link_latest_resume_on_interview_start():
    import uuid
    import time
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.db.connection import init_db, AsyncSessionLocal
    from app.db.models import ResumeModel

    await init_db()

    user_id = f"test-cv-user-{uuid.uuid4().hex[:8]}"
    resume_id = f"res-test-{uuid.uuid4().hex[:8]}"

    parsed_sample = {
        "candidate_name": "Priya Sharma",
        "email": "priya@example.com",
        "phone": "+91 9876543210",
        "skills": {
            "Languages": ["Python", "Go"],
            "Tools": ["Docker", "Kubernetes", "Kafka"]
        },
        "experience": [
            {
                "company": "Swiggy",
                "title": "Backend Software Engineer",
                "start_date": "2022",
                "end_date": "Present",
                "description": "High-throughput delivery dispatch engine."
            }
        ],
        "projects": [
            {
                "name": "Distributed Order Orchestrator",
                "tech_stack": ["Go", "Kafka", "PostgreSQL"],
                "description": "Processes 30,000 order state transitions per second with idempotent saga patterns."
            }
        ],
        "education": [],
        "coding_profiles": {},
        "raw_text": "Priya Sharma Resume Swiggy Distributed Order Orchestrator"
    }

    async with AsyncSessionLocal() as db:
        resume = ResumeModel(
            id=resume_id,
            user_id=user_id,
            file_name="Priya_Sharma_Resume.pdf",
            raw_text=parsed_sample["raw_text"],
            parsed_data=parsed_sample,
            detected_profiles=[]
        )
        db.add(resume)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Verify GET /api/resume/latest returns the seeded resume
        latest_res = await client.get("/api/resume/latest", headers={"x-user-id": user_id})
        assert latest_res.status_code == 200
        latest_json = latest_res.json()
        assert latest_json["resume_id"] == resume_id
        assert latest_json["data"]["candidate_name"] == "Priya Sharma"

        # 2. Call POST /api/interview/start WITHOUT resume_id -> Should auto-link
        start_res = await client.post(
            "/api/interview/start",
            json={
                "company": "Zomato",
                "role": "Backend Engineer",
                "location": "India",
                "duration_min": 30,
                "difficulty": "medium"
            },
            headers={"x-user-id": user_id}
        )
        assert start_res.status_code == 200
        start_json = start_res.json()
        assert start_json["resume_id"] == resume_id
        questions = start_json.get("questions", [])
        assert len(questions) > 0

        # Verify Question 1 is personalized to Priya Sharma and her project
        q1 = questions[0]
        assert "Distributed Order Orchestrator" in q1["title"] or "Distributed Order Orchestrator" in q1["description"]
        assert "Priya" in q1["description"] or "Priya" in q1["title"]

