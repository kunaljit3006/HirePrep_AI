import uuid
import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user_id
from app.db.connection import get_db
from app.db.models import ResumeModel
from app.models.resume import ResumeParseResponse, ParsedResume
from app.services.resume_service import resume_service

router = APIRouter(prefix="/api/resume", tags=["Resume"])

@router.post("/upload", response_model=ResumeParseResponse)
async def upload_and_parse_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a resume (PDF or DOCX).
    Extracts text, parses candidate details, and extracts all mentioned coding profile links.
    Saves to the database associated with the caller's user_id.
    """
    if not file.filename.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a PDF or DOCX file."
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Parse resume via service
    parsed_resume: ParsedResume = await resume_service.parse_resume(file_bytes, file.filename)
    
    # Identify detected profile platforms
    detected = [
        platform for platform, url in parsed_resume.coding_profiles.model_dump().items()
        if url is not None
    ]

    resume_id = f"res-{uuid.uuid4().hex[:12]}"

    # Save to database
    db_resume = ResumeModel(
        id=resume_id,
        user_id=user_id,
        file_name=file.filename,
        raw_text=parsed_resume.raw_text,
        parsed_data=parsed_resume.model_dump(),
        detected_profiles=detected
    )
    db.add(db_resume)
    await db.commit()

    return ResumeParseResponse(
        resume_id=resume_id,
        user_id=user_id,
        data=parsed_resume,
        detected_profiles=detected,
        created_at=datetime.datetime.utcnow().isoformat()
    )

@router.get("/latest", response_model=ResumeParseResponse)
async def get_latest_resume(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve the most recently uploaded resume for the active user."""
    stmt = (
        select(ResumeModel)
        .where(ResumeModel.user_id == user_id)
        .order_by(ResumeModel.uploaded_at.desc())
    )
    result = await db.execute(stmt)
    db_resume = result.scalars().first()

    if not db_resume:
        raise HTTPException(status_code=404, detail="No resume uploaded yet for user.")

    parsed_data = ParsedResume(**db_resume.parsed_data)
    return ResumeParseResponse(
        resume_id=db_resume.id,
        user_id=db_resume.user_id,
        data=parsed_data,
        detected_profiles=db_resume.detected_profiles or [],
        created_at=db_resume.uploaded_at.isoformat()
    )

@router.get("/{resume_id}", response_model=ResumeParseResponse)
async def get_parsed_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve an already parsed resume by ID."""
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    db_resume = result.scalar_one_or_none()

    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    parsed_data = ParsedResume(**db_resume.parsed_data)
    return ResumeParseResponse(
        resume_id=db_resume.id,
        user_id=db_resume.user_id,
        data=parsed_data,
        detected_profiles=db_resume.detected_profiles or [],
        created_at=db_resume.uploaded_at.isoformat()
    )
