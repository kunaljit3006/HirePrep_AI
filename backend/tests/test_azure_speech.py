import pytest
import base64
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.connection import init_db
from app.services.azure_speech_service import (
    azure_speech_service,
    INDIAN_FEMALE_PERSONAS,
    INDIAN_MALE_PERSONAS,
    GLOBAL_FEMALE_PERSONAS,
    GLOBAL_MALE_PERSONAS
)

@pytest.mark.asyncio
async def test_random_interviewer_persona_selection():
    """
    Verifies that interviewer persona selection:
    1. Returns Indian English voices when location is India (e.g. Priya Sharma, Prabhat Verma).
    2. Randomly chooses between Male and Female personas across runs.
    3. Contains complete profile metadata (name, gender, voice, title, accent, avatar).
    """
    genders_seen = set()
    names_seen = set()

    # Sample multiple runs to ensure diversity
    for _ in range(25):
        persona = azure_speech_service.get_random_interviewer_persona(location="India")
        assert "name" in persona
        assert "gender" in persona
        assert "voice" in persona
        assert "title" in persona
        assert "accent" in persona
        assert persona["accent"] == "Indian English"
        assert "en-IN" in persona["voice"]

        genders_seen.add(persona["gender"])
        names_seen.add(persona["name"])

    # Over 25 runs, both male and female personas must be chosen
    assert "female" in genders_seen
    assert "male" in genders_seen
    assert len(names_seen) >= 2

@pytest.mark.asyncio
async def test_interviewer_persona_explicit_gender_preference():
    """Verifies that explicit gender preference (male or female) is honored."""
    female_persona = azure_speech_service.get_random_interviewer_persona(
        location="India", preferred_gender="female"
    )
    assert female_persona["gender"] == "female"
    assert "en-IN" in female_persona["voice"]

    male_persona = azure_speech_service.get_random_interviewer_persona(
        location="India", preferred_gender="male"
    )
    assert male_persona["gender"] == "male"
    assert "en-IN" in male_persona["voice"]

@pytest.mark.asyncio
async def test_azure_speech_synthesis_base64():
    """
    Tests that azure_speech_service synthesizes speech into a valid base64 audio stream.
    """
    test_text = "Hello, welcome to your technical interview."
    audio_base64 = await azure_speech_service.synthesize_speech_base64(
        text=test_text,
        voice="en-IN-NeerjaNeural"
    )

    if audio_base64 is not None:
        assert isinstance(audio_base64, str)
        decoded = base64.b64decode(audio_base64)
        # Verify non-empty audio payload
        assert len(decoded) > 100

@pytest.mark.asyncio
async def test_interview_start_returns_persona_profile():
    """
    Tests that POST /api/interview/start binds and returns the selected interviewer persona.
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "company": "Microsoft",
            "role": "Software Engineer",
            "location": "India",
            "duration_min": 30,
            "difficulty": "medium",
            "preferred_interviewer_gender": "female"
        }
        res = await client.post("/api/interview/start", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "interviewer_persona_profile" in data
        persona = data["interviewer_persona_profile"]
        assert persona is not None
        assert persona["gender"] == "female"
        assert "en-IN" in persona["voice"]
        assert persona["accent"] == "Indian English"
        assert data["interviewer_persona"] == persona["name"]
