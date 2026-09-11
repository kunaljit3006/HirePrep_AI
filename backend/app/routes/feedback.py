from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_current_user_id
from app.db.connection import get_db
from app.db.models import FeedbackReportModel, InterviewModel, InterviewMessageModel, ProctoringViolationModel
from app.models.feedback import (
    FeedbackReportResponse, SectionScore, CommunicationMetrics,
    CameraBodyLanguageReport, CodeQualityReport, RoadmapDay
)
from app.models.proctoring import ProctoringSummary, ProctoringViolation, BodyLanguageSample
from app.models.interview import InterviewMessage
from app.services.feedback_service import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["Feedback & Analytics"])

def build_feedback_response(db_fb: FeedbackReportModel) -> FeedbackReportResponse:
    section_scores = [SectionScore(**s) for s in db_fb.section_scores]
    communication = CommunicationMetrics(**db_fb.communication)
    body_language = CameraBodyLanguageReport(**db_fb.body_language)
    code_quality = CodeQualityReport(**db_fb.code_quality) if db_fb.code_quality else None
    proctoring = ProctoringSummary(**db_fb.proctoring)
    roadmap = [RoadmapDay(**r) for r in db_fb.roadmap]

    return FeedbackReportResponse(
        feedback_id=db_fb.id,
        interview_id=db_fb.interview_id,
        user_id=db_fb.user_id,
        overall_score=db_fb.overall_score,
        letter_grade=db_fb.letter_grade,
        hire_recommendation=db_fb.hire_recommendation,
        section_scores=section_scores,
        communication=communication,
        body_language=body_language,
        code_quality=code_quality,
        proctoring=proctoring,
        top_strengths=db_fb.strengths,
        top_weaknesses=db_fb.weaknesses,
        improvement_roadmap_14_days=roadmap,
        detailed_summary=db_fb.summary,
        created_at=db_fb.created_at.isoformat()
    )

@router.get("/{interview_id}", response_model=FeedbackReportResponse)
async def get_interview_feedback(
    interview_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve comprehensive feedback report for an interview session."""
    stmt = select(FeedbackReportModel).where(FeedbackReportModel.interview_id == interview_id)
    res = await db.execute(stmt)
    db_fb = res.scalar_one_or_none()

    if not db_fb:
        raise HTTPException(
            status_code=404,
            detail="Feedback report not yet generated or interview not found."
        )

    return build_feedback_response(db_fb)

@router.get("/user/history", response_model=List[FeedbackReportResponse])
async def get_user_feedback_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve past feedback reports for the current user."""
    stmt = select(FeedbackReportModel).where(FeedbackReportModel.user_id == user_id).order_by(FeedbackReportModel.created_at.desc())
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [build_feedback_response(r) for r in records]

@router.post("/{interview_id}/generate", response_model=FeedbackReportResponse)
async def generate_feedback_report(
    interview_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually generate or re-generate feedback report for an interview session.
    """
    stmt = select(InterviewModel).where(InterviewModel.id == interview_id)
    res = await db.execute(stmt)
    db_intv = res.scalar_one_or_none()

    if not db_intv:
        raise HTTPException(status_code=404, detail="Interview not found.")

    # Load messages
    msg_stmt = select(InterviewMessageModel).where(InterviewMessageModel.interview_id == interview_id).order_by(InterviewMessageModel.timestamp.asc())
    msg_res = await db.execute(msg_stmt)
    db_msgs = msg_res.scalars().all()

    transcript = [
        InterviewMessage(
            role=m.role,
            content=m.content,
            timestamp=m.timestamp,
            round_type=m.round_type,
            question_idx=m.question_idx
        )
        for m in db_msgs
    ]

    # Load violations
    viol_stmt = select(ProctoringViolationModel).where(ProctoringViolationModel.interview_id == interview_id)
    viol_res = await db.execute(viol_stmt)
    db_viols = viol_res.scalars().all()

    violations = [
        ProctoringViolation(
            violation_type=v.violation_type,
            details=v.details,
            timestamp=v.timestamp
        )
        for v in db_viols
    ]

    report = await feedback_service.generate_report(
        interview_id=interview_id,
        user_id=user_id,
        company=db_intv.company,
        role=db_intv.role,
        transcript=transcript,
        violations=violations,
        body_language_samples=[]
    )

    # Persist or update
    existing_stmt = select(FeedbackReportModel).where(FeedbackReportModel.interview_id == interview_id)
    existing_res = await db.execute(existing_stmt)
    existing = existing_res.scalar_one_or_none()

    if existing:
        existing.overall_score = report.overall_score
        existing.letter_grade = report.letter_grade
        existing.hire_recommendation = report.hire_recommendation
        existing.section_scores = [s.model_dump() for s in report.section_scores]
        existing.communication = report.communication.model_dump()
        existing.body_language = report.body_language.model_dump()
        existing.proctoring = report.proctoring.model_dump()
        existing.strengths = report.top_strengths
        existing.weaknesses = report.top_weaknesses
        existing.roadmap = [r.model_dump() for r in report.improvement_roadmap_14_days]
        existing.summary = report.detailed_summary
    else:
        new_fb = FeedbackReportModel(
            id=report.feedback_id,
            interview_id=interview_id,
            user_id=user_id,
            overall_score=report.overall_score,
            letter_grade=report.letter_grade,
            hire_recommendation=report.hire_recommendation,
            section_scores=[s.model_dump() for s in report.section_scores],
            communication=report.communication.model_dump(),
            body_language=report.body_language.model_dump(),
            code_quality=report.code_quality.model_dump() if report.code_quality else None,
            proctoring=report.proctoring.model_dump(),
            strengths=report.top_strengths,
            weaknesses=report.top_weaknesses,
            roadmap=[r.model_dump() for r in report.improvement_roadmap_14_days],
            summary=report.detailed_summary
        )
        db.add(new_fb)

    await db.commit()
    return report
