import json
import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.services.llm_service import llm_service

logger = logging.getLogger("hireprep.node.evaluate_response")

async def evaluate_response_node(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluate Response Node:
    Assesses the candidate's answer, computes a score (0-100),
    and adapts difficulty (score < 40 -> easy, 40-70 -> medium, > 70 -> hard).
    """
    questions = state.get("questions", [])
    idx = state.get("current_question_idx", 0)
    current_q = questions[idx] if idx < len(questions) else {}
    candidate_answer = state.get("latest_candidate_response", "")

    follow_ups_done = state.get("follow_up_count", 0)

    prompt = (
        f"You are a Senior Staff Engineer evaluating a candidate's response in an interview.\n"
        f"Question: {current_q.get('title')} - {current_q.get('description')}\n"
        f"Expected Key Points: {', '.join(current_q.get('expected_key_points', []))}\n\n"
        f"Candidate Answer:\n{candidate_answer}\n\n"
        "Instructions:\n"
        "1. Score response (0.0 to 100.0).\n"
        "2. Decide difficulty adjustment ('easier', 'same', 'harder').\n"
        f"3. ACTIVE LISTENING & DEPTH PROBING:\n"
        f"   Did the candidate mention ANY specific technical concepts, low-level OS/concurrency principles (e.g. multithreading, race conditions, mutex/locks, deadlocks, thread pools, async/event loop), "
        f"   architectural patterns (e.g. microservices, event-driven, pub/sub, sharding, replication, caching, load balancing), "
        f"   database internals (e.g. ACID, B-trees, indexing, isolation levels, connection pooling), "
        f"   algorithms/data structures (e.g. sliding window, dynamic programming, tries, graph traversal), "
        f"   or tools & infrastructure (e.g. Redis, Kafka, Docker, Kubernetes, Postgres, RabbitMQ)?\n"
        f"   - If they dropped a concept, tool, or approach and we have not probed them yet (follow_ups_done={follow_ups_done} < 2), "
        f"     provide a 'probe_topic' with the exact subject and angle to challenge them on (e.g., 'multithreading race conditions and synchronization', 'why Redis was chosen and cache invalidation strategy', 'Kafka message ordering and consumer lag').\n"
        f"   - If their answer was already completely thorough or we already probed enough, set 'probe_topic' to null.\n"
        "Return pure JSON:\n"
        '{"score": float, "feedback": string, "difficulty_adjustment": "easier"|"same"|"harder", "probe_topic": string | null}'
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Evaluate candidate response and determine if probing follow-up is needed."}
    ]

    llm_res = await llm_service.call("evaluate_response", messages)

    try:
        import re
        cleaned_json = re.sub(r"^```json\s*", "", llm_res.strip())
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
        eval_dict = json.loads(cleaned_json)
        score = float(eval_dict.get("score", 75.0))
        probe_topic = eval_dict.get("probe_topic")
    except Exception:
        score = 75.0
        probe_topic = None

    # Route difficulty dynamically
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
        "phase": next_phase
    }
