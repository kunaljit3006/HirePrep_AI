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
    1. Gathers web intelligence about the company's interview process.
    2. Determines the dynamic interview round structure (company+role specific).
    3. Generates a tailored question bank matching that structure.
    Stores web_intel and structure_notes in state for the conductor to use mid-interview.
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

    # Step 1: Gather web intelligence (Reddit, LeetCode, GFG, HN, GitHub)
    web_intel = await question_service.gather_all_web_intelligence(company, role)
    logger.info(f"Web intelligence gathered for {company} {role}: {len(web_intel)} chars")

    # Step 2: Determine dynamic interview structure based on web intel
    experience_level = "Mid"  # TODO: detect from resume
    dynamic_rounds, structure_notes = await question_service.determine_interview_structure(
        company, role, experience_level, web_intel
    )
    logger.info(f"Dynamic interview structure: {[r['round_type'] for r in dynamic_rounds]}")

    # Step 3: Generate question bank using the dynamic skeleton
    questions = await question_service.generate_question_bank(
        company=company,
        role=role,
        location=location,
        tech_stack=tech_stack[:8],
        resume=resume,
        profile_data=profile_data,
        dynamic_rounds=dynamic_rounds,
        web_intel_text=web_intel
    )

    questions_list = [q.model_dump() for q in questions]
    first_round = questions_list[0]["round_type"] if questions_list else "behavioral"

    logger.info(f"Question researcher generated {len(questions_list)} questions for {company} {role}")

    return {
        "questions": questions_list,
        "current_question_idx": 0,
        "current_round": first_round,
        "phase": "interview",
        "web_intel_context": web_intel,
        "interview_structure_notes": structure_notes,
        "questions_asked_count": 0,
        "score_history": [],
        "topics_covered": [],
        "concept_gaps": [],
        "candidate_strengths": [],
    }

