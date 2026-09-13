import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.services.resume_service import resume_service

logger = logging.getLogger("hireprep.node.resume_parser")

async def resume_parser_node(state: InterviewState) -> Dict[str, Any]:
    """
    Resume Parser Node (Agent 1):
    Extracts text from uploaded resume, parses structured candidate profile,
    and extracts all mentioned coding profiles (GitHub, LeetCode, Codeforces, etc.).
    """
    resume_bytes = state.get("resume_bytes")
    filename = state.get("resume_filename") or "resume.pdf"

    if not resume_bytes:
        logger.info("No raw resume bytes provided, using existing or empty profile.")
        return {
            "resume_data": state.get("resume_data") or {},
            "phase": "prep"
        }

    parsed = await resume_service.parse_resume(resume_bytes, filename)
    profile_links_dict = {
        k: v for k, v in parsed.coding_profiles.model_dump().items() if v is not None
    }

    logger.info(f"Resume parsed. Detected profile links: {list(profile_links_dict.keys())}")

    return {
        "candidate_name": parsed.candidate_name,
        "experience_level": parsed.experience_level,
        "resume_data": parsed.model_dump(),
        "detected_profile_links": profile_links_dict,
        "phase": "scrape" if profile_links_dict else "prep"
    }
