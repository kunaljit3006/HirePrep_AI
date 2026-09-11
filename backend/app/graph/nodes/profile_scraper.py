import logging
from typing import Dict, Any
from app.graph.state import InterviewState
from app.models.resume import ProfileLinks
from app.services.profile_aggregator import profile_aggregator

logger = logging.getLogger("hireprep.node.profile_scraper")

async def profile_scraper_node(state: InterviewState) -> Dict[str, Any]:
    """
    Profile Scraper Node (Agent 2):
    Scrapes ONLY coding profiles explicitly detected in the candidate's resume.
    """
    links_dict = state.get("detected_profile_links") or {}
    user_id = state.get("user_id", "default_user")

    if not links_dict:
        logger.info("No coding profile links to scrape. Skipping to preparation phase.")
        return {
            "scraped_profiles": {"summary_for_interviewer": "No external coding profiles found in resume."},
            "phase": "prep"
        }

    profile_links = ProfileLinks(**links_dict)
    scraped_data = await profile_aggregator.aggregate_profiles_from_resume(user_id, profile_links)

    logger.info(f"Successfully scraped platforms: {scraped_data.scanned_profiles}")

    return {
        "scraped_profiles": scraped_data.model_dump(),
        "phase": "prep"
    }
