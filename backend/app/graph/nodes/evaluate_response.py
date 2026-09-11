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

    prompt = (
        f"You are a Senior Staff Engineer conducting a technical mock interview at {state.get('company')} for a {state.get('role')} role.\n"
        f"Question: {current_q.get('title')} - {current_q.get('description')}\n"
        f"Expected Key Points: {', '.join(current_q.get('expected_key_points', []))}\n\n"
        f"Candidate Said:\n{candidate_answer}\n\n"
        "Instructions:\n"
        "Step 1: CLASSIFY CANDIDATE INTENT:\n"
        "Determine if the candidate is:\n"
        "- 'approach_check': Explicitly checking their direction, asking if they are on the right track, or proposing a tentative approach before implementing "
        "(e.g. 'Am I on the right track with this approach?', 'I am thinking of using a two-pointer approach, would that work?', 'Would binary search work here?', 'Does this approach make sense?').\n"
        "- 'clarification': Asking about constraints, edge cases, scope, brute force vs optimal requirements, or format "
        "(e.g. 'Should I write brute force first or optimal?', 'Are duplicates allowed?', 'Can we assume positive integers?').\n"
        "- 'hint_request': Stuck, having difficulty, or asking for a hint or guidance "
        "(e.g. 'Can I get a hint?', 'I am stuck on how to optimize space', 'Could you give me a small pointer on how to approach this?').\n"
        "- 'answer': Describing their technical design, explaining past implementations/technologies, writing code, or presenting their solution (e.g. 'To handle read traffic, we implemented Redis for caching so queries don't hit Postgres.').\n\n"
        "Step 2:\n"
        "IF INTENT IS 'approach_check':\n"
        "- Act like an attentive, encouraging human interviewer observing their thought process or whiteboard/code.\n"
        "- Evaluate whether their proposed approach/intuition is sound and on the right track for this problem:\n"
        "  * 'on_track': Their chosen algorithm/data structure/architecture directly leads to the optimal solution.\n"
        "    Set 'track_status'='on_track'.\n"
        "    Provide an affirming, enthusiastic verbal nudge in 'affirmation_content' (e.g., 'Yes, exactly! You\\'re on the right track with [technique]. That will give you optimal complexity. Go ahead and start implementing that!').\n"
        "  * 'partially_on_track': Their approach works for a baseline or has the right intuition, but might hit a bottleneck or edge case.\n"
        "    Set 'track_status'='partially_on_track'.\n"
        "    Affirm their good intuition, then offer a gentle directional guidance in 'affirmation_content' (e.g., 'Good intuition on [X]! That gives a solid baseline. Before you write code, consider if [alternative/optimization] could get us to optimal complexity.').\n"
        "  * 'off_track': Their approach introduces an anti-pattern or severe constraint violation.\n"
        "    Set 'track_status'='off_track'.\n"
        "    Politely steer them in 'affirmation_content' (e.g., 'Careful there—notice that [constraint/case]. Let\\'s take a step back and think about how [alternative concept] might apply.').\n"
        "- Set score=null, feedback='Candidate verified approach/direction.', difficulty_adjustment='same', probe_topic=null.\n\n"
        f"IF INTENT IS 'hint_request' (Current Tier: {hint_count + 1}/3):\n"
        "- Act like a supportive, realistic human interviewer offering graduated guidance:\n"
        f"  * Tier 1 (hint_count=0): High-level intuition nudge pointing to the algorithmic pattern or data structure (e.g. Hash Map, Sliding Window, Min-Heap).\n"
        f"  * Tier 2 (hint_count=1): Structural pointer indicating what invariant or state to maintain.\n"
        f"  * Tier 3 (hint_count>=2): Concrete algorithmic edge-case or step-by-step guidance.\n"
        "- Provide warm, encouraging guidance in 'hint_content' (1 to 2 sentences max).\n"
        "- Set score=null, feedback='Candidate requested a hint.', difficulty_adjustment='same', probe_topic=null.\n\n"
        "IF INTENT IS 'clarification':\n"
        "- Act like a supportive, realistic human interviewer sitting across from them.\n"
        "- Provide a natural, encouraging 1-2 sentence response in 'clarification_answer'.\n"
        "  * For brute force vs optimal: 'Good question! Feel free to outline the brute force intuition in 30 seconds so we are aligned on the baseline, but please implement the optimal solution in code.'\n"
        "  * For constraints/edge cases: Provide a clear, reasonable assumption and invite them to proceed.\n"
        "- Set score=null, feedback='Candidate asked a clarifying question.', difficulty_adjustment='same', probe_topic=null.\n\n"
        "IF INTENT IS 'answer':\n"
        "1. Score response (0.0 to 100.0).\n"
        "2. Decide difficulty adjustment ('easier', 'same', 'harder').\n"
        f"3. ACTIVE LISTENING & DEPTH PROBING:\n"
        f"   Did the candidate mention ANY specific technical concepts, concurrency/OS principles (e.g. multithreading, mutex/locks, race conditions), "
        f"   architectures (e.g. caching, Redis, Kafka, microservices, sharding), or algorithms?\n"
        f"   - If they dropped a concept and we have not probed them yet (follow_ups_done={follow_ups_done} < 2), "
        f"     PRIORITIZE probing on the exact technologies/concepts they explicitly mentioned in their answer (e.g. Redis, locks, sharding, Postgres) to test their depth of hands-on knowledge. "
        f"     Provide a 'probe_topic' with the exact subject and angle to challenge them on.\n"
        f"   - Otherwise set 'probe_topic' to null.\n"
        "Return pure JSON:\n"
        '{"intent": "approach_check"|"clarification"|"hint_request"|"answer", "affirmation_content": string|null, "track_status": "on_track"|"partially_on_track"|"off_track"|null, "clarification_answer": string|null, "hint_content": string|null, "score": float|null, "feedback": string, "difficulty_adjustment": "easier"|"same"|"harder", "probe_topic": string|null}'
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Classify intent and evaluate candidate response or clarify or provide hint."}
    ]

    llm_res = await llm_service.call("evaluate_response", messages)

    try:
        import re
        # Strip reasoning models' <think>...</think> tags (e.g. Qwen / DeepSeek)
        cleaned_json = re.sub(r"<think>.*?</think>", "", llm_res, flags=re.DOTALL).strip()
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
    except Exception:
        intent = "answer"
        clarification_answer = None
        hint_content = None
        affirmation_content = None
        track_status = None
        score = 75.0
        probe_topic = None

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
            "phase": "awaiting_candidate"
        }

    # Route difficulty dynamically for regular answers
    if score < 40.0:
        new_difficulty = "easy"
    elif score > 70.0:
        new_difficulty = "hard"
    else:
        new_difficulty = "medium"

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
        logger.info(f"Question {idx + 1} scored: {score}. Next difficulty: {new_difficulty}. Next phase: {next_phase}")

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
        "phase": next_phase
    }
