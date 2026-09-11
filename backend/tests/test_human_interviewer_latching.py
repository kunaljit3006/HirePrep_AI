import pytest
from app.graph.graph import interview_graph

@pytest.mark.asyncio
async def test_human_interviewer_latches_on_keywords():
    """
    Verifies that when a candidate mentions a specific technology (e.g. Redis, Caching),
    the AI interviewer behaves like a real human:
    1. It detects the mention and initiates an organic probing follow-up.
    2. It does NOT skip to the next scheduled question yet.
    3. It asks specifically about the mentioned technology and trade-offs.
    4. Only after probing does it proceed to the next question.
    """
    config = {"configurable": {"thread_id": "test-human-latching-001"}}

    # State at question 0
    state = {
        "interview_id": "intv-human-001",
        "user_id": "candidate-001",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Amazon",
        "role": "SDE-2",
        "location": "India",
        "duration_min": 30,
        "questions": [
            {
                "id": "q1",
                "round_type": "system_design",
                "topic": "High-Throughput Architecture",
                "title": "Design a Scalable Service",
                "description": "How would you design a scalable backend for order processing?",
                "expected_key_points": ["Decoupling", "Caching", "Database indexing"]
            },
            {
                "id": "q2",
                "round_type": "coding",
                "topic": "Data Structures",
                "title": "Coding Problem",
                "description": "Reverse a linked list in O(N).",
                "expected_key_points": ["Three pointers"]
            }
        ],
        "current_question_idx": 0,
        "current_round": "system_design",
        "transcript": [],
        "latest_candidate_response": "To handle heavy read traffic, we implemented Redis for caching so queries don't hit Postgres.",
        "latest_interviewer_response": None,
        "current_score": 75.0,
        "difficulty_level": "medium",
        "follow_up_count": 0,
        "active_follow_up_topic": None,
        "violations": [],
        "body_language_samples": [],
        "code_submissions": [],
        "phase": "evaluate",
        "feedback_report": None
    }

    # Step 1: Evaluator evaluates the answer with "Redis" mentioned
    eval_state = await interview_graph.ainvoke(state, config=config)

    # Asserts human interviewer behavior:
    # 1. Did not advance question index prematurely (stays at question 0!)
    assert eval_state["current_question_idx"] == 0
    assert eval_state["follow_up_count"] == 1
    assert eval_state["active_follow_up_topic"] is not None
    assert "redis" in eval_state["active_follow_up_topic"].lower()

    # Step 2: The interviewer node should now produce a targeted question probing Redis!
    interviewer_response = eval_state.get("latest_interviewer_response", "")
    assert "redis" in interviewer_response.lower() or "cache" in interviewer_response.lower()
