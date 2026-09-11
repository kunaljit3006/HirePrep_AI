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


@pytest.mark.asyncio
async def test_human_interviewer_latches_on_multithreading():
    """
    Verifies that the human interviewer does NOT only latch onto tools (like Redis/Kafka),
    but latches onto ANY technical concept, OS principle, or concurrency paradigm
    such as 'multithreading', 'race conditions', or 'locks'.
    """
    config = {"configurable": {"thread_id": "test-multithreading-probe-002"}}

    state = {
        "interview_id": "intv-thread-002",
        "user_id": "candidate-002",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Google",
        "role": "Backend Engineer",
        "location": "India",
        "duration_min": 30,
        "questions": [
            {
                "id": "q1",
                "round_type": "cs_fundamentals",
                "topic": "Operating Systems & Concurrency",
                "title": "Optimizing Batch Processing",
                "description": "How would you speed up processing 10,000 files in memory?",
                "expected_key_points": ["I/O vs CPU bound", "Worker pools", "Race conditions"]
            }
        ],
        "current_question_idx": 0,
        "current_round": "cs_fundamentals",
        "transcript": [],
        "latest_candidate_response": "I solved this by introducing multithreading with a thread pool to process items concurrently in memory.",
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

    eval_state = await interview_graph.ainvoke(state, config=config)

    # Asserts that the interviewer latched onto 'multithreading'
    assert eval_state["current_question_idx"] == 0
    assert eval_state["follow_up_count"] == 1
    assert eval_state["active_follow_up_topic"] is not None
    assert "thread" in eval_state["active_follow_up_topic"].lower() or "concurrency" in eval_state["active_follow_up_topic"].lower()

    # Asserts that the spoken prompt directly challenges thread safety / synchronization
    spoken_question = eval_state.get("latest_interviewer_response", "")
    assert any(term in spoken_question.lower() for term in ["thread", "race", "synchronization", "concurrency"])
