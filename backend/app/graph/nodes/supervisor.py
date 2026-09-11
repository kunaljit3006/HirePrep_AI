import logging
from typing import Dict, Any
from app.graph.state import InterviewState

logger = logging.getLogger("hireprep.node.supervisor")

async def supervisor_node(state: InterviewState) -> Dict[str, Any]:
    """
    Supervisor Node:
    Monitors overall interview state and orchestrates phase transitions.
    """
    phase = state.get("phase", "setup")
    logger.info(f"Supervisor evaluating interview {state.get('interview_id')}, current phase: {phase}")

    # Ensure questions list is initialized
    if not state.get("questions"):
        if not state.get("resume_data") and state.get("resume_bytes"):
            return {"phase": "setup"}
        elif not state.get("scraped_profiles") and state.get("detected_profile_links"):
            return {"phase": "scrape"}
        else:
            return {"phase": "prep"}

    # If questions are ready and interview is in progress
    if phase == "interview":
        return {"phase": "interview"}

    if phase == "evaluate":
        return {"phase": "evaluate"}

    if phase == "feedback":
        return {"phase": "feedback"}

    return {"phase": phase}
