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
            f"You are a Senior Staff Engineer and technical interviewer at {state.get('company')} interviewing a candidate for a {state.get('role')} role.\n"
            f"Candidate's latest answer: \"{latest_candidate_answer}\"\n"
            f"ACTIVE LISTENING TRIGGER: You noticed they mentioned or based their response on: '{active_probe}'.\n\n"
            "HUMAN INTERVIEWER INSTRUCTIONS:\n"
            "1. Speak naturally and conversationally, exactly like a real human interviewer at Google, Amazon, or Meta.\n"
            "2. Start with a brief, organic human acknowledgment (e.g., 'Got it.', 'Understood.', 'Makes sense.', 'Fair point.', 'Interesting that you brought that up.').\n"
            f"3. Immediately latch onto their exact mention of '{active_probe}' and probe their technical depth. Test whether they truly understand how it works under the hood vs just dropping buzzwords.\n"
            "   - If they mentioned multithreading: ask how they handle synchronization, mutexes/locks, or race conditions.\n"
            "   - If they mentioned Redis/caching: ask why Redis over alternatives, and how they handle cache invalidation, stampedes, or staleness.\n"
            "   - If they mentioned Kafka/queues: ask how they ensure message ordering, idempotency, or handle consumer lag.\n"
            "   - If they mentioned database sharding/indexing: ask about the shard key strategy or B-Tree indexing trade-offs.\n"
            "4. Keep your question concise, sharp, and realistic (1 to 2 sentences max). Never sound like a robot reading a script.\n"
        )
        user_prompt = f"Ask an organic human follow-up probing their mention of: {active_probe}"
    else:
        prompt = (
            f"You are a Senior Staff Engineer and technical interviewer at {state.get('company')} interviewing for {state.get('role')}.\n"
            f"Current Round: {round_type.upper()}\n"
            f"Topic: {current_q.get('topic')}\n"
            f"Difficulty: {state.get('difficulty_level', 'medium')}\n"
            f"Question: {current_q.get('description')}\n\n"
            "HUMAN INTERVIEWER INSTRUCTIONS:\n"
            "1. Deliver the question naturally, as if sitting across the table or on a live Zoom call.\n"
            "2. If transitioning from previous discussion, use a brief natural bridge (e.g., 'Good breakdown. Let's move to our next section:', 'Understood. Now shifting gears to...').\n"
            "3. State the problem clearly and warmly invite them to walk you through their thought process.\n"
            "4. Keep it concise (2 to 3 sentences max).\n"
        )
        user_prompt = f"Present the next question naturally to the candidate: {current_q.get('title')} ({current_q.get('description')})"

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
