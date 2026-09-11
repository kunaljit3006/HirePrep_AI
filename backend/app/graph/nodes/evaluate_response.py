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

    prompt = (
        f"You are a Senior Staff Engineer conducting a technical mock interview at {state.get('company')} for a {state.get('role')} role.\n"
        f"Question: {current_q.get('title')} - {current_q.get('description')}\n"
        f"Expected Key Points: {', '.join(current_q.get('expected_key_points', []))}\n\n"
        f"Candidate Said:\n{candidate_answer}\n\n"
        "Instructions:\n"
        "Step 1: CLASSIFY CANDIDATE INTENT:\n"
        "Determine if the candidate is answering the question, OR asking a clarifying question / cross-asking you:\n"
        "- 'clarification': Candidate is asking about approach, constraints, edge cases, scope, or methodology "
        "(e.g. 'Should I write brute force first or optimal?', 'Do we need to write brute force first or direct optimal solution?', "
        "'Are duplicates allowed?', 'Can we assume positive integers?', 'Should I write pseudocode or full code?').\n"
        "- 'answer': Candidate is explaining their technical solution, writing code, or answering the problem.\n\n"
        "Step 2:\n"
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
        f"     provide a 'probe_topic' with the exact subject and angle to challenge them on.\n"
        f"   - Otherwise set 'probe_topic' to null.\n"
        "Return pure JSON:\n"
        '{"intent": "clarification"|"answer", "clarification_answer": string|null, "score": float|null, "feedback": string, "difficulty_adjustment": "easier"|"same"|"harder", "probe_topic": string|null}'
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Classify intent and evaluate candidate response or clarify."}
    ]

    llm_res = await llm_service.call("evaluate_response", messages)

    try:
        import re
        cleaned_json = re.sub(r"^```json\s*", "", llm_res.strip())
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
        eval_dict = json.loads(cleaned_json)
        intent = eval_dict.get("intent", "answer")
        clarification_answer = eval_dict.get("clarification_answer")
        score = float(eval_dict.get("score")) if eval_dict.get("score") is not None else 75.0
        probe_topic = eval_dict.get("probe_topic")
    except Exception:
        intent = "answer"
        clarification_answer = None
        score = 75.0
        probe_topic = None

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
        logger.info(f"Human Interviewer Probing activated on question {idx + 1}: Latching onto '{probe_topic}'")
    else:
        next_idx = idx + 1
        next_follow_up_count = 0
        active_topic = None
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
        "phase": next_phase
    }
