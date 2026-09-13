import os
import io
import base64
import random
import logging
from typing import Dict, Any, Optional, List
import httpx
import edge_tts

from app.config import settings

logger = logging.getLogger("hireprep.speech")

INDIAN_FEMALE_PERSONAS: List[Dict[str, Any]] = [
    {
        "name": "Priya Sharma",
        "gender": "female",
        "voice": "en-IN-NeerjaExpressiveNeural",
        "title": "Lead Distributed Systems Architect",
        "accent": "Indian English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Priya"
    },
    {
        "name": "Kavya Menon",
        "gender": "female",
        "voice": "en-IN-NeerjaNeural",
        "title": "Principal Engineering Lead",
        "accent": "Indian English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Kavya"
    },
    {
        "name": "Ananya Sen",
        "gender": "female",
        "voice": "en-IN-NeerjaExpressiveNeural",
        "title": "Bar Raiser & Staff Engineer",
        "accent": "Indian English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Ananya"
    }
]

INDIAN_MALE_PERSONAS: List[Dict[str, Any]] = [
    {
        "name": "Prabhat Verma",
        "gender": "male",
        "voice": "en-IN-PrabhatNeural",
        "title": "Principal Infrastructure Architect",
        "accent": "Indian English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Prabhat"
    },
    {
        "name": "Rehaan Kapoor",
        "gender": "male",
        "voice": "en-IN-PrabhatNeural",
        "title": "Amazon Bar Raiser Lead",
        "accent": "Indian English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Rehaan"
    },
    {
        "name": "Madhur Joshi",
        "gender": "male",
        "voice": "en-IN-PrabhatNeural",
        "title": "Google Staff Tech Lead",
        "accent": "Indian English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Madhur"
    }
]

GLOBAL_FEMALE_PERSONAS: List[Dict[str, Any]] = [
    {
        "name": "Sarah Mitchell",
        "gender": "female",
        "voice": "en-US-JennyNeural",
        "title": "Staff Systems Architect",
        "accent": "American English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Sarah"
    },
    {
        "name": "Elena Rostova",
        "gender": "female",
        "voice": "en-US-AvaNeural",
        "title": "Engineering Director",
        "accent": "American English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Elena"
    }
]

GLOBAL_MALE_PERSONAS: List[Dict[str, Any]] = [
    {
        "name": "David Chen",
        "gender": "male",
        "voice": "en-US-BrianNeural",
        "title": "Bar Raiser Lead",
        "accent": "American English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=David"
    },
    {
        "name": "Marcus Vance",
        "gender": "male",
        "voice": "en-US-AndrewNeural",
        "title": "Principal Systems Architect",
        "accent": "American English",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Marcus"
    }
]

import re

def clean_conversational_speech(text: str) -> str:
    """
    Transforms raw question/interviewer text into natural, warm, spoken human speech:
    - Strips code blocks, markdown symbols, asterisks, hash signs, and bullets.
    - If text contains an entire multi-paragraph coding/system design problem statement,
      condenses it into an inviting conversational prompt so the interviewer speaks
      like a natural human peer instead of reading an entire textbook page aloud.
    """
    if not text or not text.strip():
        return ""

    # 1. Strip code blocks
    cleaned = re.sub(r"```[\s\S]*?```", " I have placed the code template in your editor. ", text)
    cleaned = re.sub(r"`[^`]+`", "", cleaned)

    # 2. Strip markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

    # 3. Strip bold/italics
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)

    # 4. Strip bullet points, numbers, and dashes
    cleaned = re.sub(r"^[ \t]*[•\-\*\+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^[ \t]*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # 5. Strip markdown headers
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)

    # 6. Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # 7. Conversational pacing: if text is an overly verbose multi-paragraph spec,
    # keep the first 2-3 sentences for natural spoken delivery.
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    if len(sentences) > 4:
        cleaned = " ".join(sentences[:3])

    return cleaned

class AzureSpeechService:
    @classmethod
    def get_random_interviewer_persona(
        cls,
        location: str = "India",
        preferred_gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Randomly selects a realistic interviewer persona (Male or Female)
        with curated Azure Neural Voices.
        Defaults to authentic Indian English voices for candidates in India.
        """
        loc_lower = (location or "India").lower()
        is_india = "india" in loc_lower or "in" == loc_lower

        if is_india:
            female_pool = INDIAN_FEMALE_PERSONAS
            male_pool = INDIAN_MALE_PERSONAS
        else:
            female_pool = GLOBAL_FEMALE_PERSONAS + INDIAN_FEMALE_PERSONAS
            male_pool = GLOBAL_MALE_PERSONAS + INDIAN_MALE_PERSONAS

        if preferred_gender == "female":
            chosen = random.choice(female_pool)
        elif preferred_gender == "male":
            chosen = random.choice(male_pool)
        else:
            # 50/50 randomized split between male and female personas
            chosen = random.choice(random.choice([female_pool, male_pool]))

        logger.info(f"Assigned Interviewer Persona: {chosen['name']} ({chosen['gender'].capitalize()} - {chosen['accent']}, Voice: {chosen['voice']})")
        return chosen

    @classmethod
    async def synthesize_speech_base64(cls, text: str, voice: Optional[str] = None) -> Optional[str]:
        """
        Synthesizes text into high-fidelity speech audio encoded as base64 string.
        Uses clean conversational speech with warm prosody and natural pacing.
        """
        if not text or not text.strip():
            return None

        # Sanitize to natural spoken English
        clean_text = clean_conversational_speech(text)
        if not clean_text:
            clean_text = text.strip()

        if len(clean_text) > 1200:
            clean_text = clean_text[:1200]

        target_voice = voice or settings.AZURE_SPEECH_VOICE or "en-IN-NeerjaNeural"

        # 1. If official Azure Speech Key is present, use official Azure Cognitive Services with warm prosody
        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            try:
                endpoint = f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
                headers = {
                    "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                    "User-Agent": "HirePrep_AI"
                }
                ssml = (
                    f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>"
                    f"<voice name='{target_voice}'>"
                    f"<prosody rate='-3%' pitch='+1Hz'>"
                    f"{clean_text}"
                    f"</prosody></voice></speak>"
                )
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(endpoint, headers=headers, content=ssml.encode("utf-8"))
                    if resp.status_code == 200:
                        return base64.b64encode(resp.content).decode("utf-8")
                    else:
                        logger.warning(f"Azure Speech API returned status {resp.status_code}. Falling back to Neural Edge-TTS.")
            except Exception as e:
                logger.warning(f"Azure Speech API error: {e}. Falling back to Neural Edge-TTS.")

        # 2. High-Fidelity Neural Fallback using edge-tts with warm prosody rate (-3%)
        candidate_voices = [target_voice]
        if "en-IN" in target_voice:
            candidate_voices.extend(["en-IN-PrabhatNeural", "en-IN-NeerjaExpressiveNeural"])
        else:
            candidate_voices.extend(["en-US-BrianNeural", "en-US-AvaNeural"])

        for v in candidate_voices:
            try:
                communicate = edge_tts.Communicate(clean_text, v, rate="-3%")
                audio_buffer = bytearray()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.extend(chunk["data"])

                if audio_buffer:
                    return base64.b64encode(audio_buffer).decode("utf-8")
            except Exception as e:
                logger.warning(f"Voice '{v}' synthesis note: {e}")
                continue

        return None

azure_speech_service = AzureSpeechService()
