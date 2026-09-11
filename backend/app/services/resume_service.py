import re
import io
import json
import logging
from typing import Optional, Tuple, Dict, Any, List
from app.models.resume import ParsedResume, ProfileLinks, ExperienceItem, ProjectItem, EducationItem
from app.services.llm_service import llm_service

logger = logging.getLogger("hireprep.resume")

PROFILE_PATTERNS = {
    "github": r"https?://(?:www\.)?github\.com/([a-zA-Z0-9\-_]+)/?",
    "leetcode": r"https?://(?:www\.)?leetcode\.com/(?:u/)?([a-zA-Z0-9\-_]+)/?",
    "codeforces": r"https?://(?:www\.)?codeforces\.com/profile/([a-zA-Z0-9\-_]+)/?",
    "codechef": r"https?://(?:www\.)?codechef\.com/users/([a-zA-Z0-9\-_]+)/?",
    "hackerrank": r"https?://(?:www\.)?hackerrank\.com/(?:profile/)?([a-zA-Z0-9\-_]+)/?",
    "kaggle": r"https?://(?:www\.)?kaggle\.com/([a-zA-Z0-9\-_]+)/?",
    "linkedin": r"https?://(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-_]+)/?",
}

class ResumeService:
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extract plain text from PDF using PyMuPDF (fitz) or fallback."""
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            return text.strip()
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}. Trying fallback...")
            return file_bytes.decode("utf-8", errors="ignore")

    @staticmethod
    def extract_text_from_docx(file_bytes: bytes) -> str:
        """Extract plain text from DOCX."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text.strip()
        except Exception as e:
            logger.warning(f"python-docx extraction failed: {e}")
            return file_bytes.decode("utf-8", errors="ignore")

    @classmethod
    def detect_coding_profiles(cls, text: str) -> ProfileLinks:
        """Scan raw resume text with strict regex to find only mentioned coding profiles."""
        profiles = ProfileLinks()
        for platform, pattern in PROFILE_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                full_url = match.group(0).rstrip("/")
                setattr(profiles, platform, full_url)
        return profiles

    @classmethod
    async def parse_resume(cls, file_bytes: bytes, filename: str) -> ParsedResume:
        """Extract text, scan coding profiles, and structure with LLM."""
        if filename.lower().endswith(".pdf"):
            raw_text = cls.extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith((".docx", ".doc")):
            raw_text = cls.extract_text_from_docx(file_bytes)
        else:
            raw_text = file_bytes.decode("utf-8", errors="ignore")

        # Step 1: Deterministic regex scan for coding profiles (ensures no missed handles)
        detected_profiles = cls.detect_coding_profiles(raw_text)

        # Step 2: Use LLM for intelligent structured extraction
        prompt = (
            "You are an expert technical recruiter and resume parser. "
            "Extract structured information from the following resume text. "
            "Return a strictly valid JSON object matching the schema:\n"
            "{\n"
            '  "candidate_name": string,\n'
            '  "email": string,\n'
            '  "phone": string,\n'
            '  "summary": string,\n'
            '  "skills": {"Languages": [string], "Frameworks": [string], "Databases & Tools": [string]},\n'
            '  "experience": [{"title": string, "company": string, "duration": string, "highlights": [string]}],\n'
            '  "projects": [{"name": string, "description": string, "tech_stack": [string], "repo_url": string, "highlights": [string]}],\n'
            '  "education": [{"degree": string, "institution": string, "year": string, "gpa": string}],\n'
            '  "coding_profiles": {"github": string, "leetcode": string, "codeforces": string, "codechef": string, "hackerrank": string, "kaggle": string}\n'
            "}\n"
            "Only include fields that exist in the text. Return pure JSON without markdown backticks."
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Resume Text:\n{raw_text[:4000]}"}
        ]

        llm_response = await llm_service.call("resume_parser", messages)
        
        try:
            # Clean markdown codeblocks if present
            cleaned_json = re.sub(r"^```json\s*", "", llm_response.strip())
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
            parsed_dict = json.loads(cleaned_json)
        except Exception as e:
            logger.warning(f"Failed to parse LLM JSON: {e}. Building from defaults.")
            parsed_dict = {}

        # Merge regex-detected profiles to guarantee accuracy
        coding_profiles_dict = parsed_dict.get("coding_profiles", {})
        for field, value in detected_profiles.model_dump().items():
            if value and not coding_profiles_dict.get(field):
                coding_profiles_dict[field] = value

        # Construct validated Pydantic model
        parsed_resume = ParsedResume(
            candidate_name=parsed_dict.get("candidate_name") or "Candidate",
            email=parsed_dict.get("email"),
            phone=parsed_dict.get("phone"),
            summary=parsed_dict.get("summary"),
            skills=parsed_dict.get("skills", {}),
            experience=[ExperienceItem(**item) for item in parsed_dict.get("experience", [])],
            projects=[ProjectItem(**item) for item in parsed_dict.get("projects", [])],
            education=[EducationItem(**item) for item in parsed_dict.get("education", [])],
            coding_profiles=ProfileLinks(**coding_profiles_dict),
            raw_text=raw_text
        )

        return parsed_resume

resume_service = ResumeService()
