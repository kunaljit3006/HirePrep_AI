import pytest
from app.services.question_service import question_service

@pytest.mark.asyncio
async def test_question_bank_generation():
    questions = await question_service.generate_question_bank(
        company="Google",
        role="Software Engineer (L4)",
        location="India",
        tech_stack=["Python", "Distributed Systems", "PostgreSQL"]
    )

    assert len(questions) >= 3
    round_types = {q.round_type for q in questions}
    # Should include coding, behavioral, or system design
    assert "coding" in round_types or "behavioral" in round_types
    for q in questions:
        assert q.title is not None
        assert q.description is not None
        assert q.difficulty in ["easy", "medium", "hard"]
