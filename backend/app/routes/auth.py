import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.connection import get_db
from app.db.models import UserModel, InterviewModel, FeedbackReportModel
from app.dependencies import get_current_user
from app.models.user import (
    UserSyncRequest,
    UserProfileResponse,
    UserUpdateRequest,
    UserStats
)

logger = logging.getLogger("hireprep.auth_routes")

router = APIRouter(prefix="/api/auth", tags=["Authentication & User Management"])

async def _build_user_stats(user_id: str, db: AsyncSession) -> UserStats:
    """Calculates aggregated performance statistics for the candidate."""
    # Total and completed interviews
    stmt = select(
        func.count(InterviewModel.id).label("total"),
        func.count(InterviewModel.id).filter(InterviewModel.status == "completed").label("completed")
    ).where(InterviewModel.user_id == user_id)
    res = await db.execute(stmt)
    total, completed = res.first() or (0, 0)

    # Average score from feedback reports
    stmt_scores = select(func.avg(FeedbackReportModel.overall_score)).where(
        FeedbackReportModel.user_id == user_id
    )
    res_scores = await db.execute(stmt_scores)
    avg_score = res_scores.scalar() or 0.0

    # Fetch latest feedback report for strengths/weaknesses and last interview date
    stmt_latest = (
        select(FeedbackReportModel)
        .where(FeedbackReportModel.user_id == user_id)
        .order_by(FeedbackReportModel.created_at.desc())
        .limit(1)
    )
    res_latest = await db.execute(stmt_latest)
    latest_report = res_latest.scalar_one_or_none()

    strengths = latest_report.strengths[:3] if latest_report and latest_report.strengths else []
    weaknesses = latest_report.weaknesses[:3] if latest_report and latest_report.weaknesses else []
    last_interview = latest_report.created_at.isoformat() if latest_report else None

    return UserStats(
        total_interviews=total or 0,
        completed_interviews=completed or 0,
        average_score=round(float(avg_score), 1),
        top_strengths=strengths,
        top_weaknesses=weaknesses,
        last_interview_at=last_interview
    )

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get profile and interview statistics of the currently authenticated candidate.
    """
    stats = await _build_user_stats(user.id, db)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        name=user.name,
        avatar_url=user.avatar_url,
        github_handle=user.github_handle,
        leetcode_handle=user.leetcode_handle,
        codeforces_handle=user.codeforces_handle,
        target_role=user.target_role or "Full Stack Software Engineer",
        target_company=user.target_company or "Google",
        target_location=user.target_location or "India",
        experience_level=user.experience_level or "Mid",
        stats=stats,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )

@router.post("/sync", response_model=UserProfileResponse)
async def sync_supabase_user(
    req: UserSyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Explicitly synchronizes Supabase user metadata after frontend sign-in or sign-up.
    Upserts user record into the database.
    """
    stmt = select(UserModel).where(UserModel.id == req.id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        user = UserModel(
            id=req.id,
            email=req.email,
            phone=req.phone,
            name=req.name,
            avatar_url=req.avatar_url,
            github_handle=req.github_handle,
            leetcode_handle=req.leetcode_handle,
            codeforces_handle=req.codeforces_handle,
            metadata_info=req.metadata
        )
        db.add(user)
    else:
        if req.email:
            user.email = req.email
        if req.phone:
            user.phone = req.phone
        if req.name:
            user.name = req.name
        if req.avatar_url:
            user.avatar_url = req.avatar_url
        if req.github_handle:
            user.github_handle = req.github_handle
        if req.leetcode_handle:
            user.leetcode_handle = req.leetcode_handle
        if req.codeforces_handle:
            user.codeforces_handle = req.codeforces_handle
        if req.metadata:
            user.metadata_info = req.metadata
        user.updated_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    stats = await _build_user_stats(user.id, db)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        name=user.name,
        avatar_url=user.avatar_url,
        github_handle=user.github_handle,
        leetcode_handle=user.leetcode_handle,
        codeforces_handle=user.codeforces_handle,
        target_role=user.target_role or "Full Stack Software Engineer",
        target_company=user.target_company or "Google",
        target_location=user.target_location or "India",
        experience_level=user.experience_level or "Mid",
        stats=stats,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )

@router.put("/profile", response_model=UserProfileResponse)
async def update_candidate_profile(
    req: UserUpdateRequest,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update candidate's target career preferences and external coding profiles.
    """
    # Ensure user model is active in the current AsyncSession
    stmt = select(UserModel).where(UserModel.id == user.id)
    res = await db.execute(stmt)
    target_user = res.scalar_one_or_none() or user

    if req.name is not None:
        target_user.name = req.name
    if req.phone is not None:
        target_user.phone = req.phone
    if req.avatar_url is not None:
        target_user.avatar_url = req.avatar_url
    if req.github_handle is not None:
        target_user.github_handle = req.github_handle
    if req.leetcode_handle is not None:
        target_user.leetcode_handle = req.leetcode_handle
    if req.codeforces_handle is not None:
        target_user.codeforces_handle = req.codeforces_handle
    if req.target_role is not None:
        target_user.target_role = req.target_role
    if req.target_company is not None:
        target_user.target_company = req.target_company
    if req.target_location is not None:
        target_user.target_location = req.target_location
    if req.experience_level is not None:
        target_user.experience_level = req.experience_level

    target_user.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.add(target_user)
    await db.commit()
    await db.refresh(target_user)
    user = target_user

    stats = await _build_user_stats(user.id, db)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        name=user.name,
        avatar_url=user.avatar_url,
        github_handle=user.github_handle,
        leetcode_handle=user.leetcode_handle,
        codeforces_handle=user.codeforces_handle,
        target_role=user.target_role or "Full Stack Software Engineer",
        target_company=user.target_company or "Google",
        target_location=user.target_location or "India",
        experience_level=user.experience_level or "Mid",
        stats=stats,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )

@router.delete("/account")
async def delete_candidate_account(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently deletes candidate account and cleans up records.
    """
    await db.delete(user)
    await db.commit()
    return {"message": "Account successfully deleted"}

