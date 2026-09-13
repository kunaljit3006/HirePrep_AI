import pytest
import time
import datetime
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.connection import init_db, AsyncSessionLocal
from app.db.models import UserModel, InterviewModel, FeedbackReportModel
from app.services.auth_service import auth_service

@pytest.mark.asyncio
async def test_interview_history_and_analytics_endpoints():
    """
    Verifies:
    1. GET /api/interview/history returns candidate's past test history
    2. GET /api/feedback/user/history returns all past feedback reports
    3. GET /api/feedback/analytics/summary aggregates score trends and skills radar
    """
    await init_db()

    user_id = f"supa-history-user-{int(time.time()*1000)}"
    token = auth_service.create_mock_jwt(user_id=user_id, email="history.test@hireprep.ai")

    # Seed 2 completed interviews with feedback reports into SQLite
    async with AsyncSessionLocal() as db:
        # Interview 1: Amazon Backend SDE (Score: 88.0, Strong Hire)
        intv1_id = f"intv-hist-01-{int(time.time())}"
        intv1 = InterviewModel(
            id=intv1_id,
            user_id=user_id,
            company="Amazon",
            role="Backend SDE II",
            location="India",
            duration_min=30,
            difficulty="medium",
            status="completed",
            current_round="system_design",
            current_question_idx=4,
            questions=[],
            started_at=datetime.datetime.now(datetime.timezone.utc),
            ended_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(intv1)

        fb1 = FeedbackReportModel(
            id=f"fb-hist-01-{int(time.time())}",
            interview_id=intv1_id,
            user_id=user_id,
            overall_score=88.0,
            letter_grade="A",
            hire_recommendation="Strong Hire",
            section_scores=[
                {"section_name": "DSA & Problem Solving", "score": 90.0, "strengths": ["Optimal Big-O"], "weaknesses": [], "feedback": "Great"},
                {"section_name": "System Design", "score": 85.0, "strengths": ["Scalable partitioning"], "weaknesses": [], "feedback": "Solid"}
            ],
            communication={"clarity_score": 92.0, "conciseness_score": 88.0, "structure_score": 90.0, "confidence_score": 85.0, "filler_words_detected": [], "feedback": "Clear"},
            body_language={"overall_confidence_score": 85.0, "eye_contact_percentage": 90.0, "posture_stability_score": 88.0, "fidgeting_detected": False, "notes": []},
            proctoring={"integrity_score": 100.0, "total_violations": 0, "violations": [], "body_language_score": 88.0, "suspicious_events": []},
            strengths=["Optimal Time Complexity", "Clean Code Structure"],
            weaknesses=["Could clarify edge case upfront"],
            roadmap=[{"day": 1, "focus_topic": "Dynamic Programming", "action_items": ["Solve 2 Hard problems"], "curated_resources": []}],
            summary="Exceptional performance in algorithmic design."
        )
        db.add(fb1)

        # Interview 2: Google SWE (Score: 82.0, Hire)
        intv2_id = f"intv-hist-02-{int(time.time())}"
        intv2 = InterviewModel(
            id=intv2_id,
            user_id=user_id,
            company="Google",
            role="Software Engineer L4",
            location="India",
            duration_min=45,
            difficulty="hard",
            status="completed",
            current_round="dsa",
            current_question_idx=3,
            questions=[],
            started_at=datetime.datetime.now(datetime.timezone.utc),
            ended_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(intv2)

        fb2 = FeedbackReportModel(
            id=f"fb-hist-02-{int(time.time())}",
            interview_id=intv2_id,
            user_id=user_id,
            overall_score=82.0,
            letter_grade="B+",
            hire_recommendation="Hire",
            section_scores=[
                {"section_name": "DSA & Problem Solving", "score": 80.0, "strengths": ["Graph BFS/DFS"], "weaknesses": ["Space complexity"], "feedback": "Good"},
                {"section_name": "Behavioral & Leadership", "score": 85.0, "strengths": ["STAR method"], "weaknesses": [], "feedback": "Good"}
            ],
            communication={"clarity_score": 84.0, "conciseness_score": 80.0, "structure_score": 82.0, "confidence_score": 80.0, "filler_words_detected": [], "feedback": "Good"},
            body_language={"overall_confidence_score": 82.0, "eye_contact_percentage": 85.0, "posture_stability_score": 85.0, "fidgeting_detected": False, "notes": []},
            proctoring={"integrity_score": 95.0, "total_violations": 1, "violations": [], "body_language_score": 84.0, "suspicious_events": []},
            strengths=["Optimal Time Complexity", "Strong STAR examples"],
            weaknesses=["Memory optimization"],
            roadmap=[{"day": 1, "focus_topic": "Graphs", "action_items": ["Review Dijkstra"], "curated_resources": []}],
            summary="Strong problem solving with good communication."
        )
        db.add(fb2)

        # Interview 3: 9 days ago to test relative time formatting
        nine_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=9)
        intv3_id = f"intv-hist-03-{int(time.time())}"
        intv3 = InterviewModel(
            id=intv3_id,
            user_id=user_id,
            company="Microsoft",
            role="Software Engineer",
            location="India",
            duration_min=45,
            difficulty="medium",
            status="completed",
            current_round="dsa",
            current_question_idx=2,
            questions=[],
            created_at=nine_days_ago,
            started_at=nine_days_ago,
            ended_at=nine_days_ago + datetime.timedelta(minutes=45)
        )
        db.add(intv3)

        fb3 = FeedbackReportModel(
            id=f"fb-hist-03-{int(time.time())}",
            interview_id=intv3_id,
            user_id=user_id,
            overall_score=78.0,
            letter_grade="B",
            hire_recommendation="Leaning Hire",
            section_scores=[{"section_name": "DSA", "score": 78.0, "strengths": [], "weaknesses": [], "feedback": "Decent"}],
            communication={"clarity_score": 80.0, "conciseness_score": 75.0, "structure_score": 75.0, "confidence_score": 80.0, "filler_words_detected": [], "feedback": "Good"},
            body_language={"overall_confidence_score": 80.0, "eye_contact_percentage": 80.0, "posture_stability_score": 80.0, "fidgeting_detected": False, "notes": []},
            proctoring={"integrity_score": 90.0, "total_violations": 1, "violations": [], "body_language_score": 80.0, "suspicious_events": []},
            strengths=["Good communication"],
            weaknesses=["Dynamic programming edge cases"],
            roadmap=[],
            summary="Solid interview.",
            created_at=nine_days_ago
        )
        db.add(fb3)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test GET /api/interview/history
        res_intv = await client.get("/api/interview/history", headers={"Authorization": f"Bearer {token}"})
        assert res_intv.status_code == 200
        intv_list = res_intv.json()
        assert len(intv_list) >= 3

        # Check item fields and relative time formatting
        msft_intv = next(i for i in intv_list if i["company"] == "Microsoft")
        assert msft_intv["relative_time"] == "9 days ago"
        assert msft_intv["formatted_date"] is not None
        assert msft_intv["overall_score"] == 78.0
        assert msft_intv["letter_grade"] == "B"

        recent_intv = next(i for i in intv_list if i["company"] == "Amazon")
        assert recent_intv["relative_time"] == "Just now"

        # 2. Test GET /api/feedback/user/history
        res_fb = await client.get("/api/feedback/user/history", headers={"Authorization": f"Bearer {token}"})
        assert res_fb.status_code == 200
        fb_list = res_fb.json()
        assert len(fb_list) >= 3
        msft_fb = next(f for f in fb_list if f["interview_id"] == intv3_id)
        assert msft_fb["relative_time"] == "9 days ago"

        # 3. Test GET /api/feedback/analytics/summary
        res_analytics = await client.get("/api/feedback/analytics/summary", headers={"Authorization": f"Bearer {token}"})
        assert res_analytics.status_code == 200
        analytics = res_analytics.json()
        assert analytics["total_interviews_taken"] >= 3
        assert analytics["completed_interviews"] >= 3
        # Check trend points include relative_time
        msft_trend = next(t for t in analytics["score_trends"] if t["company"] == "Microsoft")
        assert msft_trend["relative_time"] == "9 days ago"
        assert msft_trend["date"] is not None
