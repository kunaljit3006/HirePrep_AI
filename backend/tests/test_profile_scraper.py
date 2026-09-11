import pytest
from app.models.resume import ProfileLinks
from app.services.profile_aggregator import profile_aggregator

@pytest.mark.asyncio
async def test_selective_profile_scraping():
    # Candidate mentions GitHub and LeetCode ONLY (No Codeforces, No CodeChef)
    links = ProfileLinks(
        github="https://github.com/torvalds",
        leetcode="https://leetcode.com/u/tourist"
    )

    scraped = await profile_aggregator.aggregate_profiles_from_resume("user-123", links)

    # Asserts that ONLY github and leetcode were scraped
    assert "github" in scraped.scanned_profiles
    assert "leetcode" in scraped.scanned_profiles
    assert "codeforces" not in scraped.scanned_profiles
    assert "codechef" not in scraped.scanned_profiles
    assert "kaggle" not in scraped.scanned_profiles

    # Check that data is populated
    assert scraped.github is not None
    assert scraped.leetcode is not None
    assert scraped.codeforces is None
    assert scraped.summary_for_interviewer is not None
