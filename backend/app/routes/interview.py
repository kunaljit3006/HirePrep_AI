import uuid
import json
import time
import datetime
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user_id
from app.db.connection import get_db, AsyncSessionLocal
from app.db.models import (
    InterviewModel, InterviewMessageModel, ProctoringViolationModel,
    ResumeModel, FeedbackReportModel
)
from app.models.interview import (
    CreateInterviewRequest, InterviewSessionResponse, CodeSubmissionRequest,
    CodeSubmissionResult, InterviewMessage, InterviewHistoryItem,
    DiagramSubmissionRequest, DiagramSubmissionResult
)
from app.models.question import QuestionItem
from app.models.proctoring import ProctoringViolation, BodyLanguageSample
from app.services.question_service import question_service, normalize_company_name
from app.services.code_runner_service import code_runner_service
from app.services.feedback_service import feedback_service
from app.services.azure_speech_service import azure_speech_service, clean_conversational_speech
from app.services.llm_service import llm_service
from app.graph.graph import interview_graph
from app.utils.date_utils import format_relative_time, format_friendly_date

logger = logging.getLogger("hireprep.interview")
router = APIRouter(prefix="/api/interview", tags=["Interview Session"])

async def generate_dynamic_interview_intro(
    persona: dict,
    company: str,
    role: str,
    resume_data: Optional[dict] = None,
    candidate_name: Optional[str] = None
) -> str:
    """
    Generates a natural, warm, conversational peer introduction using Gemini/LLM
    deeply personalized with the candidate's name, past company, and primary CV project.
    """
    persona_name = persona.get("name", "Vikram Sharma")
    persona_title = persona.get("title", "Staff Engineer")
    style = persona.get("style", "collaborative, warm senior engineer")

    c_name = candidate_name or (resume_data.get("candidate_name") if resume_data else None) or ""
    c_name = c_name.strip()
    if c_name.lower() in ["candidate", "none", "there", "null", "unknown"]:
        c_name = ""

    first_name = c_name.split()[0] if c_name else ""
    greeting_name = first_name if first_name else "there"

    top_project = None
    if resume_data and resume_data.get("projects"):
        top_project = resume_data["projects"][0]
    past_company = None
    if resume_data and resume_data.get("experience"):
        past_company = resume_data["experience"][0].get("company")

    proj_name = top_project.get("name") if top_project else None
    proj_tech = ", ".join(top_project.get("tech_stack", [])) if top_project else ""

    resume_context = ""
    if proj_name:
        resume_context = (
            f"Candidate Context from Resume:\n"
            f"- Name: {first_name or 'Candidate'}\n"
            f"- Prior Experience: {past_company or 'Engineering'}\n"
            f"- Primary Project: {proj_name} (Built with: {proj_tech or 'their core stack'})\n\n"
        )

    greeting_instruction = (
        f"1. Greet {first_name} warmly by name (say 'Hi {first_name}' or 'Hello {first_name}'). Do NOT output template placeholders like [FirstName]."
        if first_name else
        "1. Greet the candidate warmly (e.g. 'Hello and welcome!'). Do NOT output template placeholders like [FirstName]."
    )

    prompt = (
        f"You are {persona_name}, a {persona_title} at {company}. Your interviewing style is {style}.\n"
        f"You are initiating a live technical interview with {first_name or 'the candidate'} for the {role} position at {company}.\n"
        f"{resume_context}"
        "HUMAN INTERVIEWER INSTRUCTIONS:\n"
        f"{greeting_instruction}\n"
        f"2. Introduce yourself briefly (your name and role at {company}).\n"
        f"3. {'Explicitly mention that you reviewed their resume and were impressed by their work on ' + proj_name if proj_name else 'Invite them to share a brief overview of their background'}.\n"
        f"4. Warmly invite them to kick off the session by walking you through the architecture, design choices, and technical trade-offs of that project.\n"
        "5. Rules: Exactly 2 to 3 sentences in natural, spoken conversational English. Do NOT use markdown, asterisks, bullet points, brackets, or quotes."
    )
    try:
        raw = await llm_service.call(
            "interview_conductor",
            messages=[
                {"role": "system", "content": "You are a real-world senior tech interviewer at a top technology company."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.75
        )
        cleaned = clean_conversational_speech(raw)
        if cleaned:
            import re
            # Scrub any bracketed placeholders hallucinated by the model
            target_replacement = first_name if first_name else "there"
            cleaned = re.sub(r"\[(?:first\s*name|candidate(?:\s*name)?|name)\]", target_replacement, cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\[(?:your\s*name|interviewer(?:\s*name)?)\]", persona_name, cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\[(?:company)\]", company, cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\[(?:role|position)\]", role, cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\[.*?\]", "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if cleaned and len(cleaned.split()) >= 14:
            return cleaned
    except Exception as e:
        logger.warning(f"Dynamic intro generation note: {e}")

    import random
    if proj_name:
        fallbacks = [
            f"Hi {greeting_name}, great to meet you! I'm {persona_name}, {persona_title} here at {company}. I was reviewing your resume earlier and was really interested by your work on {proj_name}. To kick things off, could you share a quick overview of your background and walk me through the high-level architecture of that project?",
            f"Hello {greeting_name} and welcome! My name is {persona_name}, and I'm a {persona_title} at {company}. I had a look through your CV and noticed your work on {proj_name}. Before we dive into deeper problem solving, I'd love to hear a bit about your journey and how you architected that system.",
            f"Hi {greeting_name}! Thanks for joining today. I'm {persona_name}, {persona_title} at {company}. Your experience with {proj_name} caught my attention while going through your resume. To get started, why don't you introduce yourself and tell me about the key technical trade-offs you handled there?"
        ]
    else:
        fallbacks = [
            f"Hi {greeting_name}, great to meet you! I'm {persona_name}, {persona_title} here at {company}, and I'll be leading your interview for the {role} position today. To kick things off comfortably, could you share a quick overview of your engineering background and a project you've enjoyed building recently?",
            f"Hello {greeting_name} and welcome! My name is {persona_name}, and I'm a {persona_title} at {company}. We have an exciting technical session planned today for the {role} role. Before we dive into problem solving, I'd love to hear a bit about you and a recent technical challenge you tackled.",
            f"Hi {greeting_name}! Thanks for joining today's session. I'm {persona_name}, {persona_title} at {company}. I'm excited to talk with you today about the {role} opportunity. To get started, why don't you introduce yourself and tell me about a project you're particularly proud of?"
        ]
    return random.choice(fallbacks)

# In-memory connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, interview_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[interview_id] = websocket
        logger.info(f"WebSocket client connected to interview session {interview_id}")

    def disconnect(self, interview_id: str):
        if interview_id in self.active_connections:
            del self.active_connections[interview_id]
            logger.info(f"WebSocket client disconnected from interview session {interview_id}")

    async def send_json(self, interview_id: str, data: dict):
        ws = self.active_connections.get(interview_id)
        if ws:
            await ws.send_text(json.dumps(data))

manager = ConnectionManager()

@router.post("/start", response_model=InterviewSessionResponse)
async def start_interview(
    req: CreateInterviewRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Initializes a 30-min AI mock interview session.
    Curates questions for target company, role, location, and uploaded resume.
    """
    interview_id = f"intv-{uuid.uuid4().hex[:12]}"
    
    # Load resume if provided or auto-link active resume for user
    resume_obj = None
    loaded_resume_id = req.resume_id
    if loaded_resume_id:
        stmt = select(ResumeModel).where(ResumeModel.id == loaded_resume_id)
        res = await db.execute(stmt)
        db_resume = res.scalar_one_or_none()
        if db_resume:
            from app.models.resume import ParsedResume
            resume_obj = ParsedResume(**db_resume.parsed_data)
    else:
        # Automatic CV auto-linking for candidate
        stmt = (
            select(ResumeModel)
            .where(ResumeModel.user_id == user_id)
            .order_by(ResumeModel.uploaded_at.desc())
        )
        res = await db.execute(stmt)
        db_resume = res.scalars().first()
        if db_resume:
            from app.models.resume import ParsedResume
            resume_obj = ParsedResume(**db_resume.parsed_data)
            loaded_resume_id = db_resume.id
            logger.info(f"Auto-linked active resume {loaded_resume_id} for user {user_id}")

    candidate_name = resume_obj.candidate_name if resume_obj else None
    resume_data_dict = resume_obj.model_dump() if resume_obj else None

    # Auto-normalize company name to handle typos (e.g. 'striop' -> 'Stripe', 'amazn' -> 'Amazon')
    normalized_company = normalize_company_name(req.company)

    # Map UI difficulty to pedagogical experience level
    level_map = {"easy": "Intern/Junior", "medium": "Mid", "hard": "Senior/Staff"}
    mapped_level = level_map.get(req.difficulty, "Mid")

    # Generate question bank
    questions = await question_service.generate_question_bank(
        company=normalized_company,
        role=req.role,
        location=req.location,
        experience_level=mapped_level,
        tech_stack=req.custom_topics,
        resume=resume_obj
    )

    q_dicts = [q.model_dump() for q in questions]

    # Assign randomized interviewer persona (Male/Female, Indian English/Global)
    persona = azure_speech_service.get_random_interviewer_persona(
        location=req.location,
        preferred_gender=req.preferred_interviewer_gender
    )

    db_interview = InterviewModel(
        id=interview_id,
        user_id=user_id,
        company=normalized_company,
        role=req.role,
        location=req.location,
        duration_min=req.duration_min,
        difficulty=req.difficulty,
        status="in_progress",
        current_round=questions[0].round_type if questions else "behavioral",
        current_question_idx=0,
        questions=q_dicts,
        resume_id=loaded_resume_id,
        resume_data=resume_data_dict,
        candidate_name=candidate_name,
        interviewer_persona=persona,
        started_at=datetime.datetime.utcnow()
    )
    db.add(db_interview)
    await db.commit()

    return InterviewSessionResponse(
        interview_id=interview_id,
        user_id=user_id,
        company=req.company,
        role=req.role,
        status="in_progress",
        current_round=db_interview.current_round,
        current_question_idx=0,
        total_questions=len(questions),
        resume_id=loaded_resume_id,
        candidate_name=candidate_name,
        interviewer_persona=persona.get("name", "standard"),
        interviewer_persona_profile=persona,
        questions=questions,
        created_at=db_interview.created_at.isoformat(),
        started_at=db_interview.started_at.isoformat()
    )

@router.get("/history", response_model=List[InterviewHistoryItem])
async def get_interview_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves all past interview sessions for the current user,
    including overall score, letter grade, and hire recommendation if completed.
    """
    stmt = (
        select(InterviewModel, FeedbackReportModel)
        .outerjoin(FeedbackReportModel, InterviewModel.id == FeedbackReportModel.interview_id)
        .where(InterviewModel.user_id == user_id)
        .order_by(InterviewModel.created_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    history = []
    for intv, fb in rows:
        history.append(InterviewHistoryItem(
            id=intv.id,
            company=intv.company,
            role=intv.role,
            difficulty=intv.difficulty,
            status=intv.status,
            duration_min=intv.duration_min,
            created_at=intv.created_at.isoformat(),
            ended_at=intv.ended_at.isoformat() if intv.ended_at else None,
            formatted_date=format_friendly_date(intv.created_at),
            relative_time=format_relative_time(intv.created_at),
            overall_score=fb.overall_score if fb else None,
            letter_grade=fb.letter_grade if fb else None,
            hire_recommendation=fb.hire_recommendation if fb else None,
            feedback_id=fb.id if fb else None
        ))
    return history

@router.get("/{interview_id}", response_model=InterviewSessionResponse)
async def get_interview(interview_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve current interview state and question bank."""
    stmt = select(InterviewModel).where(InterviewModel.id == interview_id)
    res = await db.execute(stmt)
    db_interview = res.scalar_one_or_none()

    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    questions = [QuestionItem(**q) for q in db_interview.questions]

    return InterviewSessionResponse(
        interview_id=db_interview.id,
        user_id=db_interview.user_id,
        company=db_interview.company,
        role=db_interview.role,
        status=db_interview.status,
        current_round=db_interview.current_round,
        current_question_idx=db_interview.current_question_idx,
        total_questions=len(questions),
        questions=questions,
        created_at=db_interview.created_at.isoformat(),
        started_at=db_interview.started_at.isoformat() if db_interview.started_at else None,
        ended_at=db_interview.ended_at.isoformat() if db_interview.ended_at else None
    )

@router.post("/{interview_id}/code", response_model=CodeSubmissionResult)
async def submit_code_solution(
    interview_id: str,
    req: CodeSubmissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates candidate's code in Monaco Editor against question test cases
    with sandbox security checks (no system imports).
    """
    stmt = select(InterviewModel).where(InterviewModel.id == interview_id)
    res = await db.execute(stmt)
    db_interview = res.scalar_one_or_none()

    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    # Locate the target question
    target_q = None
    for q in db_interview.questions:
        if q.get("id") == req.question_id:
            target_q = QuestionItem(**q)
            break

    test_cases = target_q.test_cases if target_q else []
    result = code_runner_service.evaluate_code(req.code, req.language, test_cases)
    return result

@router.post("/{interview_id}/diagram", response_model=DiagramSubmissionResult)
async def submit_architecture_diagram(
    interview_id: str,
    req: DiagramSubmissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submits and evaluates candidate's interactive whiteboard architecture diagram.
    Analyzes components, detects single points of failure (SPOFs), bottlenecks,
    and returns immediate technical feedback.
    """
    stmt = select(InterviewModel).where(InterviewModel.id == interview_id)
    res = await db.execute(stmt)
    db_interview = res.scalar_one_or_none()

    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    components = req.diagram.components
    comp_types = [str(c.type).lower() for c in components]
    comp_labels = [str(c.label).lower() for c in components]

    has_lb = any("load_balancer" in t or "gateway" in t or "nginx" in l for t, l in zip(comp_types, comp_labels))
    has_cache = any("cache" in t or "redis" in l or "memcached" in l for t, l in zip(comp_types, comp_labels))
    has_db = any("database" in t or "sql" in l or "postgres" in l or "mongo" in l for t, l in zip(comp_types, comp_labels))
    has_queue = any("queue" in t or "kafka" in l or "rabbitmq" in l for t, l in zip(comp_types, comp_labels))

    spof_risks = []
    bottlenecks = []
    strengths = []

    if has_db and not has_cache:
        bottlenecks.append("Database tier may become a bottleneck under read-heavy traffic without a caching layer.")
    if len([t for t in comp_types if "database" in t]) == 1 and not any("replica" in l or "secondary" in l for l in comp_labels):
        spof_risks.append("Single database instance detected without primary-replica replication; presents a SPOF.")
    if len(components) >= 2 and not has_lb:
        spof_risks.append("Application servers lack a dedicated load balancer / reverse proxy for traffic distribution.")

    if has_lb:
        strengths.append("Load balancer correctly placed at the traffic ingress point.")
    if has_cache:
        strengths.append("Caching layer incorporated to absorb read spikes.")
    if has_queue:
        strengths.append("Asynchronous message queue decoupling heavy processing tasks.")

    if not strengths:
        strengths.append("Basic component structure initialized.")

    base_score = 75.0
    if has_lb: base_score += 8.0
    if has_cache: base_score += 7.0
    if has_queue: base_score += 5.0
    if spof_risks: base_score -= 10.0
    score = max(40.0, min(95.0, base_score))

    if spof_risks:
        critique = f"Your architecture is forming nicely, but consider how to mitigate single points of failure like: {spof_risks[0]}."
    else:
        critique = "Strong architectural layout. Component boundaries and data flow are well separated."

    follow_up = None
    if has_cache:
        follow_up = "How will your services handle cache invalidation and cache penetration under peak write loads?"
    elif has_queue:
        follow_up = "What happens if downstream consumers lag behind? How do you ensure message delivery guarantees?"
    elif has_db:
        follow_up = "What sharding or indexing strategy would you introduce once table size exceeds 100 million rows?"

    # Update interview model with current diagram state
    db_interview.architecture_diagram = req.diagram.model_dump()
    await db.commit()

    return DiagramSubmissionResult(
        score=score,
        architecture_score=score,
        critique=critique,
        interviewer_speech=critique,
        detected_components=[c.label for c in components],
        spof_risks=spof_risks,
        bottlenecks=bottlenecks,
        strengths=strengths,
        suggested_follow_up=follow_up,
        probed_topic=follow_up
    )

# --- REAL-TIME WEBSOCKET INTERVIEW STREAMING ---
@router.websocket("/ws/{interview_id}")
async def interview_websocket_endpoint(websocket: WebSocket, interview_id: str):
    """
    Real-time bidirectional WebSocket connection for live interview:
    - AI Interviewer streaming voice / text questions
    - Speech-to-text user answers
    - In-browser camera telemetry (eye contact, confidence)
    - Code editor anti-cheat telemetry (tab switches, paste attempts)
    - Stateful LangGraph turn orchestration
    """
    await manager.connect(interview_id, websocket)

    # Cache for live session telemetry
    session_transcript: List[dict] = []
    session_violations: List[dict] = []
    session_body_samples: List[dict] = []

    try:
        # Load interview from DB
        async with AsyncSessionLocal() as db:
            stmt = select(InterviewModel).where(InterviewModel.id == interview_id)
            res = await db.execute(stmt)
            db_intv = res.scalar_one_or_none()

            if not db_intv:
                await websocket.send_text(json.dumps({"type": "error", "message": "Interview session not found."}))
                await websocket.close()
                return

            questions = db_intv.questions
            curr_idx = db_intv.current_question_idx
            company = db_intv.company
            role = db_intv.role
            user_id = db_intv.user_id
            resume_data = getattr(db_intv, "resume_data", None) or {}
            candidate_name = getattr(db_intv, "candidate_name", None) or ""
            curr_diagram_data = db_intv.architecture_diagram or None
            curr_diagram_critique = None
            persona = (
                getattr(db_intv, "interviewer_persona", None)
                or azure_speech_service.get_random_interviewer_persona(location=getattr(db_intv, "location", "India"))
            )

        # Send initial warm greeting & conversational icebreaker
        if questions and curr_idx < len(questions):
            first_q = questions[curr_idx]
            persona_name = persona.get("name", "Vikram Sharma")
            welcome_text = await generate_dynamic_interview_intro(
                persona, company, role, resume_data=resume_data, candidate_name=candidate_name
            )
            welcome_audio = await azure_speech_service.synthesize_speech_base64(
                welcome_text, voice=persona.get("voice")
            )
            initial_msg = {
                "type": "ai_question",
                "round_type": "behavioral",
                "question_idx": curr_idx,
                "question": first_q,
                "content": welcome_text,
                "audio_base64": welcome_audio,
                "interviewer_persona": persona,
                "timestamp": time.time()
            }
            session_transcript.append({
                "role": "interviewer",
                "content": welcome_text,
                "round_type": "behavioral",
                "question_idx": curr_idx,
                "audio_base64": welcome_audio,
                "interviewer_name": persona.get("name"),
                "timestamp": time.time()
            })
            await manager.send_json(interview_id, initial_msg)

        curr_follow_up_count = 0
        curr_active_probe = None
        curr_hint_count = 0
        curr_hints_given = []
        curr_preferred_lang = None
        curr_awaiting_lang = False
        speech_clarity_stats = {
            "total_words": 0,
            "filler_words": {"um": 0, "uh": 0, "like": 0, "basically": 0, "you know": 0, "actually": 0}
        }

        import asyncio
        pending_graph_task = None
        receive_task = asyncio.create_task(websocket.receive_text())

        # Main message loop
        while True:
            tasks = [receive_task]
            if pending_graph_task:
                tasks.append(pending_graph_task)

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # If the graph task finished successfully, we can clean it up
            if pending_graph_task in done:
                try:
                    res = pending_graph_task.result()  # raise exceptions if any
                    if res == "completed":
                        break
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Graph execution error: {e}")
                pending_graph_task = None

            if receive_task not in done:
                continue

            raw_data = receive_task.result()
            receive_task = asyncio.create_task(websocket.receive_text())

            data = json.loads(raw_data)
            msg_type = data.get("type")

            # 1. Candidate speech / text response (answers, clarifying questions, hint requests, or approach checks)
            if msg_type in ["candidate_answer", "candidate_clarification", "candidate_hint_request", "candidate_approach_check"]:
                answer_text = data.get("content", "")
                if msg_type == "candidate_hint_request" and not answer_text:
                    answer_text = "Could you please provide a hint on how to approach this?"
                elif msg_type == "candidate_approach_check" and not answer_text:
                    answer_text = "Am I on the right track with this approach?"

                # Speech clarity & filler word telemetry
                words = answer_text.lower().split()
                speech_clarity_stats["total_words"] += len(words)
                for w in words:
                    cleaned_w = w.strip(".,!?;:")
                    if cleaned_w in speech_clarity_stats["filler_words"]:
                        speech_clarity_stats["filler_words"][cleaned_w] += 1
                if "you know" in answer_text.lower():
                    speech_clarity_stats["filler_words"]["you know"] += answer_text.lower().count("you know")

                session_transcript.append({
                    "role": "candidate",
                    "content": answer_text,
                    "round_type": questions[curr_idx].get("round_type") if curr_idx < len(questions) else "general",
                    "question_idx": curr_idx,
                    "timestamp": time.time()
                })

                # Acknowledge candidate input
                await manager.send_json(interview_id, {"type": "answer_received", "status": "evaluating"})

                # Execute LangGraph state turn
                graph_state = {
                    "interview_id": interview_id,
                    "user_id": user_id,
                    "company": company,
                    "role": role,
                    "location": "India",
                    "duration_min": 30,
                    "interviewer_persona": "standard",
                    "resume_data": resume_data,
                    "candidate_name": candidate_name,
                    "questions": questions,
                    "current_question_idx": curr_idx,
                    "current_round": questions[curr_idx].get("round_type") if curr_idx < len(questions) else "behavioral",
                    "transcript": session_transcript,
                    "latest_candidate_response": answer_text,
                    "latest_interviewer_response": None,
                    "current_score": 75.0,
                    "difficulty_level": "medium",
                    "follow_up_count": curr_follow_up_count,
                    "active_follow_up_topic": curr_active_probe,
                    "hint_count": curr_hint_count,
                    "hints_given": curr_hints_given,
                    "preferred_coding_language": curr_preferred_lang,
                    "awaiting_language_preference": curr_awaiting_lang,
                    "speech_clarity_metrics": speech_clarity_stats,
                    "violations": session_violations,
                    "body_language_samples": session_body_samples,
                    "code_submissions": [],
                    "diagram_data": curr_diagram_data,
                    "is_diagram_submission": False,
                    "phase": "evaluate",
                    "feedback_report": None
                }

                if pending_graph_task and not pending_graph_task.done():
                    pending_graph_task.cancel()

                async def execute_turn(g_state):
                    nonlocal curr_idx, new_difficulty, curr_follow_up_count, curr_active_probe, curr_hint_count, curr_hints_given, curr_awaiting_lang, curr_preferred_lang, curr_diagram_data
                    
                    async def send_chunk(text_chunk):
                        audio_base64 = await azure_speech_service.synthesize_speech_base64(text_chunk, voice=persona.get("voice"))
                        await manager.send_json(interview_id, {
                            "type": "ai_speech_chunk",
                            "content": text_chunk,
                            "audio_base64": audio_base64
                        })
                    
                    thread_config = {"configurable": {"thread_id": interview_id, "send_chunk_cb": send_chunk}}
                    step_result = await interview_graph.ainvoke(g_state, config=thread_config)


                    # Update index & difficulty & organic follow-up state
                    curr_idx = step_result.get("current_question_idx", curr_idx)
                    new_difficulty = step_result.get("difficulty_level", "medium")
                    curr_follow_up_count = step_result.get("follow_up_count", 0)
                    curr_active_probe = step_result.get("active_follow_up_topic")
                    curr_hint_count = step_result.get("hint_count", 0)
                    curr_hints_given = step_result.get("hints_given", [])
                    curr_awaiting_lang = step_result.get("awaiting_language_preference", False)
                    if step_result.get("preferred_coding_language"):
                        curr_preferred_lang = step_result["preferred_coding_language"]
                        # Notify frontend to automatically switch code editor language and template
                        await manager.send_json(interview_id, {
                            "type": "coding_language_selected",
                            "language": curr_preferred_lang
                        })

                    is_thinking_pause = bool(step_result.get("is_thinking_pause"))
                    is_clarification = bool(step_result.get("is_clarification"))
                    is_hint = bool(step_result.get("is_hint"))
                    is_approach_check = bool(step_result.get("is_approach_check"))
                    track_status = step_result.get("track_status", "on_track")
                    hint_tier = step_result.get("hint_tier", curr_hint_count)

                    # Check if interview complete
                    if curr_idx >= len(questions) or step_result.get("phase") == "feedback":
                        await manager.send_json(interview_id, {
                            "type": "interview_completed",
                            "message": "You have completed all sections of the interview! Generating your detailed evaluation report..."
                        })
                        return "completed"

                    # Deliver the dynamic, human AI interviewer speech
                    next_q = questions[curr_idx]
                    is_probe = bool(curr_active_probe) and not is_clarification and not is_hint and not is_approach_check and not is_thinking_pause
                    interviewer_speech = step_result.get("latest_interviewer_response")

                    if not interviewer_speech:
                        if is_thinking_pause:
                            interviewer_speech = "Sure thing, take your time! Let me know when you're ready to proceed."
                        elif is_approach_check:
                            interviewer_speech = (
                                "Yes, exactly! You are on the right track with that approach. "
                                "Go ahead and start implementing it!"
                            )
                        elif is_hint:
                            interviewer_speech = (
                                "Sure! Here is a quick pointer: Consider using a Hash Map or Two Pointers to trade space for O(1) lookups."
                            )
                        elif is_clarification:
                            interviewer_speech = (
                                "Good question! Feel free to outline the brute force intuition briefly in 30 seconds so we are aligned on the baseline, "
                                "but please implement the optimal solution directly in code. Go ahead whenever you are ready!"
                            )
                        elif is_probe:
                            interviewer_speech = (
                                f"Got it. You brought up {curr_active_probe} there—could you walk me through "
                                "how that works under the hood and what trade-offs you weighed?"
                            )
                        else:
                            spoken_summary = clean_conversational_speech(next_q.get("description", ""))
                            interviewer_speech = (
                                f"Makes sense. Now let's move into our next section: {next_q.get('title')}. "
                                f"{spoken_summary}"
                            )

                    session_transcript.append({
                        "role": "interviewer",
                        "content": interviewer_speech,
                        "round_type": next_q.get("round_type"),
                        "question_idx": curr_idx,
                        "is_thinking_pause": is_thinking_pause,
                        "is_approach_check": is_approach_check,
                        "track_status": track_status if is_approach_check else None,
                        "is_clarification": is_clarification,
                        "is_hint": is_hint,
                        "hint_tier": hint_tier if is_hint else None,
                        "is_follow_up": is_probe,
                        "timestamp": time.time()
                    })

                    if is_thinking_pause:
                        msg_response_type = "ai_pause_ack"
                    elif is_approach_check:
                        msg_response_type = "ai_affirmation"
                    elif is_hint:
                        msg_response_type = "ai_hint"
                    elif is_clarification:
                        msg_response_type = "ai_clarification"
                    elif is_probe:
                        msg_response_type = "ai_follow_up"
                    else:
                        msg_response_type = "ai_question"

                    interviewer_audio = await azure_speech_service.synthesize_speech_base64(
                        interviewer_speech, voice=persona.get("voice")
                    )
                
                    import re
                    ui_display_text = re.sub(r'<[^>]+>', '', interviewer_speech).strip()

                    await manager.send_json(interview_id, {
                        "type": msg_response_type,
                        "round_type": next_q.get("round_type"),
                        "question_idx": curr_idx,
                        "question": next_q,
                        "content": ui_display_text,
                        "audio_base64": interviewer_audio,
                        "interviewer_persona": persona,
                        "is_thinking_pause": is_thinking_pause,
                        "is_approach_check": is_approach_check,
                        "track_status": track_status if is_approach_check else None,
                        "is_hint": is_hint,
                        "hint_tier": hint_tier if is_hint else None,
                        "is_clarification": is_clarification,
                        "is_follow_up": is_probe,
                        "probed_topic": curr_active_probe,
                        "difficulty": new_difficulty,
                        "speech_clarity": speech_clarity_stats,
                        "timestamp": time.time()
                    })

                pending_graph_task = asyncio.create_task(execute_turn(graph_state))

            # 2. Barge-in handling
            elif msg_type == "barge_in":
                barge_text = data.get("content", "")
                if pending_graph_task and not pending_graph_task.done():
                    pending_graph_task.cancel()
                    pending_graph_task = None
                    logger.info(f"Barge-in detected in {interview_id}. Cancelled active generation.")
                
                await manager.send_json(interview_id, {"type": "barge_in_ack"})
                session_transcript.append({
                    "role": "candidate",
                    "content": f"[BARGE-IN]: {barge_text}",
                    "round_type": questions[curr_idx].get("round_type") if curr_idx < len(questions) else "general",
                    "question_idx": curr_idx,
                    "timestamp": time.time()
                })

            # 2. Interactive System Design Whiteboard State Update (Auto-save / Component Placement)
            elif msg_type == "whiteboard_update":
                curr_diagram_data = data.get("diagram_data") or {}
                comp_cnt = len(curr_diagram_data.get("components", [])) if isinstance(curr_diagram_data, dict) else 0
                logger.info(f"Whiteboard state updated for interview {interview_id}: {comp_cnt} component(s)")
                await manager.send_json(interview_id, {
                    "type": "whiteboard_saved",
                    "status": "ok",
                    "component_count": comp_cnt
                })

            # 3. Candidate Verbal Presentation of Architecture Diagram
            elif msg_type == "candidate_diagram_presentation":
                answer_text = data.get("content") or data.get("explanation") or "I have designed the system architecture diagram on the whiteboard."
                if data.get("diagram_data"):
                    curr_diagram_data = data.get("diagram_data")

                # Speech clarity & filler word telemetry on diagram walkthrough
                words = answer_text.lower().split()
                speech_clarity_stats["total_words"] += len(words)
                for w in words:
                    cleaned_w = w.strip(".,!?;:")
                    if cleaned_w in speech_clarity_stats["filler_words"]:
                        speech_clarity_stats["filler_words"][cleaned_w] += 1
                if "you know" in answer_text.lower():
                    speech_clarity_stats["filler_words"]["you know"] += answer_text.lower().count("you know")

                session_transcript.append({
                    "role": "candidate",
                    "content": f"[Architecture Whiteboard Submission]: {answer_text}",
                    "round_type": questions[curr_idx].get("round_type") if curr_idx < len(questions) else "system_design",
                    "question_idx": curr_idx,
                    "timestamp": time.time()
                })

                await manager.send_json(interview_id, {"type": "answer_received", "status": "evaluating"})

                graph_state = {
                    "interview_id": interview_id,
                    "user_id": user_id,
                    "company": company,
                    "role": role,
                    "location": "India",
                    "duration_min": 30,
                    "interviewer_persona": "standard",
                    "resume_data": resume_data,
                    "candidate_name": candidate_name,
                    "questions": questions,
                    "current_question_idx": curr_idx,
                    "current_round": questions[curr_idx].get("round_type") if curr_idx < len(questions) else "system_design",
                    "transcript": session_transcript,
                    "latest_candidate_response": answer_text,
                    "latest_interviewer_response": None,
                    "current_score": 75.0,
                    "difficulty_level": "medium",
                    "follow_up_count": curr_follow_up_count,
                    "active_follow_up_topic": curr_active_probe,
                    "hint_count": curr_hint_count,
                    "hints_given": curr_hints_given,
                    "speech_clarity_metrics": speech_clarity_stats,
                    "violations": session_violations,
                    "body_language_samples": session_body_samples,
                    "code_submissions": [],
                    "diagram_data": curr_diagram_data,
                    "is_diagram_submission": True,
                    "phase": "evaluate",
                    "feedback_report": None
                }

                thread_config = {"configurable": {"thread_id": interview_id}}
                step_result = await interview_graph.ainvoke(graph_state, config=thread_config)

                curr_idx = step_result.get("current_question_idx", curr_idx)
                new_difficulty = step_result.get("difficulty_level", "medium")
                curr_follow_up_count = step_result.get("follow_up_count", 0)
                curr_active_probe = step_result.get("active_follow_up_topic")
                curr_diagram_critique = step_result.get("diagram_critique")
                interviewer_speech = step_result.get("latest_interviewer_response")

                if not interviewer_speech:
                    if curr_diagram_critique and curr_diagram_critique.get("critique"):
                        interviewer_speech = curr_diagram_critique["critique"]
                    else:
                        interviewer_speech = "Thank you for walking me through your architecture. The component boundaries are well placed."

                next_q = questions[curr_idx] if curr_idx < len(questions) else questions[-1]

                session_transcript.append({
                    "role": "interviewer",
                    "content": interviewer_speech,
                    "round_type": next_q.get("round_type"),
                    "question_idx": curr_idx,
                    "is_diagram_critique": True,
                    "timestamp": time.time()
                })

                critique_audio = await azure_speech_service.synthesize_speech_base64(
                    interviewer_speech, voice=persona.get("voice")
                )

                await manager.send_json(interview_id, {
                    "type": "ai_diagram_critique",
                    "round_type": next_q.get("round_type"),
                    "question_idx": curr_idx,
                    "question": next_q,
                    "content": interviewer_speech,
                    "audio_base64": critique_audio,
                    "interviewer_persona": persona,
                    "diagram_critique": curr_diagram_critique,
                    "probed_topic": curr_active_probe,
                    "difficulty": new_difficulty,
                    "speech_clarity": speech_clarity_stats,
                    "timestamp": time.time()
                })

            # 4. Camera Body Language Telemetry from TensorFlow.js Face Mesh
            elif msg_type == "body_language_sample":
                sample = {
                    "timestamp": data.get("timestamp", time.time()),
                    "eye_contact_score": float(data.get("eye_contact_score", 85.0)),
                    "confidence_score": float(data.get("confidence_score", 80.0)),
                    "head_stability_score": float(data.get("head_stability_score", 90.0)),
                    "face_in_frame": bool(data.get("face_in_frame", True))
                }
                session_body_samples.append(sample)

            # 5. Anti-Cheat Proctoring Violation (copy-paste, tab switch, devtools)
            elif msg_type == "proctoring_violation":
                violation = {
                    "violation_type": data.get("violation_type", "tab_switch"),
                    "details": data.get("details"),
                    "timestamp": data.get("timestamp", time.time()),
                    "question_idx": curr_idx
                }
                session_violations.append(violation)
                logger.warning(f"Proctoring alert on interview {interview_id}: {violation}")
                # Send gentle warning reminder back to candidate
                await manager.send_json(interview_id, {
                    "type": "proctoring_warning",
                    "message": f"Integrity notice: {violation.get('violation_type')} was flagged and recorded in your proctoring report."
                })

    except WebSocketDisconnect:
        logger.info(f"Interview WebSocket disconnected for {interview_id}")
    except Exception as e:
        logger.error(f"WebSocket error in interview {interview_id}: {e}", exc_info=True)
    finally:
        manager.disconnect(interview_id)

        # Persist session completion and feedback report to DB
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(InterviewModel).where(InterviewModel.id == interview_id)
                res = await db.execute(stmt)
                db_intv = res.scalar_one_or_none()

                if db_intv:
                    db_intv.status = "completed"
                    db_intv.ended_at = datetime.datetime.utcnow()
                    if curr_diagram_data:
                        db_intv.architecture_diagram = curr_diagram_data
                    if persona:
                        db_intv.interviewer_persona = persona

                    # Save all messages
                    for m in session_transcript:
                        msg_record = InterviewMessageModel(
                            id=f"msg-{uuid.uuid4().hex[:12]}",
                            interview_id=interview_id,
                            role=m["role"],
                            content=m["content"],
                            round_type=m.get("round_type"),
                            question_idx=m.get("question_idx"),
                            timestamp=m.get("timestamp", time.time())
                        )
                        db.add(msg_record)

                    # Save violations
                    for v in session_violations:
                        v_record = ProctoringViolationModel(
                            id=f"viol-{uuid.uuid4().hex[:12]}",
                            interview_id=interview_id,
                            violation_type=v["violation_type"],
                            details=v.get("details"),
                            timestamp=v.get("timestamp", time.time())
                        )
                        db.add(v_record)

                    await db.commit()

            # Generate final feedback report
            typed_msgs = [InterviewMessage(**m) for m in session_transcript]
            typed_viols = [ProctoringViolation(**v) for v in session_violations]
            typed_samples = [BodyLanguageSample(**s) for s in session_body_samples]

            report = await feedback_service.generate_report(
                interview_id=interview_id,
                user_id=user_id if 'user_id' in locals() else "default_user",
                company=company if 'company' in locals() else "Company",
                role=role if 'role' in locals() else "Software Engineer",
                transcript=typed_msgs,
                violations=typed_viols,
                body_language_samples=typed_samples,
                architecture_diagram=curr_diagram_data,
                architecture_critique=curr_diagram_critique
            )

            async with AsyncSessionLocal() as db:
                stmt = select(FeedbackReportModel).where(FeedbackReportModel.interview_id == interview_id)
                res = await db.execute(stmt)
                existing_fb = res.scalar_one_or_none()

                if existing_fb:
                    existing_fb.overall_score = report.overall_score
                    existing_fb.letter_grade = report.letter_grade
                    existing_fb.hire_recommendation = report.hire_recommendation
                    existing_fb.section_scores = [s.dict() for s in report.section_scores]
                    existing_fb.communication = report.communication.dict()
                    existing_fb.body_language = report.body_language.dict()
                    existing_fb.code_quality = report.code_quality.dict() if report.code_quality else None
                    existing_fb.architecture_report = report.architecture_report.dict() if report.architecture_report else None
                    existing_fb.proctoring = report.proctoring.dict()
                    existing_fb.strengths = report.top_strengths
                    existing_fb.weaknesses = report.top_weaknesses
                    existing_fb.roadmap = [r.dict() for r in report.improvement_roadmap_14_days]
                    existing_fb.summary = report.detailed_summary
                    logger.info(f"Updated existing feedback report {existing_fb.id} for interview {interview_id}.")
                else:
                    db_fb = FeedbackReportModel(
                        id=report.feedback_id,
                        interview_id=interview_id,
                        user_id=report.user_id,
                        overall_score=report.overall_score,
                        letter_grade=report.letter_grade,
                        hire_recommendation=report.hire_recommendation,
                        section_scores=[s.dict() for s in report.section_scores],
                        communication=report.communication.dict(),
                        body_language=report.body_language.dict(),
                        code_quality=report.code_quality.dict() if report.code_quality else None,
                        architecture_report=report.architecture_report.dict() if report.architecture_report else None,
                        proctoring=report.proctoring.dict(),
                        strengths=report.top_strengths,
                        weaknesses=report.top_weaknesses,
                        roadmap=[r.dict() for r in report.improvement_roadmap_14_days],
                        summary=report.detailed_summary
                    )
                    db.add(db_fb)
                    logger.info(f"Created new feedback report {report.feedback_id} for interview {interview_id}.")

                await db.commit()

        except Exception as e:
            logger.error(f"Error finalizing interview session: {e}", exc_info=True)
