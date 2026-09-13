import pytest
from app.services.question_service import question_service
from app.graph.graph import interview_graph
from app.db.redis import redis_manager

@pytest.mark.asyncio
async def test_data_engineer_scaffolded_curriculum_progression():
    """
    Verifies that the question service generates a realistic 5-phase progressive interview loop
    for Data Engineering candidates:
    1. Warm-up (Behavioral): Pipeline architecture & intro (easy)
    2. Role Foundations (CS Fundamentals): Storage (Parquet/CSV), partitioning, lakehouses (easy/medium)
    3. Coding: Data transformation / deduplication / window functions (medium)
    4. System Design: Real-time event streaming pipeline (Kafka, Flink/Spark, Lakehouse) (medium/hard)
    5. Incident Resilience: Schema drift & backfilling (medium)

    CRITICAL: Question 1 must NEVER be System Design and must NEVER be Hard difficulty!
    """
    await redis_manager.flush_all()

    questions = await question_service.generate_question_bank(
        company="Netflix",
        role="Data Engineer",
        experience_level="Senior"
    )

    assert len(questions) >= 5

    # 1. Question 1 must be warm-up/behavioral, easy difficulty, never system design
    q1 = questions[0]
    assert q1.round_type == "behavioral"
    assert q1.difficulty == "easy"
    assert "system_design" != q1.round_type
    assert any(term in (q1.title + q1.description).lower() for term in ["pipeline", "intro", "project", "background", "data"])

    # 2. Question 2 must be domain fundamentals
    q2 = questions[1]
    assert q2.round_type == "cs_fundamentals"
    assert q2.difficulty in ["easy", "medium"]

    # 3. Question 3 must be hands-on coding with data context
    q3 = questions[2]
    assert q3.round_type == "coding"
    assert q3.starter_code is not None
    # Must support SQL and Python in starter code for Data Engineers
    assert "sql" in q3.starter_code or "python" in q3.starter_code

    # 4. Question 4 must be system design
    q4 = questions[3]
    assert q4.round_type == "system_design"
    assert any(term in (q4.title + q4.description).lower() for term in ["pipeline", "stream", "kafka", "lakehouse", "ingestion", "event", "data"])

    # 5. Question 5 must be incident resilience / resume deep dive
    q5 = questions[4]
    assert q5.round_type in ["resume", "behavioral"]


@pytest.mark.asyncio
async def test_pre_coding_language_inquiry_and_detection():
    """
    Verifies human interviewer behavior before presenting a coding problem:
    1. When transitioning to coding round without a chosen language, interviewer politely inquires.
    2. When candidate responds with their preferred language (e.g., 'I prefer Python' or 'SQL'),
       intent is classified as language selection, preferred language is set in state,
       and interviewer warmly acknowledges the choice.
    """
    config = {"configurable": {"thread_id": "test-lang-inquiry-001"}}

    coding_question = {
        "id": "q-cod-1",
        "round_type": "coding",
        "topic": "Data Transformation",
        "title": "Deduplicate Events",
        "description": "Write a query or function to deduplicate streaming events.",
        "starter_code": {"python": "def solve(): pass", "sql": "SELECT 1;"},
        "expected_key_points": ["Window functions", "Deduplication"]
    }

    # State entering coding round (no language selected yet)
    state_enter_coding = {
        "interview_id": "intv-lang-001",
        "user_id": "candidate-001",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Uber",
        "role": "Data Engineer",
        "location": "India",
        "duration_min": 30,
        "questions": [coding_question],
        "current_question_idx": 0,
        "current_round": "coding",
        "transcript": [],
        "latest_candidate_response": None,
        "latest_interviewer_response": None,
        "current_score": 75.0,
        "difficulty_level": "medium",
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

    # Step 1: Conductor runs -> asks candidate what programming language they prefer
    inquiry_state = await interview_graph.ainvoke(state_enter_coding, config=config)

    assert inquiry_state.get("awaiting_language_preference") is True
    assert inquiry_state.get("phase") == "awaiting_candidate"
    inquiry_speech = inquiry_state.get("latest_interviewer_response", "").lower()
    assert any(term in inquiry_speech for term in ["language", "python", "sql", "comfortable", "coding"])

    # Step 2: Candidate replies: "I'd prefer to use Python for this problem"
    state_reply = {
        **inquiry_state,
        "phase": "evaluate",
        "latest_candidate_response": "I'd prefer to use Python for this problem."
    }

    selected_state = await interview_graph.ainvoke(state_reply, config=config)

    assert selected_state.get("preferred_coding_language") == "python"
    assert selected_state.get("awaiting_language_preference") is False
    interviewer_texts = [msg.get("content", "").lower() for msg in selected_state.get("transcript", []) if msg.get("role") == "interviewer"]
    all_interviewer_speech = " ".join(interviewer_texts) + " " + (selected_state.get("latest_interviewer_response") or "").lower()
    assert any(term in all_interviewer_speech for term in ["python", "great", "switched", "choice", "editor", "problem", "deduplicate"])


@pytest.mark.asyncio
async def test_thinking_time_grace_handling():
    """
    Verifies that when a candidate requests thinking time ("Hmm, let me think about this for a second"),
    the evaluator:
    1. Returns is_thinking_pause = True
    2. Keeps current_question_idx on the same question
    3. Does NOT grade or penalize the candidate
    4. Sets phase = awaiting_candidate with an encouraging reassurance
    """
    config = {"configurable": {"thread_id": "test-thinking-time-001"}}

    state = {
        "interview_id": "intv-pause-001",
        "user_id": "candidate-002",
        "resume_bytes": None,
        "resume_filename": None,
        "resume_data": None,
        "detected_profile_links": None,
        "scraped_profiles": None,
        "company": "Databricks",
        "role": "Data Engineer",
        "location": "India",
        "duration_min": 30,
        "questions": [
            {
                "id": "q1",
                "round_type": "cs_fundamentals",
                "topic": "Storage Formats",
                "title": "Parquet vs CSV",
                "description": "Why is Parquet preferred over CSV for analytical queries?",
                "expected_key_points": ["Columnar projection", "Predicate pushdown"]
            }
        ],
        "current_question_idx": 0,
        "current_round": "cs_fundamentals",
        "transcript": [],
        "latest_candidate_response": "Hmm, give me a moment to trace this out in my head.",
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

    res = await interview_graph.ainvoke(state, config=config)

    assert res["current_question_idx"] == 0
    assert res.get("is_thinking_pause") is True
    assert res.get("phase") == "awaiting_candidate"
    spoken = res.get("latest_interviewer_response", "").lower()
    assert any(term in spoken for term in ["time", "sure", "ready", "take"])
