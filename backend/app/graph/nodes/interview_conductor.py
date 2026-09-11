import time
import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.services.llm_service import llm_service

logger = logging.getLogger("hireprep.node.interview_conductor")

async def interview_conductor_node(state: InterviewState) -> Dict[str, Any]:
    """
    Interview Conductor Node (Agent 4):
    Asks the current question or delivers an adaptive follow-up.
    """
    questions = state.get("questions", [])
    idx = state.get("current_question_idx", 0)
    transcript = list(state.get("transcript", []))

    if not questions or idx >= len(questions):
        logger.info("All questions completed. Transitioning to feedback phase.")
        return {"phase": "feedback"}

    current_q = questions[idx]
    round_type = current_q.get("round_type", "general")

    # If this is the start of this question or an ongoing follow-up
    prompt = (
        f"You are the senior technical interviewer conducting a mock interview for {state.get('company')} ({state.get('role')}).\n"
        f"Current Round: {round_type.upper()}\n"
        f"Topic: {current_q.get('topic')}\n"
        f"Difficulty: {state.get('difficulty_level', 'medium')}\n"
        f"Question Details:\n{current_q.get('description')}\n\n"
        "Instructions:\n"
        "- Speak directly and professionally as an interviewer.\n"
        "- If introducing the question, present it clearly and invite the candidate to share their thoughts or write code.\n"
        "- Keep your question or prompt concise (2 to 4 sentences).\n"
    )

    messages = [
        {"role": "system", "content": prompt}
    ]
    for msg in transcript[-4:]:
        role = "assistant" if msg["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"Please ask the candidate about: {current_q.get('title')} ({current_q.get('description')})"
    })

    ai_text = await llm_service.call("interview_conductor", messages)

    new_message = {
        "role": "interviewer",
        "content": ai_text,
        "round_type": round_type,
        "question_idx": idx,
        "timestamp": time.time()
    }
    transcript.append(new_message)

    return {
        "transcript": transcript,
        "latest_interviewer_response": ai_text,
        "current_round": round_type,
        "phase": "awaiting_candidate"
    }
