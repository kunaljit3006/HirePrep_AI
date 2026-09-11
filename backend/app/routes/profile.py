import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user_id
from app.db.connection import get_db
from app.db.models import ResumeModel, ProfileModel
from app.models.resume import ProfileLinks
from app.models.profile import ScrapedProfilesData
from app.services.profile_aggregator import profile_aggregator
from app.services.github_service import github_service
from app.services.leetcode_service import leetcode_service
from app.services.codeforces_service import codeforces_service

router = APIRouter(prefix="/api/profile", tags=["Coding Profiles"])

@router.post("/scrape-from-resume/{resume_id}", response_model=ScrapedProfilesData)
async def scrape_profiles_from_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Scrapes ONLY the coding profiles explicitly detected in the candidate's resume.
    If a platform was not mentioned in the resume, it is skipped.
    """
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    db_resume = result.scalar_one_or_none()

    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    coding_profiles_dict = db_resume.parsed_data.get("coding_profiles", {})
    profile_links = ProfileLinks(**coding_profiles_dict)

    # Scrape only detected platforms
    scraped: ScrapedProfilesData = await profile_aggregator.aggregate_profiles_from_resume(
        user_id=user_id,
        profile_links=profile_links
    )

    # Persist scraped profiles to DB
    for platform in scraped.scanned_profiles:
        data_obj = getattr(scraped, platform, None)
        if data_obj:
            p_model = ProfileModel(
                id=f"prof-{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                platform=platform,
                handle=getattr(data_obj, "username", getattr(data_obj, "handle", "unknown")),
                data=data_obj.model_dump()
            )
            db.add(p_model)

    await db.commit()
    return scraped

@router.get("/github/{username}")
async def get_github_profile(username: str):
    """Fetch GitHub profile stats for a username."""
    data = await github_service.fetch_profile(username)
    if not data:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    return data

@router.get("/leetcode/{username}")
async def get_leetcode_profile(username: str):
    """Fetch LeetCode stats for a username."""
    data = await leetcode_service.fetch_profile(username)
    if not data:
        raise HTTPException(status_code=404, detail="LeetCode user not found.")
    return data

@router.get("/codeforces/{handle}")
async def get_codeforces_profile(handle: str):
    """Fetch Codeforces stats for a handle."""
    data = await codeforces_service.fetch_profile(handle)
    if not data:
        raise HTTPException(status_code=404, detail="Codeforces handle not found.")
    return data
