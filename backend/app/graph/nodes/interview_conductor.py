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

    active_probe = state.get("active_follow_up_topic")
    latest_candidate_answer = state.get("latest_candidate_response", "")

    if active_probe:
        prompt = (
            f"You are a perceptive human technical interviewer at {state.get('company')} ({state.get('role')}).\n"
            f"The candidate just answered: \"{latest_candidate_answer}\"\n"
            f"HUMAN INTERVIEWER RULE: You noticed they specifically mentioned or relied on: '{active_probe}'.\n"
            "Do NOT move on to a generic new question yet. Instead, act like a real human interviewer who was actively listening:\n"
            f"- Latch onto their exact mention of '{active_probe}'.\n"
            f"- Ask a natural, sharp technical follow-up exploring why they chose it, trade-offs, or how it works internally.\n"
            "- Example style: 'You mentioned Redis and caching there—can you tell me why you opted for Redis specifically, and how you handle cache staleness?'\n"
            "- Speak naturally, concisely (1-2 sentences), and conversationally.\n"
        )
        user_prompt = f"Ask a human follow-up probing their mention of: {active_probe}"
    else:
        prompt = (
            f"You are the senior technical interviewer conducting a mock interview for {state.get('company')} ({state.get('role')}).\n"
            f"Current Round: {round_type.upper()}\n"
            f"Topic: {current_q.get('topic')}\n"
            f"Difficulty: {state.get('difficulty_level', 'medium')}\n"
            f"Question Details:\n{current_q.get('description')}\n\n"
            "Instructions:\n"
            "- Speak directly and professionally as a human interviewer.\n"
            "- If introducing the question, present it clearly and invite the candidate to share their thoughts or write code.\n"
            "- Keep your question concise (2 to 3 sentences).\n"
        )
        user_prompt = f"Please ask the candidate about: {current_q.get('title')} ({current_q.get('description')})"

    messages = [
        {"role": "system", "content": prompt}
    ]
    for msg in transcript[-4:]:
        role = "assistant" if msg["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": user_prompt
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
