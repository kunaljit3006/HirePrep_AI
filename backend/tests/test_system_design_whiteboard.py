import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.connection import init_db
from app.services.question_service import question_service
from app.services.feedback_service import feedback_service
from app.models.interview import InterviewMessage
from app.graph.nodes.evaluate_response import evaluate_response_node

@pytest.mark.asyncio
async def test_conditional_whiteboard_activation():
    """
    Ensures that System Design Whiteboard is ONLY activated (requires_whiteboard=True)
    when role seniority/company scale is high (Senior, Staff, Architect, Lead, etc.),
    and remains a normal mock interview question (requires_whiteboard=False) for Junior/Intern roles.
    """
    # 1. High scale role: Staff Engineer at Big Tech -> Whiteboard REQUIRED
    senior_questions = await question_service.generate_question_bank(
        company="Google",
        role="Staff Distributed Systems Architect",
        location="India",
        tech_stack=["Kafka", "Kubernetes", "Redis", "Cassandra"]
    )
    senior_sys_design_qs = [q for q in senior_questions if q.round_type == "system_design"]
    assert len(senior_sys_design_qs) > 0
    for q in senior_sys_design_qs:
        assert q.requires_whiteboard is True
        assert q.whiteboard_mode in ["required", "optional"]

    # 2. Junior / Intern role -> Whiteboard NOT forced (normal mock question)
    junior_questions = await question_service.generate_question_bank(
        company="Startup",
        role="Junior Software Developer Intern",
        location="India",
        tech_stack=["Python", "Flask"]
    )
    junior_sys_design_qs = [q for q in junior_questions if q.round_type == "system_design"]
    for q in junior_sys_design_qs:
        assert q.requires_whiteboard is False
        assert q.whiteboard_mode == "none"

@pytest.mark.asyncio
async def test_submit_architecture_diagram_endpoint():
    """
    Tests REST endpoint POST /api/interview/{interview_id}/diagram
    evaluating load balancer, redis cache, postgres database, and detecting SPOF risks.
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start interview
        intv_payload = {
            "company": "Uber",
            "role": "Senior Backend Architect",
            "location": "India",
            "duration_min": 30,
            "difficulty": "hard"
        }
        start_res = await client.post("/api/interview/start", json=intv_payload)
        assert start_res.status_code == 200
        intv_data = start_res.json()
        interview_id = intv_data["interview_id"]

        # Submit architecture diagram
        diagram_payload = {
            "question_id": "q-sys-test",
            "diagram": {
                "components": [
                    {"id": "comp-1", "type": "client", "label": "Mobile App Client", "x": 50, "y": 100},
                    {"id": "comp-2", "type": "load_balancer", "label": "NGINX Load Balancer", "x": 200, "y": 100},
                    {"id": "comp-3", "type": "service", "label": "Ride Matching Microservice", "x": 400, "y": 100},
                    {"id": "comp-4", "type": "cache", "label": "Redis In-Memory Cache", "x": 600, "y": 50},
                    {"id": "comp-5", "type": "database", "label": "PostgreSQL Primary DB", "x": 600, "y": 150}
                ],
                "connections": [
                    {"from_id": "comp-1", "to_id": "comp-2", "label": "HTTPS REST"},
                    {"from_id": "comp-2", "to_id": "comp-3", "label": "gRPC"},
                    {"from_id": "comp-3", "to_id": "comp-4", "label": "Cache-aside read"},
                    {"from_id": "comp-3", "to_id": "comp-5", "label": "Write/Query"}
                ],
                "snapshot_url": "https://storage.example.com/diagrams/uber_arch_1.png"
            },
            "explanation": "Here is the high level design with NGINX ingress, Redis caching for active drivers, and Postgres storage."
        }

        res_diagram = await client.post(f"/api/interview/{interview_id}/diagram", json=diagram_payload)
        assert res_diagram.status_code == 200
        data = res_diagram.json()

        assert data["score"] >= 60.0
        assert len(data["strengths"]) > 0
        assert any("load balancer" in s.lower() or "caching" in s.lower() for s in data["strengths"])
        # Should detect single DB instance without replica as SPOF
        assert len(data["spof_risks"]) > 0
        assert data["suggested_follow_up"] is not None

@pytest.mark.asyncio
async def test_human_interviewer_latching_on_diagram():
    """
    Tests that evaluate_candidate_response node actively analyzes candidate's
    submitted whiteboard components and asks a targeted probing cross-question.
    """
    state = {
        "interview_id": "test-intv-123",
        "company": "Netflix",
        "role": "Staff Distributed Systems Engineer",
        "current_question_idx": 0,
        "questions": [
            {
                "id": "q-1",
                "round_type": "system_design",
                "question": "Design a high-throughput video streaming CDN",
                "description": "Design a resilient video distribution architecture handling 10M concurrent streams."
            }
        ],
        "transcript": [],
        "latest_candidate_response": "I placed an Edge Cache layer with Redis and a Kafka event queue to ingest viewing metrics.",
        "follow_up_count": 0,
        "active_follow_up_topic": None,
        "hint_count": 0,
        "hints_given": [],
        "diagram_data": {
            "components": [
                {"id": "c1", "type": "load_balancer", "label": "Cloudflare CDN Edge"},
                {"id": "c2", "type": "service", "label": "Video Catalog Service"},
                {"id": "c3", "type": "cache", "label": "Redis Cache Cluster"},
                {"id": "c4", "type": "queue", "label": "Kafka Event Bus"}
            ],
            "connections": []
        },
        "is_diagram_submission": True,
        "violations": []
    }

    result = await evaluate_response_node(state)
    assert "diagram_critique" in result
    critique = result["diagram_critique"]
    assert critique is not None
    assert "score" in critique
    assert "spof_risks" in critique
    assert "bottlenecks" in critique
    assert result["diagram_data"] is not None

@pytest.mark.asyncio
async def test_feedback_service_synthesizes_architecture_report():
    """
    Tests that feedback_service.generate_report synthesizes an architecture report
    with fault tolerance, scalability ratings, and technical recommendations.
    """
    diag = {
        "components": [
            {"id": "1", "type": "load_balancer", "label": "AWS ALB"},
            {"id": "2", "type": "service", "label": "API Gateway & Auth"},
            {"id": "3", "type": "cache", "label": "Redis Cache Cluster"},
            {"id": "4", "type": "database", "label": "Amazon Aurora Multi-AZ"}
        ]
    }
    critique = {
        "score": 88.0,
        "spof_risks": [],
        "bottlenecks": ["Cache cold start"],
        "strengths": ["Clear multi-AZ decoupling", "Edge caching included"],
        "critique": "Solid architecture with resilient high availability setup."
    }

    report = await feedback_service.generate_report(
        interview_id="intv-arch-test",
        user_id="user-arch-test",
        company="Amazon",
        role="Principal Systems Engineer",
        transcript=[
            InterviewMessage(role="interviewer", content="Please present your architecture.", timestamp=1726156800.0),
            InterviewMessage(role="candidate", content="Here is my multi-AZ scalable microservice design.", timestamp=1726156830.0)
        ],
        violations=[],
        body_language_samples=[],
        architecture_diagram=diag,
        architecture_critique=critique
    )

    assert report.architecture_report is not None
    arch = report.architecture_report
    assert arch.architecture_score == 88.0
    assert arch.scalability_rating == "High"
    assert arch.fault_tolerance == "High Availability"
    assert len(arch.strengths) > 0
    assert "bottlenecks" in arch.dict()
