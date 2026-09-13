import time
import json
import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.services.llm_service import llm_service

logger = logging.getLogger("hireprep.node.evaluate_response")

async def evaluate_response_node(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluate Response Node:
    1. Detects whether candidate is cross-asking/clarifying (e.g. brute force vs optimal, constraints, scope)
       or providing their technical answer.
    2. If clarifying: responds supportively as a human interviewer, stays on the same question, and awaits their code/answer.
    3. If answering: evaluates score, adapts difficulty, and checks for dynamic concept latching (e.g. multithreading, redis).
    """
    questions = state.get("questions", [])
    idx = state.get("current_question_idx", 0)
    current_q = questions[idx] if idx < len(questions) else {}
    candidate_answer = state.get("latest_candidate_response", "")

    follow_ups_done = state.get("follow_up_count", 0)
    hint_count = state.get("hint_count", 0)
    hints_given = list(state.get("hints_given", []))
    diagram_data = state.get("diagram_data")
    awaiting_lang = state.get("awaiting_language_preference", False)
    preferred_lang = state.get("preferred_coding_language")

    lower_ans = candidate_answer.lower().strip()

    # ── 0. EMPTY / INAUDIBLE RESPONSE GUARD ──
    if not lower_ans or len(lower_ans) < 3:
        logger.info("Empty candidate response received. Prompting candidate gently.")
        nudge = "Take your time! Whenever you're ready, feel free to speak or type your thoughts."
        return {
            "latest_interviewer_response": nudge,
            "current_question_idx": idx,
            "current_round": current_q.get("round_type", "behavioral"),
            "phase": "awaiting_candidate"
        }

    # ── 1. PRE-CODING LANGUAGE SELECTION DETECTION ──
    # If the candidate was asked what language they prefer, or specifies a language before coding
    detected_lang = None
    if "python" in lower_ans:
        detected_lang = "python"
    elif "sql" in lower_ans:
        detected_lang = "sql"
    elif "javascript" in lower_ans or " js" in lower_ans or lower_ans == "js":
        detected_lang = "javascript"
    elif "c++" in lower_ans or "cpp" in lower_ans:
        detected_lang = "cpp"
    elif "java" in lower_ans:
        detected_lang = "java"

    if (awaiting_lang or (current_q.get("round_type") == "coding" and not preferred_lang)) and detected_lang:
        logger.info(f"Candidate selected preferred coding language: {detected_lang}")
        transcript = list(state.get("transcript", []))
        lang_ack = (
            f"Awesome, {detected_lang.upper() if detected_lang == 'sql' else detected_lang.title()} is a great choice! "
            f"I've switched your editor over. Let's take a look at the problem statement, and feel free to ask any clarifying questions about constraints before writing code."
        )
        interviewer_msg = {
            "role": "interviewer",
            "content": lang_ack,
            "round_type": "coding",
            "question_idx": idx,
            "preferred_coding_language": detected_lang,
            "timestamp": time.time()
        }
        transcript.append(interviewer_msg)
        return {
            "transcript": transcript,
            "latest_interviewer_response": lang_ack,
            "preferred_coding_language": detected_lang,
            "awaiting_language_preference": False,
            "current_question_idx": idx,
            "current_round": "coding",
            "follow_up_count": 0,
            "active_follow_up_topic": None,
            "is_clarification": False,
            "is_hint": False,
            "hint_count": 0,
            "hints_given": hints_given,
            "diagram_data": diagram_data,
            "diagram_critique": None,
            "phase": "interview"  # Conductor will now present the coding question description
        }

    # ── 2. THINKING TIME / PAUSE HANDLING ──
    # Candidates often say "let me think for a second" or "give me a moment"
    is_pause_request = any(p in lower_ans for p in [
        "let me think", "give me a moment", "give me a sec", "give me a minute",
        "one second", "one moment", "just thinking", "thinking through", "hang on a sec"
    ])
    if is_pause_request:
        logger.info(f"Candidate requested thinking pause on question {idx + 1}")
        transcript = list(state.get("transcript", []))
        pause_ack = "Sure thing, take your time! Let me know as soon as you're ready to share your thought process."
        interviewer_msg = {
            "role": "interviewer",
            "content": pause_ack,
            "round_type": current_q.get("round_type", "general"),
            "question_idx": idx,
            "is_thinking_pause": True,
            "timestamp": time.time()
        }
        transcript.append(interviewer_msg)
        return {
            "transcript": transcript,
            "latest_interviewer_response": pause_ack,
            "is_thinking_pause": True,
            "is_clarification": False,
            "is_hint": False,
            "hint_count": hint_count,
            "hints_given": hints_given,
            "current_question_idx": idx,
            "current_round": current_q.get("round_type", "behavioral"),
            "follow_up_count": follow_ups_done,
            "active_follow_up_topic": None,
            "diagram_data": diagram_data,
            "diagram_critique": None,
            "phase": "awaiting_candidate"
        }

    diagram_summary = ""
    if diagram_data:
        comps = [f"{c.get('type', 'component')}: {c.get('label', '')}" for c in diagram_data.get("components", [])]
        conns = [f"{c.get('from_id')} -> {c.get('to_id')} ({c.get('protocol', 'HTTP')})" for c in diagram_data.get("connections", [])]
        diagram_summary = (
            f"\n\nCandidate Interactive Whiteboard / System Design Diagram:\n"
            f"- Drawn Components ({len(comps)}): {', '.join(comps) if comps else 'None drawn yet'}\n"
            f"- Architecture Data Flows: {', '.join(conns) if conns else 'None specified'}\n"
            f"- Candidate Diagram Notes: {diagram_data.get('notes', 'None')}\n"
        )

    prompt = (
        f"You are a Senior Staff Engineer conducting a technical mock interview at {state.get('company')} for a {state.get('role')} role.\n"
        f"Round Type: {current_q.get('round_type', 'general')}\n"
        f"Question: {current_q.get('title')} - {current_q.get('description')}\n"
        f"Expected Key Points: {', '.join(current_q.get('expected_key_points', []))}\n"
        f"{diagram_summary}\n"
        f"Candidate Said / Presented:\n{candidate_answer}\n\n"
        "Instructions:\n"
        "Step 1: CLASSIFY CANDIDATE INTENT:\n"
        "Determine if the candidate is:\n"
        "- 'approach_check': Explicitly checking their direction, asking if they are on the right track, or proposing a tentative approach/diagram before finishing "
        "(e.g. 'Am I on the right track with this approach/diagram?', 'I am thinking of using Redis between API gateway and Postgres, does that make sense?', 'Would binary search work here?').\n"
        "- 'clarification': Asking about constraints, edge cases, traffic volume, SLA, brute force vs optimal requirements, or format "
        "(e.g. 'Should I write brute force first or optimal?', 'What is the read-to-write ratio?', 'Are duplicates allowed?').\n"
        "- 'hint_request': Stuck, having difficulty, or asking for a hint or guidance "
        "(e.g. 'Can I get a hint?', 'I am stuck on how to handle high write traffic', 'Could you give me a pointer?').\n"
        "- 'answer': Describing their technical design, explaining past implementations/technologies, presenting their whiteboard diagram, or writing code "
        "(e.g. 'Here is my architecture: clients hit an ALB which routes to microservices. For caching, I placed Redis in front of Postgres.').\n\n"
        "Step 2: LIVE COACHING, PHONETIC TOLERANCE, & BEHAVIORAL CHECKS\n"
        "- **Phonetic & Typo Tolerance**: Overlook speech-to-text transcription errors (e.g., 'read is' -> Redis, 'ama-john' -> Amazon, 'sequel' -> SQL). Evaluate the technical intent, do not penalize for typos.\n"
        "- **Live Logic & Calculation Correction**: If the candidate makes a minor calculation error (e.g. 'sorting is O(N^2)') or a logic flaw (e.g. 'cache behind the DB') while explaining an 'answer', set 'logic_correction' to a gentle 1-sentence interjection (e.g. 'Wait, just to double check, wouldn't sorting take O(N log N)?'). Otherwise null.\n"
        "- **Tangent Detection**: If the candidate provides a long answer that doesn't address the core topic, set 'is_tangent'=true.\n"
        "- **Empathy & Sentiment**: If the candidate explicitly says they are blanking, nervous, or sorry, set 'sentiment'='struggling_emotionally'. Otherwise 'neutral'.\n"
        "- **STAR Format Check**: IF Round Type is 'behavioral', explicitly check if their answer contains a Situation, Task, Action, and Result. If they missed the Result/Impact, set 'missing_star_component'='result' and set 'probe_topic' to ask for it. Otherwise null.\n\n"
        "Step 3: GENERATE ROUTING & FEEDBACK\n"
        "IF INTENT IS 'approach_check':\n"
        "- Act like an attentive, encouraging human interviewer observing their thought process or whiteboard/code.\n"
        "- Evaluate whether their proposed approach/diagram is sound and on the right track for this problem:\n"
        "  * 'on_track': Their chosen algorithm/architecture directly leads to the optimal solution. Set 'track_status'='on_track'.\n"
        "    Provide an affirming, enthusiastic verbal nudge in 'affirmation_content'. If evaluating a diagram, affirm the components they got right.\n"
        "  * 'partially_on_track': Solid baseline but introduces a potential bottleneck or missing layer (e.g. missing cache or message queue). Set 'track_status'='partially_on_track'.\n"
        "    Affirm their good intuition, then offer gentle directional guidance in 'affirmation_content'.\n"
        "  * 'off_track': Severe anti-pattern or constraint violation. Set 'track_status'='off_track'. Steer them politely in 'affirmation_content'.\n"
        "- Set score=null, feedback='Candidate verified approach/direction.', difficulty_adjustment='same', probe_topic=null.\n\n"
        f"IF INTENT IS 'hint_request' (Current Tier: {hint_count + 1}/3):\n"
        "- Act like a supportive, realistic human interviewer offering graduated guidance:\n"
        f"  * Tier 1 (hint_count=0): High-level intuition nudge pointing to the algorithmic pattern or architectural layer (e.g., in-memory cache, decoupled message queue, hash map).\n"
        f"  * Tier 2 (hint_count=1): Structural pointer indicating what invariant or state to maintain (e.g., cache-aside pattern, worker consumers, read replicas).\n"
        f"  * Tier 3 (hint_count>=2): Concrete algorithmic edge-case or step-by-step guidance.\n"
        "- Provide warm, encouraging guidance in 'hint_content' (1 to 2 sentences max).\n"
        "- Set score=null, feedback='Candidate requested a hint.', difficulty_adjustment='same', probe_topic=null.\n\n"
        "IF INTENT IS 'clarification':\n"
        "- Act like a supportive, realistic human interviewer sitting across from them.\n"
        "- Provide a natural, encouraging 1-2 sentence response in 'clarification_answer' directly answering their question (e.g. advising whether to write brute force or optimal code, or clarifying constraints).\n"
        "- Set score=null, feedback='Candidate asked a clarifying question.', difficulty_adjustment='same', probe_topic=null.\n\n"
        "IF INTENT IS 'answer':\n"
        "1. Score response (0.0 to 100.0). NOTE: If this is question 1 (Warm-up / Behavioral background), evaluate communication, ownership, and background smoothly without penalizing for technical depth.\n"
        "2. Decide difficulty adjustment ('easier', 'same', 'harder').\n"
        f"3. ACTIVE LISTENING & DEPTH PROBING:\n"
        f"   - If the candidate's answer is objectively incorrect or fundamentally flawed, you MUST set 'probe_topic' to 'incorrect_answer' so the interviewer can gently challenge them or offer a hint.\n"
        f"   - If the candidate's answer is very short, vague, or incomplete, you MUST set 'probe_topic' to 'elaboration_needed' so the interviewer can ask them to clarify.\n"
        f"   - If they mentioned specific technical concepts (multithreading, locks, kafka, parquet, spark, delta lake, partitioning, redis, sharding) and follow_ups_done={follow_ups_done} < 2, "
        f"     PRIORITIZE probing on their exact choices. Provide a 'probe_topic' with the exact subject to challenge them on.\n"
        f"   - Otherwise set 'probe_topic' to null.\n"
        "4. If evaluating a system design diagram, list any 'spof_risks' and 'bottlenecks'.\n"
        "5. ADAPTIVE SIGNALS (REQUIRED for 'answer' intent):\n"
        "   - 'answer_depth': How thorough was the answer? 'shallow' (surface-level, buzzword-dropping), 'adequate' (solid but no extras), 'deep' (thorough with edge cases and trade-offs).\n"
        "   - 'concept_gaps': List specific concepts the candidate was weak on or missed (e.g., ['cache invalidation', 'race conditions']). Empty list if none.\n"
        "   - 'strengths': List specific concepts the candidate demonstrated mastery of (e.g., ['hash maps', 'SQL joins']). Empty list if none.\n"
        "   - 'next_question_guidance': A short instruction for the next question. Examples: 'Ask a simpler follow-up on OOP basics', 'They aced this - escalate to distributed systems', 'Probe their weak understanding of concurrency'.\n\n"
        "Return pure JSON:\n"
        '{"intent": "approach_check"|"clarification"|"hint_request"|"answer", "affirmation_content": string|null, "track_status": "on_track"|"partially_on_track"|"off_track"|null, "clarification_answer": string|null, "hint_content": string|null, "score": float|null, "feedback": string, "difficulty_adjustment": "easier"|"same"|"harder", "probe_topic": string|null, "answer_depth": "shallow"|"adequate"|"deep"|null, "concept_gaps": [string], "strengths": [string], "next_question_guidance": string|null, "spof_risks": [string], "bottlenecks": [string], "logic_correction": string|null, "is_tangent": boolean, "sentiment": "struggling_emotionally"|"neutral", "missing_star_component": string|null}'
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Classify intent and evaluate candidate response or clarify or provide hint."}
    ]

    try:
        llm_res = await llm_service.call("evaluate_response", messages)
        import re
        # Strip reasoning models' <think>...</think> tags (e.g. Qwen / DeepSeek)
        cleaned_json = re.sub(r"<think>.*?</think>", "", (llm_res or "").strip(), flags=re.DOTALL).strip()
        cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
        # Extract outermost JSON object if surrounded by preamble
        json_match = re.search(r"(\{.*\})", cleaned_json, re.DOTALL)
        if json_match:
            cleaned_json = json_match.group(1)
        eval_dict = json.loads(cleaned_json)
        intent = eval_dict.get("intent", "answer")
        clarification_answer = eval_dict.get("clarification_answer")
        hint_content = eval_dict.get("hint_content")
        affirmation_content = eval_dict.get("affirmation_content")
        track_status = eval_dict.get("track_status", "on_track")
        score = float(eval_dict.get("score")) if eval_dict.get("score") is not None else 75.0
        probe_topic = eval_dict.get("probe_topic")
        spof_risks = eval_dict.get("spof_risks", [])
        bottlenecks = eval_dict.get("bottlenecks", [])
        answer_depth = eval_dict.get("answer_depth", "adequate")
        concept_gaps_new = eval_dict.get("concept_gaps", [])
        strengths_new = eval_dict.get("strengths", [])
        next_q_guidance = eval_dict.get("next_question_guidance")
        
        logic_correction = eval_dict.get("logic_correction")
        is_tangent = eval_dict.get("is_tangent", False)
        sentiment = eval_dict.get("sentiment", "neutral")
        missing_star_component = eval_dict.get("missing_star_component")
    except Exception:
        # Heuristic intent & probing fallback if external LLM provider quota is momentarily exceeded
        if any(h in lower_ans for h in ["hint", "stuck", "pointer", "clue", "nudge"]):
            intent = "hint_request"
            hint_content = "Consider analyzing the bottleneck or trading O(N) space using a hash table to achieve O(1) lookups."
            clarification_answer = None
            affirmation_content = None
            track_status = None
            score = 75.0
            probe_topic = None
        elif any(c in lower_ans for c in ["clarify", "brute force", "direct optimal", "allowed", "should i", "can i"]):
            intent = "clarification"
            clarification_answer = "Good question! Feel free to outline the brute force approach briefly, then implement the optimal solution directly in code."
            hint_content = None
            affirmation_content = None
            track_status = None
            score = 75.0
            probe_topic = None
        elif any(a in lower_ans for a in ["right track", "correct direction", "am i on", "good approach"]):
            intent = "approach_check"
            affirmation_content = "Yes, exactly! You are on the right track with that approach. Continue fleshing it out."
            track_status = "on_track"
            clarification_answer = None
            hint_content = None
            score = 75.0
            probe_topic = None
        else:
            intent = "answer"
            clarification_answer = None
            hint_content = None
            affirmation_content = None
            track_status = None
            score = 85.0 if idx == 0 else 75.0
            if "redis" in lower_ans:
                probe_topic = "Redis Caching"
            elif "multithreading" in lower_ans or "concurrency" in lower_ans:
                probe_topic = "Multithreading & Concurrency"
            elif "kafka" in lower_ans:
                probe_topic = "Kafka Message Queue"
            elif "parquet" in lower_ans:
                probe_topic = "Parquet Columnar Storage"
            elif "spark" in lower_ans or "pyspark" in lower_ans:
                probe_topic = "Spark Stream Processing"
            elif "partition" in lower_ans:
                probe_topic = "Partitioning Strategy"
            elif "lakehouse" in lower_ans or "delta" in lower_ans or "iceberg" in lower_ans:
                probe_topic = "Lakehouse Architecture"
            else:
                probe_topic = None

        answer_depth = "adequate"
        concept_gaps_new = []
        strengths_new = []
        next_q_guidance = None
        logic_correction = None
        is_tangent = False
        sentiment = "neutral"
        missing_star_component = None

        spof_risks = ["Single database instance presents a SPOF"] if diagram_data else []
        bottlenecks = ["Potential read saturation under peak traffic"] if diagram_data else []
        eval_dict = {}

    diagram_critique = None
    if diagram_data:
        diagram_critique = {
            "score": score if intent == "answer" else None,
            "spof_risks": spof_risks,
            "bottlenecks": bottlenecks,
            "feedback": affirmation_content or hint_content or eval_dict.get("feedback", "Architecture analyzed.")
        }

    # Handle Candidate In-Progress Approach Check / Right-Track Guidance
    if intent == "approach_check" and affirmation_content:
        logger.info(f"Candidate checked approach/direction on Question {idx + 1}. Track status: {track_status}")
        transcript = list(state.get("transcript", []))
        interviewer_msg = {
            "role": "interviewer",
            "content": affirmation_content,
            "round_type": current_q.get("round_type", "general"),
            "question_idx": idx,
            "is_approach_check": True,
            "track_status": track_status,
            "timestamp": time.time()
        }
        transcript.append(interviewer_msg)
        return {
            "transcript": transcript,
            "latest_interviewer_response": affirmation_content,
            "is_approach_check": True,
            "track_status": track_status,
            "is_clarification": False,
            "is_hint": False,
            "hint_count": hint_count,
            "hints_given": hints_given,
            "current_question_idx": idx,
            "current_round": current_q.get("round_type", "behavioral"),
            "follow_up_count": follow_ups_done,
            "active_follow_up_topic": None,
            "diagram_data": diagram_data,
            "diagram_critique": diagram_critique,
            "phase": "awaiting_candidate"
        }

    # Handle Candidate Hint Request
    if intent == "hint_request" and hint_content:
        new_hint_count = hint_count + 1
        hints_given.append(hint_content)
        logger.info(f"Delivered Tier {new_hint_count} hint to candidate on question {idx + 1}")
        transcript = list(state.get("transcript", []))
        interviewer_msg = {
            "role": "interviewer",
            "content": hint_content,
            "round_type": current_q.get("round_type", "general"),
            "question_idx": idx,
            "is_hint": True,
            "hint_tier": new_hint_count,
            "timestamp": time.time()
        }
        transcript.append(interviewer_msg)
        return {
            "transcript": transcript,
            "latest_interviewer_response": hint_content,
            "is_hint": True,
            "hint_tier": new_hint_count,
            "hint_count": new_hint_count,
            "hints_given": hints_given,
            "is_clarification": False,
            "current_question_idx": idx,
            "current_round": current_q.get("round_type", "behavioral"),
            "follow_up_count": follow_ups_done,
            "active_follow_up_topic": None,
            "diagram_data": diagram_data,
            "diagram_critique": diagram_critique,
            "phase": "awaiting_candidate"
        }

    # Handle Candidate Clarification / Cross-Questioning
    if intent == "clarification" and clarification_answer:
        logger.info(f"Candidate asked a clarifying question on Question {idx + 1}: '{candidate_answer}'. Answering directly.")
        transcript = list(state.get("transcript", []))
        interviewer_msg = {
            "role": "interviewer",
            "content": clarification_answer,
            "round_type": current_q.get("round_type", "general"),
            "question_idx": idx,
            "is_clarification": True,
            "timestamp": time.time()
        }
        transcript.append(interviewer_msg)
        return {
            "transcript": transcript,
            "latest_interviewer_response": clarification_answer,
            "is_clarification": True,
            "is_hint": False,
            "hint_count": hint_count,
            "hints_given": hints_given,
            "current_question_idx": idx,
            "current_round": current_q.get("round_type", "behavioral"),
            "follow_up_count": follow_ups_done,
            "active_follow_up_topic": None,
            "diagram_data": diagram_data,
            "diagram_critique": diagram_critique,
            "phase": "awaiting_candidate"
        }

    # Route difficulty dynamically for regular answers
    if score < 40.0:
        new_difficulty = "easy"
    elif score > 70.0:
        new_difficulty = "hard"
    else:
        new_difficulty = "medium"

    # Cumulative performance tracking
    score_history = list(state.get("score_history", []))
    existing_gaps = list(state.get("concept_gaps", []))
    existing_strengths = list(state.get("candidate_strengths", []))
    topics_covered = list(state.get("topics_covered", []))
    questions_asked = state.get("questions_asked_count", 0)

    if intent == "answer":
        score_history.append({
            "question_idx": idx,
            "round_type": current_q.get("round_type", "general"),
            "score": score,
            "answer_depth": answer_depth,
            "topic": current_q.get("topic", "")
        })
        # Merge concept gaps and strengths (deduplicated)
        for g in concept_gaps_new:
            if g and g not in existing_gaps:
                existing_gaps.append(g)
        for s in strengths_new:
            if s and s not in existing_strengths:
                existing_strengths.append(s)
        # Track topic as covered
        topic = current_q.get("topic", "")
        if topic and topic not in topics_covered:
            topics_covered.append(topic)
        questions_asked += 1

    # Calculate cumulative performance from recent scores
    recent_scores = [sh["score"] for sh in score_history[-4:] if sh.get("score") is not None]
    if recent_scores:
        avg_score = sum(recent_scores) / len(recent_scores)
        if avg_score < 45:
            cumulative_perf = "struggling"
        elif avg_score > 70:
            cumulative_perf = "excelling"
        else:
            cumulative_perf = "average"
    else:
        cumulative_perf = "average"

    # Human Interviewer Latching Rule: If candidate mentioned an interesting tech/concept and hasn't been probed enough (< 2 follow-ups):
    should_probe = bool(probe_topic and follow_ups_done < 2)

    if should_probe:
        next_idx = idx
        next_follow_up_count = follow_ups_done + 1
        active_topic = probe_topic
        next_phase = "interview"
        next_round = current_q.get("round_type", "behavioral")
        next_hint_count = hint_count
        logger.info(f"Human Interviewer Probing activated on question {idx + 1}: Latching onto '{probe_topic}'")
    else:
        next_idx = idx + 1
        next_follow_up_count = 0
        active_topic = None
        next_hint_count = 0  # Reset hint count for the new question
        has_next = next_idx < len(questions)
        next_phase = "interview" if has_next else "feedback"
        next_round = questions[next_idx].get("round_type", "behavioral") if has_next else "done"
        logger.info(f"Question {idx + 1} scored: {score}. Depth: {answer_depth}. Cumulative: {cumulative_perf}. Next phase: {next_phase}")

    return {
        "current_score": score,
        "difficulty_level": new_difficulty,
        "current_question_idx": next_idx,
        "current_round": next_round,
        "follow_up_count": next_follow_up_count,
        "active_follow_up_topic": active_topic,
        "is_clarification": False,
        "is_hint": False,
        "hint_count": next_hint_count,
        "hints_given": hints_given,
        "preferred_coding_language": preferred_lang,
        "awaiting_language_preference": False,
        "diagram_data": diagram_data,
        "diagram_critique": diagram_critique,
        "phase": next_phase,
        "answer_depth": answer_depth,
        "concept_gaps": existing_gaps,
        "candidate_strengths": existing_strengths,
        "next_question_guidance": next_q_guidance,
        "cumulative_performance": cumulative_perf,
        "score_history": score_history,
        "questions_asked_count": questions_asked,
        "topics_covered": topics_covered,
        "logic_correction": logic_correction,
        "is_tangent": is_tangent,
        "candidate_sentiment": sentiment,
        "missing_star_component": missing_star_component,
    }
