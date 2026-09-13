import time
import logging
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from app.graph.state import InterviewState
from app.services.llm_service import llm_service

logger = logging.getLogger("hireprep.node.interview_conductor")

async def interview_conductor_node(state: InterviewState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Interview Conductor Node (Agent 4):
    Asks the current question or delivers an adaptive follow-up.
    """
    questions = state.get("questions", [])
    idx = state.get("current_question_idx", 0)
    transcript = list(state.get("transcript", []))

    is_qa_wrapup = state.get("is_qa_wrapup", False)

    if not questions or (idx >= len(questions) and is_qa_wrapup):
        logger.info("All questions and QA completed. Transitioning to feedback phase.")
        return {"phase": "feedback"}

    current_q = questions[idx] if idx < len(questions) else {"round_type": "qa", "topic": "Q&A", "description": "Candidate Q&A"}
    round_type = current_q.get("round_type", "general")
    preferred_lang = state.get("preferred_coding_language")
    awaiting_lang = state.get("awaiting_language_preference")

    active_probe = state.get("active_follow_up_topic")
    latest_candidate_answer = state.get("latest_candidate_response", "")
    persona = state.get("interviewer_persona", "standard")
    company = state.get("company", "our engineering team")
    role = state.get("role", "Software Engineer")

    # Adaptive Signals
    web_intel = state.get("web_intel_context", "")
    answer_depth = state.get("answer_depth")
    concept_gaps = state.get("concept_gaps", [])
    strengths = state.get("candidate_strengths", [])
    next_question_guidance = state.get("next_question_guidance")
    cumulative_perf = state.get("cumulative_performance", "average")
    round_focus = current_q.get("round_focus", "")
    
    logic_correction = state.get("logic_correction")
    is_tangent = state.get("is_tangent", False)
    candidate_sentiment = state.get("candidate_sentiment", "neutral")
    missing_star = state.get("missing_star_component")
    
    elapsed_min = 0
    if transcript:
        elapsed_min = int((time.time() - transcript[0].get("timestamp", time.time())) // 60)

    # ── RESUME & CANDIDATE CONTEXT ──
    resume_data = state.get("resume_data") or {}
    c_name = state.get("candidate_name") or resume_data.get("candidate_name") or resume_data.get("name") or "there"
    if str(c_name).strip().lower() in ["candidate", "none", "there", "null", "unknown"]:
        c_name = "there"
    projects = resume_data.get("projects") or []
    experience = resume_data.get("experience") or []
    skills_raw = resume_data.get("skills") or []
    skills_list = []
    if isinstance(skills_raw, dict):
        for val in skills_raw.values():
            if isinstance(val, list):
                skills_list.extend(val)
            elif isinstance(val, str):
                skills_list.append(val)
    elif isinstance(skills_raw, list):
        skills_list = skills_raw

    top_proj = projects[0] if projects else None
    top_proj_name = top_proj.get("name") if top_proj else None
    top_proj_tech = ", ".join(top_proj.get("tech_stack", [])[:3]) if top_proj else ""
    past_company = experience[0].get("company") if experience and experience[0].get("company") else None
    known_skills = ", ".join(skills_list[:5]) if skills_list else ""

    resume_summary_prompt = ""
    if top_proj_name:
        resume_summary_prompt += f"Candidate Name: {c_name}\nCandidate's Key Resume Project: '{top_proj_name}' (Tech: {top_proj_tech})\n"
    if past_company:
        resume_summary_prompt += f"Candidate's Prior Experience: at {past_company}\n"
    if known_skills:
        resume_summary_prompt += f"Candidate's Known Core Skills: {known_skills}\n"

    # ── PRE-CODING LANGUAGE INQUIRY ──
    # In real human interviews, interviewers ALWAYS confirm language comfort before presenting coding problems.
    if round_type == "coding" and not preferred_lang and not awaiting_lang:
        lang_prompt_text = (
            f"Before we dive into our hands-on problem, what programming language are you most comfortable using today? "
            f"We support Python, SQL, Java, C++, and JavaScript."
        )
        new_message = {
            "role": "interviewer",
            "content": lang_prompt_text,
            "round_type": "coding",
            "question_idx": idx,
            "is_language_prompt": True,
            "timestamp": time.time()
        }
        transcript.append(new_message)
        logger.info(f"Interviewer asked candidate for preferred programming language before question {idx + 1}")
        return {
            "transcript": transcript,
            "latest_interviewer_response": lang_prompt_text,
            "awaiting_language_preference": True,
            "current_round": "coding",
            "phase": "awaiting_candidate"
        }

    persona_guide = ""
    if persona == "amazon_bar_raiser":
        persona_guide = (
            "INTERVIEWER PERSONA (Amazon Bar Raiser):\n"
            "- Relentlessly probe for concrete metrics, quantifiable impact, and trade-offs.\n"
            "- Emphasize Amazon Leadership Principles (Customer Obsession, Ownership, Bias for Action, Disagree and Commit).\n\n"
        )
    elif persona == "google_staff":
        persona_guide = (
            "INTERVIEWER PERSONA (Google Senior Staff):\n"
            "- Probe deeply on asymptotic complexity, mathematical Big-O lower bounds, and distributed scalability bottlenecks.\n"
            "- Rigorously challenge assumptions and memory bounds.\n\n"
        )
    elif persona == "startup_cto":
        persona_guide = (
            "INTERVIEWER PERSONA (Fast-Paced Startup CTO):\n"
            "- Focus on execution speed, practical maintainability, simplicity, and debugging resiliency over theoretical over-engineering.\n\n"
        )

    # Conversational bridge based on progression and resume grounding
    stage_bridge = ""
    if idx == 0:
        if top_proj_name:
            stage_bridge = f"Warmly welcome {c_name} by name. Mention that you reviewed their CV and specifically noticed their work on '{top_proj_name}'. Ask them to introduce themselves and walk through that project."
        else:
            stage_bridge = f"Warmly welcome {c_name} by name, introduce yourself, and ease in with a warm-up question about their background and recent engineering work."
    elif round_type == "cs_fundamentals":
        stage_bridge = "Acknowledge their prior answer positively, and naturally bridge into testing core foundations and system trade-offs."
    elif round_type == "coding":
        stage_bridge = f"The candidate has chosen their language ({preferred_lang or 'Python'}). Present the coding problem clearly and warmly invite them to ask clarifying questions before writing code."
    elif round_type == "system_design":
        stage_bridge = "Transition enthusiastically to high-level architecture and system design. Encourage them to outline the end-to-end data flow."
    elif round_type == "resume":
        stage_bridge = "Transition to real-world operational resilience, handling failures, edge cases, and lessons learned from production."

    if idx >= len(questions) and not is_qa_wrapup:
        active_probe = "qa_wrapup"

    if active_probe == "qa_wrapup":
        prompt = (
            f"You are a Senior Technical Interviewer at {company}.\n"
            "HUMAN INTERVIEWER INSTRUCTIONS:\n"
            "1. Wrap up the technical portion of the interview gracefully.\n"
            f"2. Mention that we have a few minutes left (we are {elapsed_min} minutes in).\n"
            "3. Ask the candidate if they have any questions for you about the team, role, or culture.\n"
        )
        user_prompt = "Wrap up and ask if they have questions for you."

    if active_probe == "incorrect_answer":
        prompt = (
            f"You are a Senior Technical Interviewer at {company} interviewing for a {role} role.\n"
            f"{persona_guide}"
            f"Candidate's Name: {c_name}\n"
            f"{resume_summary_prompt}\n"
            f"Candidate's latest answer: \"{latest_candidate_answer}\"\n"
            f"ACTIVE LISTENING TRIGGER: The candidate's answer was objectively incorrect or fundamentally flawed.\n\n"
            "HUMAN INTERVIEWER INSTRUCTIONS:\n"
            "1. Speak naturally and conversationally, exactly like a real human interviewer.\n"
            "2. DO NOT validate their answer (do NOT say 'nice', 'great', or 'you are on the right track').\n"
            "3. Gently challenge their assumption or point out the flaw conversationally (e.g., 'Hmm, are you sure about that? What if...' or 'Actually, in that scenario...').\n"
            "4. Keep your response concise, warm, and encouraging (1 to 2 sentences max). Offer a hint if they seem completely stuck.\n"
            "5. Inject natural human disfluencies (e.g., 'Hmm...', 'Let's see here...', 'So...') to simulate thinking on the spot.\n"
        )
        user_prompt = "Gently challenge the incorrect answer or offer a hint."
    elif active_probe == "elaboration_needed":
        prompt = (
            f"You are a Senior Technical Interviewer at {company} interviewing for a {role} role.\n"
            f"{persona_guide}"
            f"Candidate's Name: {c_name}\n"
            f"{resume_summary_prompt}\n"
            f"Candidate's latest answer: \"{latest_candidate_answer}\"\n"
            f"ACTIVE LISTENING TRIGGER: You noticed their answer was very short, incomplete, or vague.\n\n"
            "HUMAN INTERVIEWER INSTRUCTIONS:\n"
            "1. Speak naturally and conversationally, exactly like a real human interviewer.\n"
            "2. DO NOT validate their answer as fully correct yet. Do NOT say 'nice' or 'you are on the right track' if they haven't actually answered the core problem.\n"
            "3. Gently ask them to elaborate (e.g., 'Could you go into a little more detail?' or 'How would that work under the hood?').\n"
            "4. Keep your question concise, warm, and encouraging (1 to 2 sentences max).\n"
            "5. Inject natural human disfluencies (e.g., 'Hmm...', 'Let's see here...', 'So...') to simulate thinking on the spot.\n"
        )
        user_prompt = "Ask an organic human follow-up asking them to elaborate."
    elif active_probe:
        prompt = (
            f"You are a Senior Technical Interviewer at {company} interviewing for a {role} role.\n"
            f"{persona_guide}"
            f"Candidate's Name: {c_name}\n"
            f"{resume_summary_prompt}\n"
            f"Candidate's latest answer: \"{latest_candidate_answer}\"\n"
            f"ACTIVE LISTENING TRIGGER: You noticed they mentioned or based their response on: '{active_probe}'.\n\n"
            "HUMAN INTERVIEWER INSTRUCTIONS:\n"
            "1. Speak naturally and conversationally, exactly like a real human interviewer.\n"
            "2. Start with a brief, organic human acknowledgment (e.g., 'Got it.', 'Understood.', 'Makes sense.', 'Fair point.', 'Interesting that you brought that up.').\n"
            f"3. Immediately latch onto their exact mention of '{active_probe}' and probe their technical depth. Test whether they truly understand how it works under the hood vs just dropping buzzwords.\n"
            "   - If they mentioned multithreading: ask how they handle synchronization, mutexes/locks, or race conditions.\n"
            "   - If they mentioned Redis/caching: ask why Redis over alternatives, and how they handle cache invalidation, stampedes, or staleness.\n"
            "   - If they mentioned Kafka/queues: ask how they ensure message ordering, idempotency, or handle consumer lag.\n"
            "   - If they mentioned database sharding/partitioning: ask about the partition key strategy or skew mitigation.\n"
            "   - If they mentioned Parquet/Lakehouse: ask about compression ratios, small file problems, or predicate pushdown.\n"
            "4. Keep your question concise, sharp, and realistic (1 to 2 sentences max). Never sound like a robot reading a script.\n"
            "5. Inject natural human disfluencies (e.g., 'Hmm...', 'Right...', 'So...') to simulate thinking on the spot.\n"
            "6. If the candidate goes on a tangent, gracefully acknowledge it and ask a quick follow-up before steering back, rather than rigidly forcing them back immediately.\n"
        )
        user_prompt = f"Ask an organic human follow-up probing their mention of: {active_probe}"
    else:
        adaptive_context = ""
        if answer_depth:
            adaptive_context += f"Last Answer Depth: {answer_depth}\n"
        if concept_gaps:
            adaptive_context += f"Candidate's Concept Gaps: {', '.join(concept_gaps)}\n"
        if strengths:
            adaptive_context += f"Candidate's Strengths: {', '.join(strengths)}\n"
        if cumulative_perf:
            adaptive_context += f"Cumulative Performance: {cumulative_perf}\n"
        if next_question_guidance:
            adaptive_context += f"Evaluation Guidance: {next_question_guidance}\n"
            
        coach_instructions = ""
        if candidate_sentiment == "struggling_emotionally":
            coach_instructions += "- EMPATHY OVERRIDE: The candidate is visibly nervous or blanking. Drop the strict persona. Offer a very warm, empathetic reassurance before asking the next question.\n"
        if is_tangent:
            coach_instructions += "- REDIRECTION OVERRIDE: The candidate went on a tangent. Politely interrupt and gracefully steer them back to the core constraints of the problem.\n"
        if logic_correction:
            coach_instructions += f"- LIVE COACHING OVERRIDE: The candidate made a logical/calculation error. Gently interject: '{logic_correction}' and ask what they think.\n"
        if missing_star:
            coach_instructions += f"- BEHAVIORAL COACHING: The candidate's behavioral answer missed the {missing_star}. Prompt them specifically for what the {missing_star} was.\n"

        prompt = (
            f"You are a Senior Staff Engineer and technical interviewer at {company} interviewing {c_name} for {role}.\n"
            f"{persona_guide}"
            f"CANDIDATE CV / RESUME CONTEXT:\n"
            f"{resume_summary_prompt or 'No CV details provided.'}\n"
            f"Current Round: {round_type.upper()}\n"
            f"Round Focus: {round_focus}\n"
            f"Topic: {current_q.get('topic')}\n"
            f"Difficulty: {state.get('difficulty_level', 'medium')}\n"
            f"Base Question Framework: {current_q.get('description')}\n"
            f"Stage Bridge Context: {stage_bridge}\n\n"
            "ADAPTIVE INTERVIEW SIGNALS:\n"
            f"{adaptive_context if adaptive_context else 'None (First Question)'}\n"
            f"Elapsed Interview Time: {elapsed_min} minutes.\n"
            "COMPANY-SPECIFIC INTERVIEW CONTEXT (From Web Intelligence):\n"
            f"{web_intel[:1000] if web_intel else 'None'}\n\n"
            "DYNAMIC DIFFICULTY & GENERATION RULES:\n"
            "- If this is Q1 or Q2: Ask a BASIC foundational question related to the topic (e.g., 'What is method overloading?' or 'Explain a linked list').\n"
            "- If the candidate's cumulative performance is 'struggling' or last answer was 'shallow': Stay at the same difficulty or go easier. Target their concept_gaps specifically.\n"
            "- If the candidate is 'excelling' or last answer was 'deep': Escalate difficulty. Ask about edge cases, trade-offs, or advanced patterns.\n"
            "- Use the Company-Specific Context to make questions feel like they're from an actual {company} interviewer.\n"
            "- The question topics, scenarios, and evaluation criteria should reflect what {company} actually asks.\n"
            "- NEVER jump to a hard question without the candidate demonstrating mastery at medium first.\n\n"
            f"{coach_instructions}\n"
            "HUMAN CONVERSATIONAL BRIDGING RULES:\n"
            "1. Deliver the question naturally, exactly as a human tech lead would on a video call or in-person interview.\n"
            "2. TRANSCRIPTION LENIENCY: You are reading raw, error-prone Speech-to-Text output. Do NOT take words literally if they don't fit the technical context. Phonetically deduce what the candidate actually meant. CRITICAL: Do NOT point out the typos, do NOT explain your deductions out loud, and do NOT break character to act like an AI assistant analyzing text. Silently deduce their intent and respond as a human interviewer continuing the conversation.\n"
            "3. Keep your response extremely concise (1-2 sentences) to ensure the fastest possible latency. Never read out question headers, IDs, or bullet points.\n"
            "4. Resume Grounding: If this is Question 1 or a resume deep-dive, explicitly cite their project or past background.\n"
            "5. Introducing 'Out-of-the-Box' Tools: If the question introduces a technology (e.g. Kafka, Redis, Parquet, Kubernetes) that may be new to their resume, bridge conversationally like a real human: e.g., 'Looking at your background, you've worked extensively with [their tech]. Here at [Company], we operate at scale with [tool]. Have you heard about or worked with [tool] before?'\n"
            "6. For coding or system design, warmly invite them: 'Feel free to ask any clarifying questions about constraints or scale before you dive in.'\n"
            "7. Inject natural human disfluencies (e.g., 'Hmm...', 'Let's see here...', 'So...') to simulate thinking on the spot.\n"
            "8. If the candidate goes on a tangent, gracefully acknowledge it and ask a quick follow-up before steering back, rather than rigidly forcing them back immediately.\n"
            "9. CRITICAL ANTI-ROBOT RULE: NEVER say things like 'I cannot evaluate this', 'Please provide the response', or break character. If the candidate's response is missing or confusing, just say 'I didn't quite catch that, could you repeat?' like a normal human.\n"
        )
        user_prompt = f"Present the next question naturally to {c_name} adapting based on their previous answers: {current_q.get('title')} ({current_q.get('description')})"

    messages = [
        {"role": "system", "content": prompt}
    ]
    for msg in transcript[-10:]:
        role = "assistant" if msg["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": user_prompt
    })

    send_chunk_cb = config.get("configurable", {}).get("send_chunk_cb")

    if send_chunk_cb:
        stream_gen = await llm_service.call("interview_conductor", messages, stream=True)
        import re
        ai_text = ""
        current_sentence = ""
        
        first_name = c_name.split()[0] if c_name and c_name.lower() not in ["candidate", "there", "none"] else ""
        target_rep = first_name if first_name else "there"
        
        async def process_sentence(sentence):
            sentence = re.sub(r"\[(?:first\s*name|candidate(?:\s*name)?|name)\]", target_rep, sentence, flags=re.IGNORECASE)
            sentence = re.sub(r"\[(?:your\s*name|interviewer(?:\s*name)?)\]", "I", sentence, flags=re.IGNORECASE)
            sentence = re.sub(r"\[(?:company)\]", company, sentence, flags=re.IGNORECASE)
            sentence = re.sub(r"\[.*?\]", "", sentence)
            sentence = re.sub(r"\s+", " ", sentence).strip()
            if sentence:
                await send_chunk_cb(sentence)
                return sentence
            return ""

        async for chunk in stream_gen:
            current_sentence += chunk
            if any(punct in chunk for punct in [". ", "? ", "! ", ".\n", "?\n", "!\n"]):
                boundary_idx = max([current_sentence.rfind(p) for p in [". ", "? ", "! ", ".\n", "?\n", "!\n"]])
                if boundary_idx != -1:
                    sentence = current_sentence[:boundary_idx+1]
                    processed = await process_sentence(sentence)
                    if processed:
                        ai_text += processed + " "
                    current_sentence = current_sentence[boundary_idx+1:]
        
        if current_sentence.strip():
            processed = await process_sentence(current_sentence)
            if processed:
                ai_text += processed
            
        ai_text = ai_text.strip()
    else:
        ai_text = await llm_service.call("interview_conductor", messages)
        # Filter meta-instruction bleed-through and sanitize placeholders
        bad_meta = ["share the candidate's response", "classify their intent", "as an ai", "as an assistant", "please provide the candidate"]
        if any(bm in (ai_text or "").lower() for bm in bad_meta):
            from app.services.azure_speech_service import clean_conversational_speech
            ai_text = clean_conversational_speech(current_q.get("description", ""))

        import re
        first_name = c_name.split()[0] if c_name and c_name.lower() not in ["candidate", "there", "none"] else ""
        target_rep = first_name if first_name else "there"
        ai_text = re.sub(r"\[(?:first\s*name|candidate(?:\s*name)?|name)\]", target_rep, ai_text, flags=re.IGNORECASE)
        ai_text = re.sub(r"\[(?:your\s*name|interviewer(?:\s*name)?)\]", "I", ai_text, flags=re.IGNORECASE)
        ai_text = re.sub(r"\[(?:company)\]", company, ai_text, flags=re.IGNORECASE)
        ai_text = re.sub(r"\[.*?\]", "", ai_text)
        ai_text = re.sub(r"\s+", " ", ai_text).strip()

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
        "awaiting_language_preference": False,
        "is_qa_wrapup": active_probe == "qa_wrapup",
        "phase": "awaiting_candidate"
    }
