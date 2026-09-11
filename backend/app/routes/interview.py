import uuid
import json
import time
import datetime
import logging
from typing import Dict, Any, List
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
    CodeSubmissionResult, InterviewMessage
)
from app.models.question import QuestionItem
from app.models.proctoring import ProctoringViolation, BodyLanguageSample
from app.services.question_service import question_service
from app.services.code_runner_service import code_runner_service
from app.services.feedback_service import feedback_service
from app.graph.graph import interview_graph

logger = logging.getLogger("hireprep.interview")
router = APIRouter(prefix="/api/interview", tags=["Interview Session"])

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
    
    # Load resume if provided
    resume_obj = None
    if req.resume_id:
        stmt = select(ResumeModel).where(ResumeModel.id == req.resume_id)
        res = await db.execute(stmt)
        db_resume = res.scalar_one_or_none()
        if db_resume:
            from app.models.resume import ParsedResume
            resume_obj = ParsedResume(**db_resume.parsed_data)

    # Generate question bank
    questions = await question_service.generate_question_bank(
        company=req.company,
        role=req.role,
        location=req.location,
        tech_stack=req.custom_topics,
        resume=resume_obj
    )

    q_dicts = [q.model_dump() for q in questions]

    db_interview = InterviewModel(
        id=interview_id,
        user_id=user_id,
        company=req.company,
        role=req.role,
        location=req.location,
        duration_min=req.duration_min,
        difficulty=req.difficulty,
        status="in_progress",
        current_round=questions[0].round_type if questions else "behavioral",
        current_question_idx=0,
        questions=q_dicts,
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
        questions=questions,
        created_at=db_interview.created_at.isoformat(),
        started_at=db_interview.started_at.isoformat()
    )

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
    result = code_runner_service.evaluate_python_code(req.code, test_cases)
    return result

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

        # Send initial greeting & first question
        if questions and curr_idx < len(questions):
            first_q = questions[curr_idx]
            welcome_text = (
                f"Hello! Welcome to your technical mock interview for the {role} position at {company}. "
                f"We will be covering {len(questions)} rounds today including coding, system design, and behavioral questions. "
                "Whenever you are ready, let's begin with our first question: "
                f"{first_q.get('description')}"
            )
            initial_msg = {
                "type": "ai_question",
                "round_type": first_q.get("round_type"),
                "question_idx": curr_idx,
                "question": first_q,
                "content": welcome_text,
                "timestamp": time.time()
            }
            session_transcript.append({
                "role": "interviewer",
                "content": welcome_text,
                "round_type": first_q.get("round_type"),
                "question_idx": curr_idx,
                "timestamp": time.time()
            })
            await manager.send_json(interview_id, initial_msg)

        curr_follow_up_count = 0
        curr_active_probe = None
        curr_hint_count = 0
        curr_hints_given = []
        speech_clarity_stats = {
            "total_words": 0,
            "filler_words": {"um": 0, "uh": 0, "like": 0, "basically": 0, "you know": 0, "actually": 0}
        }

        # Main message loop
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")

            # 1. Candidate speech / text response (answers, clarifying questions, or hint requests)
            if msg_type in ["candidate_answer", "candidate_clarification", "candidate_hint_request"]:
                answer_text = data.get("content", "")
                if msg_type == "candidate_hint_request" and not answer_text:
                    answer_text = "Could you please provide a hint on how to approach this?"

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
                    "speech_clarity_metrics": speech_clarity_stats,
                    "violations": session_violations,
                    "body_language_samples": session_body_samples,
                    "code_submissions": [],
                    "phase": "evaluate",
                    "feedback_report": None
                }

                thread_config = {"configurable": {"thread_id": interview_id}}
                step_result = await interview_graph.ainvoke(graph_state, config=thread_config)

                # Update index & difficulty & organic follow-up state
                curr_idx = step_result.get("current_question_idx", curr_idx)
                new_difficulty = step_result.get("difficulty_level", "medium")
                curr_follow_up_count = step_result.get("follow_up_count", 0)
                curr_active_probe = step_result.get("active_follow_up_topic")
                curr_hint_count = step_result.get("hint_count", 0)
                curr_hints_given = step_result.get("hints_given", [])
                is_clarification = bool(step_result.get("is_clarification"))
                is_hint = bool(step_result.get("is_hint"))
                hint_tier = step_result.get("hint_tier", curr_hint_count)

                # Check if interview complete
                if curr_idx >= len(questions) or step_result.get("phase") == "feedback":
                    await manager.send_json(interview_id, {
                        "type": "interview_completed",
                        "message": "You have completed all sections of the interview! Generating your detailed evaluation report..."
                    })
                    break

                # Deliver the dynamic, human AI interviewer speech
                next_q = questions[curr_idx]
                is_probe = bool(curr_active_probe) and not is_clarification and not is_hint
                interviewer_speech = step_result.get("latest_interviewer_response")

                if not interviewer_speech:
                    if is_hint:
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
                        interviewer_speech = (
                            f"Understood. Let's move to our next section ({next_q.get('round_type').upper()}): "
                            f"{next_q.get('description')}"
                        )

                session_transcript.append({
                    "role": "interviewer",
                    "content": interviewer_speech,
                    "round_type": next_q.get("round_type"),
                    "question_idx": curr_idx,
                    "is_clarification": is_clarification,
                    "is_hint": is_hint,
                    "hint_tier": hint_tier if is_hint else None,
                    "is_follow_up": is_probe,
                    "timestamp": time.time()
                })

                if is_hint:
                    msg_response_type = "ai_hint"
                elif is_clarification:
                    msg_response_type = "ai_clarification"
                elif is_probe:
                    msg_response_type = "ai_follow_up"
                else:
                    msg_response_type = "ai_question"

                await manager.send_json(interview_id, {
                    "type": msg_response_type,
                    "round_type": next_q.get("round_type"),
                    "question_idx": curr_idx,
                    "question": next_q,
                    "content": interviewer_speech,
                    "is_hint": is_hint,
                    "hint_tier": hint_tier if is_hint else None,
                    "is_clarification": is_clarification,
                    "is_follow_up": is_probe,
                    "probed_topic": curr_active_probe,
                    "difficulty": new_difficulty,
                    "speech_clarity": speech_clarity_stats,
                    "timestamp": time.time()
                })

            # 2. Camera Body Language Telemetry from TensorFlow.js Face Mesh
            elif msg_type == "body_language_sample":
                sample = {
                    "timestamp": data.get("timestamp", time.time()),
                    "eye_contact_score": float(data.get("eye_contact_score", 85.0)),
                    "confidence_score": float(data.get("confidence_score", 80.0)),
                    "head_stability_score": float(data.get("head_stability_score", 90.0)),
                    "face_in_frame": bool(data.get("face_in_frame", True))
                }
                session_body_samples.append(sample)

            # 3. Anti-Cheat Proctoring Violation (copy-paste, tab switch, devtools)
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
                body_language_samples=typed_samples
            )

            async with AsyncSessionLocal() as db:
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
                    proctoring=report.proctoring.dict(),
                    strengths=report.top_strengths,
                    weaknesses=report.top_weaknesses,
                    roadmap=[r.dict() for r in report.improvement_roadmap_14_days],
                    summary=report.detailed_summary
                )
                db.add(db_fb)
                await db.commit()
                logger.info(f"Saved final feedback report {report.feedback_id} to database.")

        except Exception as e:
            logger.error(f"Error finalizing interview session: {e}", exc_info=True)
