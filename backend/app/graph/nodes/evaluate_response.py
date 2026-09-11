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

    prompt = (
        f"You are evaluating a candidate's response to the interview question:\n"
        f"Question: {current_q.get('title')} - {current_q.get('description')}\n"
        f"Expected Key Points: {', '.join(current_q.get('expected_key_points', []))}\n\n"
        f"Candidate Answer:\n{candidate_answer}\n\n"
        "Score the response from 0.0 to 100.0 and decide difficulty adjustment ('easier', 'same', 'harder').\n"
        "Return pure JSON:\n"
        '{"score": float, "feedback": string, "difficulty_adjustment": "easier" | "same" | "harder"}'
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Evaluate response."}
    ]

    llm_res = await llm_service.call("evaluate_response", messages)

    try:
        import re
        cleaned_json = re.sub(r"^```json\s*", "", llm_res.strip())
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
        eval_dict = json.loads(cleaned_json)
        score = float(eval_dict.get("score", 70.0))
    except Exception:
        score = 75.0

    # Route difficulty dynamically
    if score < 40.0:
        new_difficulty = "easy"
    elif score > 70.0:
        new_difficulty = "hard"
    else:
        new_difficulty = "medium"

    next_idx = idx + 1
    has_next = next_idx < len(questions)
    next_phase = "interview" if has_next else "feedback"
    next_round = questions[next_idx].get("round_type", "behavioral") if has_next else "done"

    logger.info(f"Question {idx + 1} scored: {score}. Next difficulty: {new_difficulty}. Next phase: {next_phase}")

    return {
        "current_score": score,
        "difficulty_level": new_difficulty,
        "current_question_idx": next_idx,
        "current_round": next_round,
        "phase": next_phase
    }
