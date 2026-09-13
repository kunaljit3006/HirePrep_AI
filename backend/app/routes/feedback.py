from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_current_user_id
from app.db.connection import get_db
from app.db.models import FeedbackReportModel, InterviewModel, InterviewMessageModel, ProctoringViolationModel
from app.models.feedback import (
    FeedbackReportResponse, SectionScore, CommunicationMetrics,
    CameraBodyLanguageReport, CodeQualityReport, RoadmapDay,
    CandidateAnalyticsOverview, PerformanceTrendPoint, SkillsRadarAverage,
    SystemDesignArchitectureReport
)
from app.models.proctoring import ProctoringSummary, ProctoringViolation, BodyLanguageSample
from app.models.interview import InterviewMessage
from app.services.feedback_service import feedback_service
from app.utils.date_utils import format_relative_time, format_friendly_date

router = APIRouter(prefix="/api/feedback", tags=["Feedback & Analytics"])

def build_feedback_response(db_fb: FeedbackReportModel) -> FeedbackReportResponse:
    section_scores = [SectionScore(**s) for s in db_fb.section_scores]
    communication = CommunicationMetrics(**db_fb.communication)
    body_language = CameraBodyLanguageReport(**db_fb.body_language)
    code_quality = CodeQualityReport(**db_fb.code_quality) if db_fb.code_quality else None
    proctoring = ProctoringSummary(**db_fb.proctoring)
    roadmap = [RoadmapDay(**r) for r in db_fb.roadmap]
    architecture_report = (
        SystemDesignArchitectureReport(**db_fb.architecture_report)
        if getattr(db_fb, "architecture_report", None)
        else None
    )

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
        architecture_report=architecture_report,
        proctoring=proctoring,
        top_strengths=db_fb.strengths,
        top_weaknesses=db_fb.weaknesses,
        improvement_roadmap_14_days=roadmap,
        detailed_summary=db_fb.summary,
        created_at=db_fb.created_at.isoformat(),
        formatted_date=format_friendly_date(db_fb.created_at),
        relative_time=format_relative_time(db_fb.created_at)
    )

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

@router.get("/analytics/summary", response_model=CandidateAnalyticsOverview)
async def get_candidate_analytics_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns aggregated performance analytics for the authenticated candidate:
    - Score trends over time (for progression charts)
    - Radar skill breakdown (DSA, System Design, Behavioral, Problem Solving, Communication)
    - Hiring recommendation rate
    - Top recurring strengths and weaknesses
    """
    stmt = (
        select(InterviewModel, FeedbackReportModel)
        .outerjoin(FeedbackReportModel, InterviewModel.id == FeedbackReportModel.interview_id)
        .where(InterviewModel.user_id == user_id)
        .order_by(InterviewModel.created_at.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    total_interviews = len(rows)
    completed = [r for r in rows if r[0].status == "completed" and r[1] is not None]

    if not completed:
        return CandidateAnalyticsOverview(
            user_id=user_id,
            total_interviews_taken=total_interviews,
            completed_interviews=0,
            average_score=0.0,
            highest_score=0.0,
            lowest_score=0.0,
            hire_recommendation_rate=0.0,
            score_trends=[],
            skills_radar=SkillsRadarAverage(
                dsa_score=0.0,
                system_design_score=0.0,
                behavioral_score=0.0,
                problem_solving_score=0.0,
                communication_score=0.0
            ),
            top_recurring_strengths=[],
            top_recurring_weaknesses=[]
        )

    scores = [fb.overall_score for _, fb in completed]
    highest = max(scores)
    lowest = min(scores)
    avg_score = sum(scores) / len(scores)

    hires = sum(1 for _, fb in completed if fb.hire_recommendation in ["Hire", "Strong Hire"])
    hire_rate = round((hires / len(completed)) * 100.0, 1)

    trends = []
    for intv, fb in completed:
        trends.append(PerformanceTrendPoint(
            interview_id=intv.id,
            date=format_friendly_date(intv.created_at),
            relative_time=format_relative_time(intv.created_at),
            company=intv.company,
            role=intv.role,
            overall_score=fb.overall_score,
            letter_grade=fb.letter_grade,
            hire_recommendation=fb.hire_recommendation
        ))

    dsa_scores, sys_scores, beh_scores, prob_scores, comm_scores = [], [], [], [], []
    all_strengths, all_weaknesses = [], []

    for _, fb in completed:
        if fb.strengths:
            all_strengths.extend(fb.strengths)
        if fb.weaknesses:
            all_weaknesses.extend(fb.weaknesses)

        if fb.communication and isinstance(fb.communication, dict) and "clarity_score" in fb.communication:
            comm_scores.append(float(fb.communication["clarity_score"]))

        for sec in (fb.section_scores or []):
            if isinstance(sec, dict):
                name = sec.get("section_name", "").lower()
                s_val = float(sec.get("score", 75.0))
                if "dsa" in name or "algorithm" in name or "data structure" in name:
                    dsa_scores.append(s_val)
                elif "system" in name or "design" in name or "architecture" in name:
                    sys_scores.append(s_val)
                elif "behavioral" in name or "leadership" in name or "culture" in name:
                    beh_scores.append(s_val)
                else:
                    prob_scores.append(s_val)

    def _safe_avg(lst, fallback=75.0):
        return round(sum(lst) / len(lst), 1) if lst else fallback

    radar = SkillsRadarAverage(
        dsa_score=_safe_avg(dsa_scores, avg_score),
        system_design_score=_safe_avg(sys_scores, avg_score),
        behavioral_score=_safe_avg(beh_scores, avg_score),
        problem_solving_score=_safe_avg(prob_scores, avg_score),
        communication_score=_safe_avg(comm_scores, 80.0)
    )

    from collections import Counter
    top_str = [item for item, _ in Counter(all_strengths).most_common(5)]
    top_weak = [item for item, _ in Counter(all_weaknesses).most_common(5)]

    return CandidateAnalyticsOverview(
        user_id=user_id,
        total_interviews_taken=total_interviews,
        completed_interviews=len(completed),
        average_score=round(avg_score, 1),
        highest_score=round(highest, 1),
        lowest_score=round(lowest, 1),
        hire_recommendation_rate=hire_rate,
        score_trends=trends,
        skills_radar=radar,
        top_recurring_strengths=top_str,
        top_recurring_weaknesses=top_weak
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
