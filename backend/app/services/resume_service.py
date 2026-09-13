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
    def extract_name_from_raw_text(cls, raw_text: str) -> Optional[str]:
        """Extract candidate name from top lines of resume text as a deterministic fallback."""
        for line in raw_text.strip().split("\n")[:8]:
            cleaned = re.sub(r"[#*•\-\x83\t]", " ", line).strip()
            if not cleaned:
                continue
            if any(k in cleaned.lower() for k in ["resume", "curriculum vitae", "cv", "profile", "github", "linkedin", "email", "phone", "http", "@"]):
                continue
            words = cleaned.split()
            if 1 <= len(words) <= 4 and all(w.replace("-", "").replace("'", "").isalpha() for w in words) and len(cleaned) < 40:
                return cleaned
        return None

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

        # Deterministic name extraction heuristic
        heuristic_name = cls.extract_name_from_raw_text(raw_text)

        # Step 2: Use LLM for intelligent structured extraction
        prompt = (
            "You are an expert technical recruiter and resume parser. "
            "Extract structured information from the following resume text. "
            "Return a strictly valid JSON object matching the schema:\n"
            "{\n"
            '  "candidate_name": string,\n'
            '  "experience_level": "Intern" | "Junior" | "Mid" | "Senior" | "Staff",\n'
            '  "email": string,\n'
            '  "phone": string,\n'
            '  "summary": string,\n'
            '  "skills": {"Languages": [string], "Frameworks": [string], "Tools": [string]},\n'
            '  "experience": [{"title": string, "company": string, "duration": string}],\n'
            '  "projects": [{"name": string, "description": string, "tech_stack": [string]}],\n'
            '  "education": [{"degree": string, "institution": string, "year": string}],\n'
            '  "coding_profiles": {"github": string, "leetcode": string, "codechef": string}\n'
            "}\n"
            "Return ONLY JSON without markdown backticks."
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Resume Text:\n{raw_text[:6000]}"}
        ]

        llm_response = await llm_service.call("resume_parser", messages, max_tokens=3000)
        
        parsed_dict = {}
        try:
            # Clean markdown codeblocks if present
            cleaned_json = re.sub(r"^```json\s*", "", (llm_response or "").strip())
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
            parsed_dict = json.loads(cleaned_json)
        except Exception as e:
            logger.warning(f"Failed to parse LLM JSON directly: {e}. Attempting robust regex recovery.")
            # Recover candidate_name from LLM response via regex
            name_match = re.search(r'"candidate_name":\s*"([^"]+)"', llm_response or "")
            if name_match:
                parsed_dict["candidate_name"] = name_match.group(1).strip()
            email_match = re.search(r'"email":\s*"([^"]+)"', llm_response or "")
            if email_match:
                parsed_dict["email"] = email_match.group(1).strip()
            phone_match = re.search(r'"phone":\s*"([^"]+)"', llm_response or "")
            if phone_match:
                parsed_dict["phone"] = phone_match.group(1).strip()

            # Recover projects from LLM response
            recovered_projects = []
            proj_matches = re.finditer(r'\{\s*"name":\s*"([^"]+)",\s*"description":\s*"([^"]*)"(?:,\s*"tech_stack":\s*(\[[^\]]*\]))?', llm_response or "")
            for pm in proj_matches:
                p_name = pm.group(1).strip()
                p_desc = pm.group(2).strip()
                p_stack = []
                if pm.group(3):
                    try:
                        p_stack = json.loads(pm.group(3))
                    except Exception:
                        pass
                recovered_projects.append({"name": p_name, "description": p_desc, "tech_stack": p_stack})
            if recovered_projects:
                parsed_dict["projects"] = recovered_projects

            # Heuristic skills fallback
            skills_match = re.search(r"skills?:\s*([^\n\r]+)", raw_text, re.IGNORECASE)
            if skills_match:
                skills_list = [s.strip() for s in skills_match.group(1).split(",") if s.strip()]
                parsed_dict["skills"] = {"Core Skills": skills_list}

        # Guaranteed candidate name resolution
        final_name = (
            parsed_dict.get("candidate_name")
            or heuristic_name
            or "Candidate"
        )
        if final_name.lower() in ["candidate", "null", "none", "unknown"] and heuristic_name:
            final_name = heuristic_name

        # Merge regex-detected profiles to guarantee accuracy
        coding_profiles_dict = parsed_dict.get("coding_profiles", {})
        for field, value in detected_profiles.model_dump().items():
            if value and not coding_profiles_dict.get(field):
                coding_profiles_dict[field] = value

        # Construct validated Pydantic model
        parsed_resume = ParsedResume(
            candidate_name=final_name,
            experience_level=parsed_dict.get("experience_level", "Mid"),
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
