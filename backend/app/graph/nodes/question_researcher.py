import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.models.resume import ParsedResume
from app.models.profile import ScrapedProfilesData
from app.services.question_service import question_service

logger = logging.getLogger("hireprep.node.question_researcher")

async def question_researcher_node(state: InterviewState) -> Dict[str, Any]:
    """
    Question Researcher Node (Agent 3):
    Generates a company/role/resume-tailored question bank spanning:
    - Behavioral
    - Resume Deep-Dive
    - Coding / DSA
    - System Design
    - CS Fundamentals
    """
    company = state.get("company", "Tech Company")
    role = state.get("role", "Software Engineer")
    location = state.get("location", "India")
    
    resume_dict = state.get("resume_data")
    resume = ParsedResume(**resume_dict) if resume_dict else None

    profile_dict = state.get("scraped_profiles")
    profile_data = ScrapedProfilesData(**profile_dict) if profile_dict else None

    tech_stack = []
    if resume and resume.skills:
        for cat, skills in resume.skills.items():
            tech_stack.extend(skills)

    questions = await question_service.generate_question_bank(
        company=company,
        role=role,
        location=location,
        tech_stack=tech_stack[:8],
        resume=resume,
        profile_data=profile_data
    )

    questions_list = [q.model_dump() for q in questions]
    first_round = questions_list[0]["round_type"] if questions_list else "behavioral"

    logger.info(f"Question researcher generated {len(questions_list)} questions for {company} {role}")

    return {
        "questions": questions_list,
        "current_question_idx": 0,
        "current_round": first_round,
        "phase": "interview"
    }
