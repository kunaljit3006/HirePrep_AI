import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.models.interview import InterviewMessage
from app.models.proctoring import ProctoringViolation, BodyLanguageSample
from app.services.feedback_service import feedback_service

logger = logging.getLogger("hireprep.node.feedback_generator")

async def feedback_generator_node(state: InterviewState) -> Dict[str, Any]:
    """
    Feedback Generator Node (Agent 5):
    Compiles final holistic evaluation report covering:
    - Overall score & Letter grade
    - Section breakdown
    - Communication quality
    - Camera body language metrics
    - Proctoring integrity & anti-cheat score
    - 14-Day personalized roadmap
    """
    interview_id = state.get("interview_id", "default_interview")
    user_id = state.get("user_id", "default_user")
    company = state.get("company", "Tech Company")
    role = state.get("role", "Software Engineer")

    # Map state data to models
    raw_transcript = state.get("transcript", [])
    transcript = [
        InterviewMessage(
            role=msg["role"],
            content=msg["content"],
            timestamp=msg.get("timestamp", 0.0),
            round_type=msg.get("round_type"),
            question_idx=msg.get("question_idx")
        )
        for msg in raw_transcript
    ]

    raw_violations = state.get("violations", [])
    violations = [
        ProctoringViolation(
            violation_type=v.get("violation_type", "tab_switch"),
            details=v.get("details"),
            timestamp=v.get("timestamp", 0.0),
            question_idx=v.get("question_idx")
        )
        for v in raw_violations
    ]

    raw_samples = state.get("body_language_samples", [])
    body_samples = [
        BodyLanguageSample(
            timestamp=s.get("timestamp", 0.0),
            eye_contact_score=s.get("eye_contact_score", 85.0),
            confidence_score=s.get("confidence_score", 80.0),
            head_stability_score=s.get("head_stability_score", 85.0),
            face_in_frame=s.get("face_in_frame", True)
        )
        for s in raw_samples
    ]

    report = await feedback_service.generate_report(
        interview_id=interview_id,
        user_id=user_id,
        company=company,
        role=role,
        transcript=transcript,
        violations=violations,
        body_language_samples=body_samples,
        score_history=state.get("score_history", []),
        concept_gaps=state.get("concept_gaps", []),
        candidate_strengths=state.get("candidate_strengths", []),
        topics_covered=state.get("topics_covered", [])
    )

    logger.info(f"Feedback report generated for interview {interview_id}. Overall Score: {report.overall_score}")

    return {
        "feedback_report": report.dict(),
        "phase": "done"
    }
