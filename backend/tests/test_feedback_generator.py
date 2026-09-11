import pytest
from app.services.feedback_service import feedback_service
from app.models.interview import InterviewMessage
from app.models.proctoring import ProctoringViolation, BodyLanguageSample

@pytest.mark.asyncio
async def test_feedback_generation_with_proctoring():
    transcript = [
        InterviewMessage(
            role="interviewer",
            content="Can you explain how sliding window works in O(N)?",
            timestamp=100.0,
            round_type="coding"
        ),
        InterviewMessage(
            role="candidate",
            content="We maintain two pointers left and right, expanding right until a condition breaks, then shrink from left. This guarantees each element is processed at most twice, resulting in O(N) time.",
            timestamp=120.0,
            round_type="coding"
        )
    ]

    violations = [
        ProctoringViolation(violation_type="tab_switch", timestamp=110.0),
        ProctoringViolation(violation_type="copy_paste_attempt", timestamp=115.0)
    ]

    samples = [
        BodyLanguageSample(timestamp=100.0, eye_contact_score=92.0, confidence_score=85.0, head_stability_score=88.0),
        BodyLanguageSample(timestamp=120.0, eye_contact_score=88.0, confidence_score=84.0, head_stability_score=90.0)
    ]

    report = await feedback_service.generate_report(
        interview_id="test-intv-1",
        user_id="user-001",
        company="Amazon",
        role="SDE-2",
        transcript=transcript,
        violations=violations,
        body_language_samples=samples
    )

    assert report.overall_score > 0
    assert report.letter_grade in ["A+", "A", "B+", "B", "C", "D", "F"]
    assert report.proctoring.tab_switches == 1
    assert report.proctoring.paste_attempts == 1
    # Check that score took deductions for violations (100 - 5 - 10 = 85)
    assert report.proctoring.integrity_score <= 85.0
    assert report.body_language.eye_contact_percentage >= 85.0
    assert len(report.improvement_roadmap_14_days) > 0
