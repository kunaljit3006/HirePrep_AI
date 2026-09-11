import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.dependencies import get_current_user_id
from app.db.connection import get_db
from app.db.models import QuestionBankModel, ResumeModel
from app.models.question import QuestionBankRequest, QuestionBankResponse, QuestionItem
from app.models.resume import ParsedResume
from app.services.question_service import question_service

router = APIRouter(prefix="/api/question", tags=["Questions"])

@router.post("/generate", response_model=QuestionBankResponse)
async def generate_questions(
    req: QuestionBankRequest,
    resume_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a curated question bank tailored to target company, role, location,
    tech stack, and candidate resume projects.
    """
    resume = None
    if resume_id:
        stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
        res = await db.execute(stmt)
        db_resume = res.scalar_one_or_none()
        if db_resume:
            resume = ParsedResume(**db_resume.parsed_data)

    questions = await question_service.generate_question_bank(
        company=req.company,
        role=req.role,
        location=req.location,
        experience_level=req.experience_level,
        tech_stack=req.tech_stack,
        resume=resume
    )

    bank_id = f"qbank-{uuid.uuid4().hex[:12]}"
    q_dicts = [q.model_dump() for q in questions]

    db_bank = QuestionBankModel(
        id=bank_id,
        company=req.company,
        role=req.role,
        location=req.location,
        experience_level=req.experience_level,
        questions=q_dicts
    )
    db.add(db_bank)
    await db.commit()

    return QuestionBankResponse(
        bank_id=bank_id,
        company=req.company,
        role=req.role,
        location=req.location,
        total_questions=len(questions),
        questions=questions,
        created_at=datetime.datetime.utcnow().isoformat()
    )

@router.get("/bank/{bank_id}", response_model=QuestionBankResponse)
async def get_question_bank(bank_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve an existing question bank by ID."""
    stmt = select(QuestionBankModel).where(QuestionBankModel.id == bank_id)
    res = await db.execute(stmt)
    db_bank = res.scalar_one_or_none()

    if not db_bank:
        raise HTTPException(status_code=404, detail="Question bank not found.")

    questions = [QuestionItem(**q) for q in db_bank.questions]
    return QuestionBankResponse(
        bank_id=db_bank.id,
        company=db_bank.company,
        role=db_bank.role,
        location=db_bank.location,
        total_questions=len(questions),
        questions=questions,
        created_at=db_bank.created_at.isoformat()
    )
