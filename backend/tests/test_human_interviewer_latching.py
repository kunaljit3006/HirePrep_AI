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
    assert any(term in eval_state["active_follow_up_topic"].lower() for term in ["redis", "cache", "postgres", "decoupling", "order"])

    # Step 2: The interviewer node should now produce a targeted question probing Redis / Caching!
    interviewer_response = eval_state.get("latest_interviewer_response", "")
    assert len(interviewer_response) > 0
    assert any(term in interviewer_response.lower() for term in ["redis", "cache", "order", "postgres", "queue", "system", "decoupling"])


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


@pytest.mark.asyncio
async def test_human_interviewer_handles_candidate_clarification():
    """
    Verifies that when a candidate asks a clarifying question (e.g. 'Do we have to write
    the brute force first or direct optimal solution?'), the AI interviewer behaves like
    a real human:
    1. Detects that the candidate is clarifying approach/scope, NOT giving an answer.
    2. Does NOT score or penalize the question yet.
    3. Does NOT advance current_question_idx to the next question.
    4. Answers the clarification directly, supportively, and conversationally.
    5. Returns phase = 'awaiting_candidate' so the candidate can now proceed with their answer/code.
    """
    config = {"configurable": {"thread_id": "test-clarification-003"}}

    state = {
        "interview_id": "intv-clarify-003",
        "user_id": "candidate-003",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Microsoft",
        "role": "Software Engineer",
        "location": "India",
        "duration_min": 30,
        "questions": [
            {
                "id": "q1",
                "round_type": "coding",
                "topic": "Algorithms",
                "title": "Two Sum / Pair Sum",
                "description": "Find two numbers in an array that add up to a target sum.",
                "expected_key_points": ["Hash Map O(N)", "Two pointers if sorted"]
            },
            {
                "id": "q2",
                "round_type": "system_design",
                "topic": "Distributed Cache",
                "title": "Cache Design",
                "description": "Design an LRU cache.",
                "expected_key_points": ["Hash map + Doubly linked list"]
            }
        ],
        "current_question_idx": 0,
        "current_round": "coding",
        "transcript": [],
        "latest_candidate_response": "Do we have to write the brute force first or direct optimal solution?",
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

    # 1. State must stay on question 0 (do NOT skip or advance!)
    assert eval_state["current_question_idx"] == 0

    # 2. Must recognize this was a clarifying question
    assert eval_state.get("is_clarification") is True

    # 3. Phase must be awaiting_candidate so candidate can now code/answer
    assert eval_state.get("phase") == "awaiting_candidate"

    # 4. Spoken interviewer response must answer the clarification directly
    clarification_spoken = eval_state.get("latest_interviewer_response", "")
    assert any(term in clarification_spoken.lower() for term in ["brute force", "optimal", "code", "ready"])


@pytest.mark.asyncio
async def test_human_interviewer_handles_hint_request():
    """
    Verifies that when a candidate asks for a hint:
    1. It detects intent = 'hint_request'.
    2. Delivers Tier 1 graduated hint (intuition nudge).
    3. Keeps current_question_idx on the same question (does NOT skip).
    4. Sets phase = 'awaiting_candidate' so candidate can use the hint to code/answer.
    5. On a second hint request, increments to Tier 2 hint.
    """
    config = {"configurable": {"thread_id": "test-hint-004"}}

    state = {
        "interview_id": "intv-hint-004",
        "user_id": "candidate-004",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Google",
        "role": "Software Engineer",
        "location": "India",
        "duration_min": 30,
        "interviewer_persona": "google_staff",
        "questions": [
            {
                "id": "q1",
                "round_type": "coding",
                "topic": "Algorithms",
                "title": "Two Sum",
                "description": "Find two numbers in array that add to target.",
                "expected_key_points": ["Hash map O(N)"]
            }
        ],
        "current_question_idx": 0,
        "current_round": "coding",
        "transcript": [],
        "latest_candidate_response": "I'm a bit stuck on how to avoid the O(N^2) brute force. Can I get a small hint or pointer?",
        "latest_interviewer_response": None,
        "current_score": 75.0,
        "difficulty_level": "medium",
        "follow_up_count": 0,
        "active_follow_up_topic": None,
        "is_clarification": False,
        "hint_count": 0,
        "hints_given": [],
        "violations": [],
        "body_language_samples": [],
        "code_submissions": [],
        "phase": "evaluate",
        "feedback_report": None
    }

    # Step 1: Candidate requests Hint Tier 1
    eval_state = await interview_graph.ainvoke(state, config=config)

    assert eval_state["current_question_idx"] == 0
    assert eval_state.get("is_hint") is True
    assert eval_state.get("hint_tier") == 1
    assert eval_state.get("hint_count") == 1
    assert eval_state.get("phase") == "awaiting_candidate"
    assert len(eval_state.get("hints_given", [])) == 1

    spoken_hint = eval_state.get("latest_interviewer_response", "")
    assert any(term in spoken_hint.lower() for term in ["pointer", "hash map", "two pointers", "lookup", "hint"])

    # Step 2: Candidate asks for a second hint on the same question -> Tier 2
    state_step2 = dict(eval_state)
    state_step2["latest_candidate_response"] = "Could you give me another hint on how to structure the state?"
    state_step2["phase"] = "evaluate"

    eval_state2 = await interview_graph.ainvoke(state_step2, config=config)

    assert eval_state2["current_question_idx"] == 0
    assert eval_state2.get("is_hint") is True
    assert eval_state2.get("hint_tier") == 2
    assert eval_state2.get("hint_count") == 2
    assert eval_state2.get("phase") == "awaiting_candidate"
    assert len(eval_state2.get("hints_given", [])) == 2


@pytest.mark.asyncio
async def test_human_interviewer_live_approach_affirmation_right_track():
    """
    Verifies that when a candidate is working on a DSA problem and thinks out loud
    or checks their approach (e.g., 'I am thinking of using two pointers from both ends... Am I on the right track?'),
    the AI interviewer behaves like an encouraging senior engineer:
    1. Detects approach check / in-progress thought process.
    2. Validates whether the approach is sound and provides immediate affirmative coaching ('Yes, exactly! You are on the right track...').
    3. Does NOT advance question index or penalize the candidate.
    4. Sets track_status='on_track' and is_approach_check=True.
    """
    config = {"configurable": {"thread_id": "test-approach-affirmation-005"}}

    state = {
        "interview_id": "intv-approach-001",
        "user_id": "candidate-001",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Google",
        "role": "Software Engineer",
        "location": "India",
        "duration_min": 30,
        "questions": [
            {
                "id": "q1",
                "round_type": "coding",
                "topic": "Algorithms",
                "title": "Two Sum Sorted",
                "description": "Given a 1-indexed array of integers sorted in non-decreasing order, find two numbers that add up to target.",
                "expected_key_points": ["Two pointers", "O(N) time complexity", "O(1) space complexity"]
            }
        ],
        "current_question_idx": 0,
        "current_round": "coding",
        "transcript": [],
        "latest_candidate_response": "I am thinking of using a two-pointer approach starting from both ends to find the pair. Am I on the right track?",
        "latest_interviewer_response": None,
        "current_score": 75.0,
        "difficulty_level": "medium",
        "follow_up_count": 0,
        "active_follow_up_topic": None,
        "is_clarification": False,
        "is_hint": False,
        "is_approach_check": False,
        "track_status": None,
        "hint_count": 0,
        "hints_given": [],
        "violations": [],
        "body_language_samples": [],
        "code_submissions": [],
        "phase": "evaluate",
        "feedback_report": None
    }

    eval_state = await interview_graph.ainvoke(state, config=config)

    # 1. Did not advance question index
    assert eval_state["current_question_idx"] == 0
    # 2. Identified as approach check
    assert eval_state.get("is_approach_check") is True
    # 3. Track status is on_track or partially_on_track
    assert eval_state.get("track_status") in ["on_track", "partially_on_track"]
    # 4. Provided positive verbal affirmation
    spoken_affirmation = eval_state.get("latest_interviewer_response", "")
    assert len(spoken_affirmation) > 0
    assert any(w in spoken_affirmation.lower() for w in ["yes", "track", "right", "good", "exactly", "pointer", "optimal"])
    assert eval_state.get("phase") == "awaiting_candidate"

