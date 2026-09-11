import pytest
from app.graph.graph import interview_graph

SAMPLE_RESUME = """
Ankit Verma
Senior Backend Engineer
GitHub: https://github.com/ankitverma
LeetCode: https://leetcode.com/u/ankit_v
Skills: Python, Go, Kubernetes, Kafka, PostgreSQL
Experience:
Senior Software Engineer at ScaleWorks
Built low latency Kafka event streaming ingestion pipeline.
"""

@pytest.mark.asyncio
async def test_langgraph_full_orchestration():
    # Initial state
    initial_state = {
        "interview_id": "test-langgraph-001",
        "user_id": "candidate-001",
        "resume_bytes": SAMPLE_RESUME.encode("utf-8"),
        "resume_filename": "resume.txt",
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Amazon",
        "role": "SDE-2",
        "location": "India",
        "duration_min": 30,
        "questions": [],
        "current_question_idx": 0,
        "current_round": "behavioral",
        "transcript": [],
        "latest_candidate_response": None,
        "latest_interviewer_response": None,
        "current_score": 0.0,
        "difficulty_level": "medium",
        "violations": [],
        "body_language_samples": [],
        "code_submissions": [],
        "phase": "setup",
        "feedback_report": None
    }

    config = {"configurable": {"thread_id": "test-langgraph-001"}}

    # Turn 1: Resume Parser -> Scraper -> Prep -> Interview
    result_state = await interview_graph.ainvoke(initial_state, config=config)

    assert result_state.get("resume_data") is not None
    assert len(result_state.get("questions", [])) > 0
    assert result_state.get("phase") in ["awaiting_candidate", "interview", "evaluate", "done"]

    # Turn 2: Simulate candidate answering question
    answer_state = {
        **result_state,
        "phase": "evaluate",
        "latest_candidate_response": "I designed the partition key strategy using customer IDs to guarantee strict ordering."
    }

    eval_result = await interview_graph.ainvoke(answer_state, config=config)
    assert eval_result.get("current_score") > 0
    assert eval_result.get("difficulty_level") in ["easy", "medium", "hard"]
