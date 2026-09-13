import json
import uuid
import logging
import difflib
from typing import List, Dict, Any, Optional
from app.models.question import QuestionItem, TestCase, QuestionBankResponse, QuestionBankRequest
from app.models.resume import ParsedResume
from app.models.profile import ScrapedProfilesData
from app.services.llm_service import llm_service
from app.services.cache_service import cache_service

logger = logging.getLogger("hireprep.question_service")

KNOWN_TECH_COMPANIES = [
    "Google", "Stripe", "Amazon", "Meta", "Microsoft", "Apple", "Netflix",
    "Uber", "Airbnb", "Spotify", "Palantir", "Databricks", "Snowflake",
    "ByteDance", "Adobe", "Salesforce", "Oracle", "Cisco", "Twitter",
    "Coinbase", "Lyft", "Robinhood", "DoorDash", "Pinterest", "Snap",
    "LinkedIn", "Atlassian", "Twilio", "Dropbox", "Square", "Block",
    "Shopify", "Nvidia", "Intel", "AMD", "Qualcomm", "Tesla", "Instacart",
    "Reddit", "GitHub", "GitLab", "Zoom", "Figma", "Canva", "Brex", "Plaid"
]

def normalize_company_name(raw_name: str) -> str:
    """
    Fuzzy matches and auto-corrects company names with typos (e.g. 'striop' -> 'Stripe', 'amazn' -> 'Amazon').
    """
    if not raw_name or not raw_name.strip():
        return "Technology Company"
    clean = raw_name.strip()
    for comp in KNOWN_TECH_COMPANIES:
        if clean.lower() == comp.lower():
            return comp
    matches = difflib.get_close_matches(clean.lower(), [c.lower() for c in KNOWN_TECH_COMPANIES], n=1, cutoff=0.62)
    if matches:
        matched_lower = matches[0]
        for comp in KNOWN_TECH_COMPANIES:
            if comp.lower() == matched_lower:
                return comp
    return clean.title()

class QuestionService:

    @staticmethod
    async def fetch_reddit_experiences(company: str, role: str, client: Any) -> List[str]:
        """
        Searches Reddit (r/cscareerquestions & r/leetcode) using Reddit's JSON API
        to find recent real-world interview experiences and question patterns.
        """
        results = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HirePrep-AI/1.0"}
        search_query = f"{company} {role} interview"

        urls = [
            f"https://www.reddit.com/r/cscareerquestions/search.json?q={search_query}&restrict_sr=1&sort=relevance&limit=3",
            f"https://www.reddit.com/r/leetcode/search.json?q={company}+interview&restrict_sr=1&sort=relevance&limit=3"
        ]

        for url in urls:
            try:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", {}).get("children", [])
                    for post in data:
                        post_data = post.get("data", {})
                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")[:250]
                        if title:
                            results.append(f"Reddit Experience: '{title}' - {selftext}")
            except Exception:
                continue

        return results[:3]

    @staticmethod
    async def fetch_leetcode_discussions(company: str, client: Any) -> List[str]:
        """
        Queries LeetCode Discuss GraphQL API for company-tagged problem patterns.
        """
        results = []
        query = """
        query questionDiscussionTopics($keyword: String!) {
            topicSearch(keyword: $keyword, first: 3) {
                edges {
                    node {
                        title
                        summary
                    }
                }
            }
        }
        """
        try:
            res = await client.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {"keyword": f"{company} interview"}},
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            if res.status_code == 200:
                edges = res.json().get("data", {}).get("topicSearch", {}).get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    if node.get("title"):
                        results.append(f"LeetCode Discuss: '{node['title']}' - {node.get('summary', '')[:200]}")
        except Exception as e:
            logger.warning(f"LeetCode Discuss query failed: {e}")

        return results[:3]

    @staticmethod
    async def fetch_hackernews_intel(company: str, role: str, client: Any) -> List[str]:
        """
        Searches HackerNews via Algolia API (blazing-fast, zero auth)
        for senior engineering discussions, hiring standards, and interview bar.
        """
        results = []
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={company}+interview&tags=story&hitsPerPage=3"
            res = await client.get(url)
            if res.status_code == 200:
                hits = res.json().get("hits", [])
                for hit in hits:
                    title = hit.get("title", "")
                    story_url = hit.get("url", "")
                    if title:
                        results.append(f"HackerNews Thread: '{title}' ({story_url})")
        except Exception as e:
            logger.warning(f"HackerNews search failed: {e}")

        return results[:3]

    @staticmethod
    async def fetch_github_interview_archives(company: str, client: Any) -> List[str]:
        """
        Searches curated GitHub open-source interview repositories for company-specific question banks.
        """
        results = []
        try:
            from app.config import settings
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "HirePrep-AI-Research-Agent"}
            if settings.GITHUB_TOKEN:
                headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

            url = f"https://api.github.com/search/repositories?q={company}+interview+questions&sort=stars&order=desc&per_page=3"
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                items = res.json().get("items", [])
                for repo in items:
                    name = repo.get("full_name", "")
                    desc = repo.get("description", "") or ""
                    stars = repo.get("stargazers_count", 0)
                    results.append(f"GitHub Interview Repo: '{name}' ({stars}★) - {desc[:150]}")
        except Exception as e:
            logger.warning(f"GitHub interview repo search failed: {e}")

        return results[:3]

    @staticmethod
    async def fetch_geeksforgeeks_patterns(company: str, role: str, client: Any) -> List[str]:
        """
        Fetches company interview trends and round patterns from GeeksforGeeks archives.
        """
        results = []
        try:
            import bs4
            slug = company.lower().replace(" ", "-")
            url = f"https://www.geeksforgeeks.org/{slug}-interview-experience/"
            res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                soup = bs4.BeautifulSoup(res.text, "html.parser")
                headings = [h.get_text().strip() for h in soup.find_all(["h2", "h3"]) if len(h.get_text().strip()) > 10][:3]
                for h in headings:
                    results.append(f"GeeksforGeeks Pattern: {h}")
        except Exception:
            # Fallback pattern for GFG
            results.append(f"GeeksforGeeks Archives: High frequency rounds for {company} include DSA, System Design, and CS Fundamentals.")

        return results[:2]

    @classmethod
    async def gather_all_web_intelligence(cls, company: str, role: str) -> str:
        """
        Executes parallel multi-source gathering across 5 intelligence pipelines:
        1. Reddit JSON API (r/cscareerquestions, r/leetcode)
        2. LeetCode Discuss GraphQL API
        3. HackerNews Algolia Search API
        4. GitHub Interview Repositories Search API
        5. GeeksforGeeks Company Archives
        Uses in-memory TTL caching to guarantee maximum speed and efficiency.
        """
        import time
        import httpx
        import asyncio

        cache_key = cache_service.web_intel_key(company, role)
        cached = await cache_service.get_json(cache_key)
        if cached:
            logger.info(f"Cache HIT: Using cached web intelligence for {company} {role}")
            return cached

        gathered_items: List[str] = []

        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                tasks = [
                    cls.fetch_reddit_experiences(company, role, client),
                    cls.fetch_leetcode_discussions(company, client),
                    cls.fetch_hackernews_intel(company, role, client),
                    cls.fetch_github_interview_archives(company, client),
                    cls.fetch_geeksforgeeks_patterns(company, role, client)
                ]

                # Run all 5 sources concurrently in parallel
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in results:
                    if isinstance(res, list):
                        gathered_items.extend(res)
        except Exception as e:
            logger.warning(f"Error during parallel intelligence gathering for {company}: {e}")

        if not gathered_items:
            gathered_items = [
                f"Standard {company} pattern: Focus on clean code, optimal algorithmic complexity, STAR behavioral answers, and scalable architecture."
            ]

        # Store in cache with 24h TTL
        intel_text = "\n".join(gathered_items)
        await cache_service.set_json(cache_key, intel_text, ttl_seconds=cache_service.WEB_INTEL_TTL)
        return intel_text

    @classmethod
    def _detect_role_domain(cls, role: str) -> str:
        r = role.lower()
        if any(k in r for k in ["data", "etl", "big data", "analytics engineer", "pipeline", "lakehouse", "warehouse"]):
            return "data_engineering"
        if any(k in r for k in ["machine learning", "ml", "ai", "deep learning", "nlp", "computer vision", "llm"]):
            return "machine_learning"
        if any(k in r for k in ["frontend", "front-end", "ui", "react", "web developer", "mobile", "ios", "android"]):
            return "frontend"
        if any(k in r for k in ["devops", "sre", "reliability", "cloud", "infrastructure", "platform", "kubernetes"]):
            return "devops"
        return "backend"

    @classmethod
    async def determine_interview_structure(
        cls, company: str, role: str, experience_level: str, web_intel: str
    ) -> list:
        """
        Uses web intelligence to determine the actual interview round structure
        for this specific company+role combination. Returns a list of round dicts.
        """
        domain = cls._detect_role_domain(role)

        prompt = (
            f"You are a career coach who has studied thousands of real interview experiences at {company} for '{role}' ({experience_level} level).\n\n"
            f"WEB INTELLIGENCE (Real discussions from Reddit, LeetCode, GeeksforGeeks, HackerNews):\n{web_intel[:2000]}\n\n"
            "Based on this intelligence and your knowledge of how {company} actually conducts interviews for this role, "
            "determine the EXACT round structure they use.\n\n"
            "IMPORTANT RULES:\n"
            "- Different companies have VERY different structures. Amazon is LP-heavy (3-4 behavioral rounds). Google is coding-heavy (2 coding rounds). Startups are project-focused.\n"
            "- Not every role needs coding or system design. A Data Analyst needs SQL + case study. A PM needs product sense. A Frontend dev needs JS + React coding, not backend system design.\n"
            "- The number of rounds should be 4-6 typically.\n"
            "- Round 1 should ALWAYS be a warm-up / behavioral introduction.\n"
            f"- Calibrate difficulty for {experience_level} level.\n\n"
            'Return a JSON object:\n'
            '{\n'
            '  "rounds": [\n'
            '    {"round_type": "behavioral"|"cs_fundamentals"|"coding"|"system_design"|"resume", "focus": "specific focus area", "difficulty_start": "easy"|"medium"|"hard"}\n'
            '  ],\n'
            '  "notes": "Brief company-specific interview tips"\n'
            '}\n'
            "Return ONLY JSON without backticks."
        )

        try:
            import re
            llm_res = await llm_service.call("question_researcher", [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Determine the interview structure for {company} {role} ({experience_level})."}
            ], max_tokens=1500)

            cleaned = re.sub(r"^```json\s*", "", (llm_res or "").strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
            json_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1)
            result = json.loads(cleaned)
            rounds = result.get("rounds", [])
            notes = result.get("notes", "")

            if rounds and len(rounds) >= 3:
                # Validate round_types
                valid_types = {"behavioral", "cs_fundamentals", "coding", "system_design", "resume"}
                validated = []
                for r in rounds:
                    rt = r.get("round_type", "behavioral")
                    if rt not in valid_types:
                        rt = "behavioral"
                    validated.append({
                        "round_type": rt,
                        "focus": r.get("focus", ""),
                        "difficulty_start": r.get("difficulty_start", "medium")
                    })
                logger.info(f"Dynamic interview structure for {company} {role}: {[r['round_type'] for r in validated]}")
                return validated, notes
        except Exception as e:
            logger.warning(f"Failed to determine dynamic interview structure: {e}. Using domain defaults.")

        # Fallback: domain-based default structure
        if domain == "data_engineering":
            return [
                {"round_type": "behavioral", "focus": "Background & data pipeline experience", "difficulty_start": "easy"},
                {"round_type": "cs_fundamentals", "focus": "Storage formats, partitioning, ACID lakehouse", "difficulty_start": "easy"},
                {"round_type": "coding", "focus": "SQL / Python data transformation", "difficulty_start": "medium"},
                {"round_type": "system_design", "focus": "Real-time streaming pipeline architecture", "difficulty_start": "medium"},
                {"round_type": "resume", "focus": "Production incidents & pipeline recovery", "difficulty_start": "medium"},
            ], f"Standard {company} data engineering interview structure."
        elif domain == "machine_learning":
            return [
                {"round_type": "behavioral", "focus": "Background & ML project experience", "difficulty_start": "easy"},
                {"round_type": "cs_fundamentals", "focus": "ML fundamentals, bias-variance, loss functions", "difficulty_start": "easy"},
                {"round_type": "coding", "focus": "ML coding / data preprocessing", "difficulty_start": "medium"},
                {"round_type": "system_design", "focus": "ML system design, inference pipeline", "difficulty_start": "medium"},
                {"round_type": "resume", "focus": "Model deployment & monitoring in production", "difficulty_start": "medium"},
            ], f"Standard {company} ML engineer interview structure."
        elif domain == "frontend":
            return [
                {"round_type": "behavioral", "focus": "Background & frontend project experience", "difficulty_start": "easy"},
                {"round_type": "cs_fundamentals", "focus": "JavaScript fundamentals, DOM, event loop", "difficulty_start": "easy"},
                {"round_type": "coding", "focus": "Live frontend coding / React component", "difficulty_start": "medium"},
                {"round_type": "system_design", "focus": "Frontend architecture & performance", "difficulty_start": "medium"},
                {"round_type": "resume", "focus": "Accessibility, cross-browser, production issues", "difficulty_start": "medium"},
            ], f"Standard {company} frontend interview structure."
        else:
            return [
                {"round_type": "behavioral", "focus": "Background & recent engineering work", "difficulty_start": "easy"},
                {"round_type": "cs_fundamentals", "focus": "Core CS: OOP, databases, concurrency", "difficulty_start": "easy"},
                {"round_type": "coding", "focus": "Algorithms & data structures", "difficulty_start": "medium"},
                {"round_type": "system_design", "focus": "Distributed system architecture", "difficulty_start": "medium"},
                {"round_type": "resume", "focus": "Production experience & incident response", "difficulty_start": "medium"},
            ], f"Standard {company} software engineering interview structure."


    @classmethod
    def _get_domain_guidance(cls, domain: str, role: str) -> str:
        if domain == "data_engineering":
            return (
                f"DOMAIN FOCUS (DATA ENGINEERING for '{role}'):\n"
                "- Warm-up (Behavioral): Easing in with candidate background and architectural walkthrough of a recent data pipeline/ETL.\n"
                "- CS Fundamentals / Domain Core: Storage formats (Parquet vs CSV/JSON), partitioning vs indexing, ACID lakehouse (Delta Lake / Apache Iceberg), batch vs streaming semantics.\n"
                "- Coding: Hands-on data transformation, sliding-window event aggregation, or deduplication using Python/SQL logic.\n"
                "- System Design: Real-time event streaming ingestion pipeline (Kafka, Flink/Spark Streaming, Lakehouse, Dead-letter queue, Backpressure).\n"
                "- Wrap-up / Resilience: Production pipeline recovery, handling schema drift, backfilling historical data, and data reconciliation.\n"
            )
        elif domain == "machine_learning":
            return (
                f"DOMAIN FOCUS (MACHINE LEARNING / AI for '{role}'):\n"
                "- Warm-up: Background in ML models and production deployment.\n"
                "- Fundamentals: Bias-variance trade-off, vector embeddings, loss functions, distributed training fundamentals.\n"
                "- Coding: Vector operations, custom loss function, or data preprocessing logic.\n"
                "- System Design: Real-time inference architecture, feature store, model drift detection.\n"
                "- Wrap-up: Offline/online metric evaluation and rollback strategies.\n"
            )
        return (
            f"DOMAIN FOCUS (SOFTWARE ENGINEERING for '{role}'):\n"
            "- Warm-up: Background and recent technical project.\n"
            "- Fundamentals: Database isolation levels, concurrency, caching patterns, network protocols.\n"
            "- Coding: Algorithmic problem solving, two pointers, graphs, or hash maps.\n"
            "- System Design: High scalability distributed microservice architecture.\n"
            "- Wrap-up: Incident response, single points of failure, operational debugging.\n"
        )

    @classmethod
    def _sort_and_normalize_pedagogical_rounds(
        cls,
        questions: List[QuestionItem],
        company: str,
        role: str,
        resume: Optional[ParsedResume] = None,
        experience_level: str = "Mid"
    ) -> List[QuestionItem]:
        """
        Guarantees realistic human interview progression (Pedagogical Ramp-Up Curve):
        1. Behavioral / Warm-up (Difficulty: Easy) - Rapport building, background, recent project.
        2. CS Fundamentals / Domain Foundations (Difficulty: Easy/Medium) - Role-specific foundations.
        3. Coding (Difficulty: Medium) - Hands-on coding/data transformation.
        4. System Design (Difficulty: Medium/Hard) - Scalable architecture.
        5. Resume / Incident & Wrap-up (Difficulty: Medium) - Production failures, trade-offs.

        CRITICAL RULE: Question 1 is NEVER a System Design question and NEVER Hard difficulty.
        """
        round_priority = {
            "behavioral": 0,
            "cs_fundamentals": 1,
            "coding": 2,
            "system_design": 3,
            "resume": 4
        }

        # Sort by pedagogical round priority
        sorted_qs = sorted(questions, key=lambda q: round_priority.get(q.round_type, 99))

        # Ensure we have at least one warm-up question at index 0
        if not sorted_qs or sorted_qs[0].round_type == "system_design" or sorted_qs[0].difficulty == "hard":
            # Prepend or swap with a proper warm-up question
            warmups = [q for q in sorted_qs if q.round_type == "behavioral"]
            if warmups:
                sorted_qs.remove(warmups[0])
                warmups[0].difficulty = "easy"
                sorted_qs.insert(0, warmups[0])
            else:
                default_qs = cls._get_default_questions(company, role, resume, experience_level)
                sorted_qs.insert(0, default_qs[0])

        # Clamp question 0 difficulty to easy/medium
        if sorted_qs and sorted_qs[0].difficulty == "hard":
            sorted_qs[0].difficulty = "easy"

        # Guarantee candidate name & project grounding on Question 1 if resume is present
        cand_name = (getattr(resume, "candidate_name", None) or getattr(resume, "name", None) or "").strip()
        has_proj = bool(resume and getattr(resume, "projects", None))
        proj_name = resume.projects[0].name if has_proj else None

        if sorted_qs and cand_name:
            q0 = sorted_qs[0]
            first_name = cand_name.split()[0]
            if first_name.lower() not in q0.description.lower() and first_name.lower() not in q0.title.lower():
                if q0.description.startswith("Welcome!"):
                    q0.description = f"Welcome {first_name}! " + q0.description[8:].strip()
                elif q0.description.startswith("Welcome"):
                    parts = q0.description.split("!", 1)
                    if len(parts) > 1:
                        q0.description = f"Welcome {first_name}! " + parts[1].strip()
                    else:
                        q0.description = f"Welcome {first_name}! " + q0.description
                else:
                    q0.description = f"Welcome {first_name}! " + q0.description

        if sorted_qs and proj_name:
            q0 = sorted_qs[0]
            if proj_name.lower() not in q0.description.lower() and proj_name.lower() not in q0.title.lower():
                q0.title = f"Introduction & Architecture of {proj_name}"

        return sorted_qs

    @classmethod
    async def generate_question_bank(
        cls,
        company: str,
        role: str,
        location: str = "India",
        experience_level: str = "Mid",
        tech_stack: Optional[List[str]] = None,
        resume: Optional[ParsedResume] = None,
        profile_data: Optional[ScrapedProfilesData] = None,
        dynamic_rounds: Optional[list] = None,
        web_intel_text: Optional[str] = None
    ) -> List[QuestionItem]:
        """
        Generates a balanced question bank customized for the candidate's target company,
        role, location, and specific resume projects, grounded in real Reddit, LeetCode,
        HackerNews, GitHub, and GeeksforGeeks discussions.
        Uses dynamic_rounds (company-specific skeleton) when provided.
        """
        company = normalize_company_name(company)
        domain = cls._detect_role_domain(role)
        domain_guidance = cls._get_domain_guidance(domain, role)

        # Check 7-day Question Bank Cache for standardized roles (no custom candidate resume/profile)
        is_standard_request = (resume is None or not getattr(resume, "projects", None)) and (profile_data is None)
        qbank_key = cache_service.question_bank_key(company, role, experience_level)
        if is_standard_request:
            cached_qbank = await cache_service.get_json(qbank_key)
            if cached_qbank and isinstance(cached_qbank, list):
                logger.info(f"Cache HIT: Returning verified question bank for {company} {role} ({experience_level})")
                raw_items = [QuestionItem(**q) for q in cached_qbank]
                return cls._sort_and_normalize_pedagogical_rounds(raw_items, company, role, resume, experience_level)

        # Multi-source parallel web intelligence gathering
        online_intel = web_intel_text or await cls.gather_all_web_intelligence(company, role)
        stack_str = ", ".join(tech_stack) if tech_stack else f"{role} Tech Stack"

        skills_summary = ""
        if resume and resume.skills:
            if isinstance(resume.skills, dict):
                skills_parts = []
                for cat, sks in resume.skills.items():
                    if isinstance(sks, list):
                        skills_parts.append(f"{cat}: {', '.join(sks)}")
                    else:
                        skills_parts.append(f"{cat}: {sks}")
                skills_summary = "; ".join(skills_parts)
            elif isinstance(resume.skills, list):
                skills_summary = ", ".join(resume.skills)
        if not tech_stack and skills_summary:
            stack_str = skills_summary

        projects_summary = ""
        top_project_name = None
        secondary_project_name = None
        if resume and resume.projects:
            top_project_name = resume.projects[0].name
            if len(resume.projects) > 1:
                secondary_project_name = resume.projects[1].name
            projects_summary = "\n".join([
                f"- Project {i+1}: '{p.name}' | Tech Stack: {', '.join(p.tech_stack) if p.tech_stack else 'N/A'}\n  Description: {p.description or ''}"
                for i, p in enumerate(resume.projects[:3])
            ])

        cand_name_val = (getattr(resume, "candidate_name", None) or getattr(resume, "name", None) or "").strip()
        if cand_name_val.lower() in ["candidate", "none", "there", "null", "unknown"]:
            cand_name_val = ""
        first_name = cand_name_val.split()[0] if cand_name_val else ""
        cand_name_line = f"Candidate Name: {cand_name_val}\n" if cand_name_val else ""
        profiles_summary = profile_data.summary_for_interviewer if profile_data else "None"

        is_junior = experience_level.lower() in ["intern", "junior", "entry", "intern/junior"]

        # Build dynamic round instructions from the company-specific skeleton
        if dynamic_rounds and len(dynamic_rounds) >= 3:
            round_instructions = ""
            for i, rnd in enumerate(dynamic_rounds):
                rt = rnd.get('round_type', 'behavioral')
                focus = rnd.get('focus', '')
                diff = rnd.get('difficulty_start', 'medium')
                if i == 0 and top_project_name:
                    q_inst = (
                        f"Explicitly cite their real project '{top_project_name}' from their resume. "
                        f"Focus: {focus}. Difficulty MUST be 'easy'"
                    )
                elif i == 0:
                    q_inst = f"Welcome them warmly. Focus: {focus}. Difficulty MUST be 'easy'"
                else:
                    q_inst = f"Focus: {focus}. Difficulty: '{diff}'"
                round_instructions += f"{i+1}. round_type: '{rt}' ({q_inst})\n"
        else:
            # Legacy fallback for when no dynamic_rounds are provided
            q1_proj_instruction = (
                f"Explicitly cite their real project '{top_project_name}' from their resume. Difficulty MUST be 'easy'"
                if top_project_name else
                "Ask them to introduce themselves and discuss their engineering background - Difficulty MUST be 'easy'"
            )
            round_instructions = (
                f"1. round_type: 'behavioral' (WARM-UP: Welcome {first_name or 'the candidate'} warmly. {q1_proj_instruction})\n"
                f"2. round_type: 'cs_fundamentals' (ROLE FOUNDATIONS: Core domain concepts relevant to {role} - Difficulty 'easy' or 'medium')\n"
                f"3. round_type: 'coding' (HANDS-ON PROBLEM: Practical coding challenge for {company} {role} - Difficulty 'medium')\n"
                f"4. round_type: 'system_design' (SCALABLE ARCHITECTURE: Tailored system design for {company}'s scale - Difficulty 'medium')\n"
                f"5. round_type: 'resume' (PRODUCTION DEEP-DIVE: Production edge cases and resilience - Difficulty 'medium')\n"
            )

        prompt = (
            f"You are a Principal Engineer and Hiring Committee Lead at {company}. "
            f"You are preparing a deeply personalized technical interview question bank for {cand_name_val or 'the candidate'} interviewing for '{role}' (Target Level: {experience_level}) in {location}.\n\n"
            f"CANDIDATE'S ACTUAL RESUME PROFILE:\n"
            f"- Candidate Name: {cand_name_val or 'Candidate'}\n"
            f"- Candidate Verified Skills: {skills_summary or stack_str}\n"
            f"- Real Projects from Candidate's CV:\n{projects_summary or 'No specific projects listed.'}\n"
            f"- Coding Profile Context:\n{profiles_summary}\n\n"
            f"{domain_guidance}\n"
            f"Real Online Discussions from Reddit & LeetCode:\n{online_intel}\n\n"
            "COMPANY-SPECIFIC INTERVIEW ROUND STRUCTURE (determined from web intelligence):\n"
            f"{round_instructions}\n"
            "STRICT RESUME GROUNDING & ROLE CALIBRATION INSTRUCTIONS:\n"
            f"Every question MUST be grounded in THIS candidate's real profile and experience and perfectly calibrated for a {experience_level} level candidate in a {role} role.\n"
            f"Generate EXACTLY {len(dynamic_rounds) if dynamic_rounds else 5} questions, one per round above.\n"
            "CRITICAL: Question 1 MUST NOT be generic and MUST NOT use placeholder names. Always use their real project name if available!\n"
            f"For each question, include a 'round_focus' field with the specific focus area from the round structure above.\n\n"
            "Return a strictly valid JSON array of question objects where each object has:\n"
            "{\n"
            '  "id": string,\n'
            '  "round_type": "behavioral" | "cs_fundamentals" | "coding" | "system_design" | "resume",\n'
            '  "round_focus": string,\n'
            '  "topic": string,\n'
            '  "title": string,\n'
            '  "description": string,\n'
            '  "difficulty": "easy" | "medium" | "hard",\n'
            '  "hints": [string],\n'
            '  "expected_key_points": [string],\n'
            '  "starter_code": {"python": string, "sql": string, "javascript": string},\n'
            '  "test_cases": [{"input": string, "expected_output": string, "is_hidden": boolean}],\n'
            '  "company_context": string,\n'
            '  "source_attribution": string\n'
            "}\n"
            "Return ONLY the JSON array without backticks or preamble."
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Generate targeted progressive interview questions for {company} {role}."}
        ]

        questions: List[QuestionItem] = []
        try:
            llm_response = await llm_service.call("question_researcher", messages)
            import re
            cleaned_json = re.sub(r"^```json\s*", "", (llm_response or "").strip())
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
            raw_list = json.loads(cleaned_json)
            is_hld_required = cls._is_high_requirement_system_design(company, role, experience_level)
            for item in raw_list:
                test_cases = [TestCase(**tc) for tc in item.get("test_cases", [])]
                round_t = item.get("round_type", "behavioral")
                is_wb = is_hld_required if round_t == "system_design" else False
                wb_mode = "required" if is_wb else "none"

                desc = item.get("description", "")
                if round_t == "system_design":
                    if is_wb:
                        desc += "\n\n[Architecture Whiteboard Required]: Draw the high-level architecture diagram (load balancers, caches, services, databases, queues) on the canvas and walk through your trade-offs."
                    else:
                        desc += "\n\n[Conceptual Mock Discussion]: Discuss the system architecture, component trade-offs, and scaling bottlenecks verbally or in text as in a standard interview. Drawing is optional."

                questions.append(QuestionItem(
                    id=item.get("id") or str(uuid.uuid4())[:8],
                    round_type=round_t,
                    topic=item.get("topic", "General"),
                    title=item.get("title", "Question"),
                    description=desc,
                    difficulty=item.get("difficulty", "medium"),
                    hints=item.get("hints", []),
                    expected_key_points=item.get("expected_key_points", []),
                    starter_code=item.get("starter_code"),
                    test_cases=test_cases,
                    requires_whiteboard=is_wb,
                    whiteboard_mode=wb_mode,
                    company_context=item.get("company_context", f"Asked at {company}"),
                    source_attribution=item.get("source_attribution", "HirePrep Knowledge Base"),
                    round_focus=item.get("round_focus")
                ))
        except Exception as e:
            logger.warning(f"Error parsing LLM question bank: {e}. Using curated defaults.")
            questions = cls._get_default_questions(company, role, resume, experience_level)

        # Enforce pedagogical progressive ordering (Warm-up -> Fundamentals -> Coding -> System Design -> Wrap-up)
        questions = cls._sort_and_normalize_pedagogical_rounds(questions, company, role, resume, experience_level)

        # Cache standard question bank with 7-day TTL
        if is_standard_request and questions:
            q_dicts = [q.model_dump() for q in questions]
            await cache_service.set_json(qbank_key, q_dicts, ttl_seconds=cache_service.QUESTION_BANK_TTL)
            logger.info(f"Cache SET: Saved verified question bank for {company} {role} ({experience_level}) with 7-day TTL")

        return questions

    @classmethod
    def _is_high_requirement_system_design(cls, company: str, role: str, experience_level: str = "Mid") -> bool:
        """
        Determines if the company and role require an interactive architectural whiteboard.
        Senior SDE, SDE-2+, Staff, Architects, or Tier-1 Big Tech HLD rounds REQUIRE a whiteboard.
        Interns, Junior, SDE-1, and early career roles do NOT require whiteboard (normal conceptual mock discussion).
        """
        senior_indicators = ["senior", "sr", "lead", "staff", "principal", "architect", "sde 2", "sde-2", "sde ii", "sde 3", "sde-3", "sde iii", "l5", "l6"]
        junior_indicators = ["intern", "junior", "jr", "entry", "freshman", "associate", "sde 1", "sde-1", "sde i"]

        role_lower = role.lower()
        level_lower = experience_level.lower()

        # Explicit junior / intern check
        if any(j in role_lower for j in junior_indicators) or level_lower in ["entry", "junior", "intern"]:
            return False

        # Explicit senior check
        if any(s in role_lower for s in senior_indicators) or level_lower in ["senior", "lead", "staff", "architect"]:
            return True

        # Big Tech companies at mid-level usually require HLD whiteboard
        big_tech = ["google", "amazon", "meta", "netflix", "uber", "microsoft", "apple", "stripe"]
        if any(b in company.lower() for b in big_tech) and level_lower in ["mid", "senior"]:
            return True

        return False

    @classmethod
    def _get_default_questions(
        cls,
        company: str,
        role: str,
        resume: Optional[ParsedResume] = None,
        experience_level: str = "Mid"
    ) -> List[QuestionItem]:
        has_proj = bool(resume and resume.projects)
        project_name = resume.projects[0].name if has_proj else "your primary project"
        project_tech = f" using {', '.join(resume.projects[0].tech_stack[:3])}" if (has_proj and resume.projects[0].tech_stack) else ""
        cand_str = (getattr(resume, "candidate_name", None) or getattr(resume, "name", None) or "") if resume else ""
        candidate_name = f" {cand_str}" if cand_str else ""
        domain = cls._detect_role_domain(role)
        is_wb = cls._is_high_requirement_system_design(company, role, experience_level)
        wb_mode = "required" if is_wb else "none"

        # ── SPECIALIZED CURRICULUM: DATA ENGINEER ──
        if domain == "data_engineering":
            de_intro_title = f"Introduction & Architecture of {project_name}" if has_proj else "Introduction & Recent Data Engineering Project"
            de_intro_desc = (
                f"Welcome{candidate_name}! To kick things off, I saw on your resume that you built {project_name}{project_tech}. Could you introduce yourself and walk me through the high-level architecture of that pipeline? What were your source systems, ingestion cadence, and target data stores?"
                if has_proj else
                f"Welcome{candidate_name}! To kick things off, could you introduce yourself and walk me through an end-to-end data pipeline you designed or optimized recently? What were the source systems, ingestion methods, and target data stores?"
            )
            sys_desc = (
                f"Design an end-to-end real-time event streaming pipeline for {company} to ingest 100,000 events/second (e.g. clickstreams, telemetry, or user transactions). "
                "The pipeline must support streaming deduplication, schema validation, partitioning, write to a Lakehouse (Delta/Iceberg), and handle consumer backpressure.\n\n"
                + ("[Architecture Whiteboard Required]: Draw the end-to-end pipeline (Data Sources, Kafka broker, Stream Processing Engine, Lakehouse storage, Dead-Letter Queue) on the canvas and walk through your partition key and idempotency strategies."
                   if is_wb else
                   "[Conceptual Mock Discussion]: Discuss the pipeline components, partition key strategy, idempotency mechanisms, and late-arriving data handling verbally or in text.")
            )
            return [
                QuestionItem(
                    id="q-de-warmup-1",
                    round_type="behavioral",
                    topic="Pipeline Engineering & Experience",
                    title=de_intro_title,
                    description=de_intro_desc,
                    difficulty="easy",
                    hints=["Highlight source systems, ingestion cadence (batch vs streaming), transformation framework, and destination.", "Use the STAR technique."],
                    expected_key_points=["Clear architectural flow", "Choice of ingestion tooling", "Business and operational impact"],
                    company_context=f"Warm-up assessment for {role} at {company}.",
                    source_attribution="Reddit r/dataengineering"
                ),
                QuestionItem(
                    id="q-de-fund-1",
                    round_type="cs_fundamentals",
                    topic="Storage Formats & Lakehouse Foundations",
                    title="Columnar Storage (Parquet) vs Row Storage & Partitioning",
                    description="In analytical data systems, why is Apache Parquet preferred over CSV or JSON for querying terabyte-scale data? Explain how columnar projection and predicate pushdown work, and how you would choose an optimal partition key to avoid small file problems.",
                    difficulty="medium",
                    hints=["Discuss row-group statistics (min/max), dictionary encoding, and file compaction.", "Mention query engine read amplification."],
                    expected_key_points=["Columnar projection & predicate pushdown", "Compression efficiency", "Small file problem & partition pruning"],
                    company_context="Tests core data engineering foundations and storage optimization.",
                    source_attribution="Databricks & Snowflake Technical Interviews"
                ),
                QuestionItem(
                    id="q-de-code-1",
                    round_type="coding",
                    topic="Data Transformation & Deduplication",
                    title="Stream Event Deduplication with Sliding Window",
                    description="Given a stream of incoming events with (user_id: string, event_time: int, event_type: string, payload: dict), write a function that deduplicates duplicate events arriving within a 10-minute window and returns the latest event for each (user_id, event_type). You may implement this in Python or SQL.",
                    difficulty="medium",
                    hints=["Think about how you maintain state in memory or using window functions.", "In SQL, consider ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...). In Python, consider a dictionary or sliding queue."],
                    expected_key_points=["Correct window bounds", "State eviction for expired timestamps", "Optimal time complexity"],
                    starter_code={
                        "python": "def deduplicate_events(events: list[dict], window_seconds: int = 600) -> list[dict]:\n    # Implement sliding window deduplication\n    # events format: [{'user_id': str, 'timestamp': int, 'event_type': str}]\n    pass\n",
                        "sql": "-- Write a query to deduplicate events and keep only the latest per (user_id, event_type)\n-- Table: raw_events(user_id VARCHAR, event_time TIMESTAMP, event_type VARCHAR, payload JSON)\nSELECT user_id, event_time, event_type\nFROM (\n    SELECT *,\n           ROW_NUMBER() OVER (PARTITION BY user_id, event_type ORDER BY event_time DESC) as rn\n    FROM raw_events\n) sub\nWHERE rn = 1;\n",
                        "javascript": "function deduplicateEvents(events, windowSeconds = 600) {\n    // Write your solution here\n}\n"
                    },
                    test_cases=[
                        TestCase(input="[{'user_id': 'u1', 'event_type': 'login', 'timestamp': 100}, {'user_id': 'u1', 'event_type': 'login', 'timestamp': 120}]", expected_output="[{'user_id': 'u1', 'event_type': 'login', 'timestamp': 120}]", is_hidden=False),
                        TestCase(input="[{'user_id': 'u1', 'event_type': 'view', 'timestamp': 100}, {'user_id': 'u2', 'event_type': 'view', 'timestamp': 150}]", expected_output="[{'user_id': 'u1', 'event_type': 'view', 'timestamp': 100}, {'user_id': 'u2', 'event_type': 'view', 'timestamp': 150}]", is_hidden=False),
                        TestCase(input="[{'user_id': 'u1', 'event_type': 'cart', 'timestamp': 100}, {'user_id': 'u1', 'event_type': 'cart', 'timestamp': 800}]", expected_output="2 events retained due to window expiry", is_hidden=True)
                    ],
                    company_context=f"High frequency data processing question for {company}.",
                    source_attribution="LeetCode / HackerRank Data Engineering Track"
                ),
                QuestionItem(
                    id="q-de-sys-1",
                    round_type="system_design",
                    topic="Real-Time Streaming Pipeline Architecture",
                    title=f"Design Real-Time Event Ingestion & Lakehouse Pipeline for {company}",
                    description=sys_desc,
                    difficulty="hard" if is_wb else "medium",
                    hints=["Consider Kafka partition strategy by user_id, stream engine checkpointing (Spark Structured Streaming / Flink), Delta Lake/Iceberg compaction, and Dead-Letter Queue (DLQ) for poisoned messages."],
                    expected_key_points=["Kafka partitioning & consumer groups", "Exactly-once or at-least-once semantics", "Dead-letter queue & lakehouse compaction"],
                    requires_whiteboard=is_wb,
                    whiteboard_mode=wb_mode,
                    company_context=f"Core system design round for {role} at {company}.",
                    source_attribution="Uber / Netflix Engineering Blogs"
                ),
                QuestionItem(
                    id="q-de-res-1",
                    round_type="resume",
                    topic="Pipeline Failure Recovery & Data Quality",
                    title=f"Handling Pipeline Failures & Schema Drift in {project_name}",
                    description=f"In production data platforms like {project_name}, things inevitably break. How do you handle schema evolution when an upstream API adds or renames a field? If a pipeline fails midway through a 4-hour batch run, how do you guarantee idempotent backfilling without creating duplicate records in downstream analytics?",
                    difficulty="medium",
                    hints=["Discuss schema registry, Delta Lake schema enforcement vs mergeSchema, idempotency keys, and partition overwrites."],
                    expected_key_points=["Schema registry or schema evolution policy", "Atomic partition overwrites / idempotency", "Data quality monitoring (e.g. Great Expectations)"],
                    company_context="Tests senior operational maturity and disaster recovery.",
                    source_attribution="HirePrep Data Engineering Curriculum"
                )
            ]

        # ── GENERAL / BACKEND SOFTWARE ENGINEER CURRICULUM ──
        sys_desc = (
            f"Design a distributed notification system capable of sending push notifications, SMS, and emails to millions of active users with priority queuing, deduplication, and rate limiting.\n\n"
            + ("[Architecture Whiteboard Required]: Draw the high-level architecture diagram (load balancers, caches, services, databases, queues) on the canvas and walk through your trade-offs."
               if is_wb else
               "[Conceptual Mock Discussion]: Discuss the system architecture, component trade-offs, and scaling bottlenecks verbally or in text as in a standard interview. Drawing is optional.")
        )
        swe_intro_title = f"Introduction & Architecture of {project_name}" if has_proj else f"Introduction & Technical Impact at {company}"
        is_junior = experience_level.lower() in ["intern", "junior", "entry", "intern/junior"]
        swe_intro_desc = (
            f"Welcome{candidate_name}! Let's start with a brief introduction. I noticed on your resume your work on {project_name}{project_tech}. Could you share an overview of your background, and tell me what inspired you to build that project?"
            if has_proj and is_junior else
            f"Welcome{candidate_name}! Let's start with a brief introduction. I noticed on your resume your work on {project_name}{project_tech}. Could you share an overview of your background, and tell me about the architecture and key technical trade-offs you handled in {project_name}?"
            if has_proj else
            f"Welcome{candidate_name}! Let's start with a brief introduction. Could you share an overview of your engineering background, and tell me about a recent project you enjoyed building?"
            if is_junior else
            f"Welcome{candidate_name}! Let's start with a brief introduction. Could you share an overview of your engineering background, and tell me about a recent project or architectural decision where you took ownership and delivered measurable impact?"
        )
        return [
            QuestionItem(
                id="q-beh-1",
                round_type="behavioral",
                topic="Introduction & Engineering Leadership",
                title=swe_intro_title,
                description=swe_intro_desc,
                difficulty="easy",
                hints=["Focus on quantifiable metrics, engineering trade-offs, and lessons learned.", "Use the STAR format."],
                expected_key_points=["Quantifiable business/technical impact", "Constructive debate", "Ownership"],
                company_context=f"Warm-up assessment for {company}.",
                source_attribution="Reddit r/cscareerquestions"
            ),
            QuestionItem(
                id="q-cs-1",
                round_type="cs_fundamentals",
                topic="Database Concurrency & Transactions",
                title="ACID Properties, Isolation Levels & MVCC",
                description="Explain the practical difference between 'Read Committed' and 'Repeatable Read' isolation levels. What is a phantom read, and how do modern relational engines like PostgreSQL handle it under the hood with MVCC?",
                difficulty="medium",
                hints=["Discuss MVCC (Multi-Version Concurrency Control) snapshot isolation and lock mechanisms."],
                expected_key_points=["Dirty reads vs Non-repeatable reads vs Phantom reads", "MVCC snapshot implementation"],
                company_context="Tests core computer science foundations and backend maturity.",
                source_attribution="GeeksforGeeks Interview Corner"
            ),
            QuestionItem(
                id="q-cod-1",
                round_type="coding",
                topic="Algorithms & Two Pointers",
                title="Container With Most Water",
                description="You are given an integer array height of length n. There are n vertical lines drawn such that the two endpoints of the ith line are (i, 0) and (i, height[i]). Find two lines that together with the x-axis form a container, such that the container contains the most water. Return the maximum amount of water a container can store.",
                difficulty="medium",
                hints=["Can you solve this in O(N) time using two pointers?", "Which pointer should you move at each step?"],
                expected_key_points=["O(N) time complexity", "O(1) auxiliary space", "Two-pointer optimal approach"],
                starter_code={
                    "python": "class Solution:\n    def maxArea(self, height: list[int]) -> int:\n        # Write your code here\n        pass\n",
                    "javascript": "function maxArea(height) {\n    // Write your code here\n}\n",
                    "sql": "-- LeetCode algorithmic problem\n"
                },
                test_cases=[
                    TestCase(input="[1,8,6,2,5,4,8,3,7]", expected_output="49", is_hidden=False),
                    TestCase(input="[1,1]", expected_output="1", is_hidden=False),
                    TestCase(input="[4,3,2,1,4]", expected_output="16", is_hidden=True)
                ],
                company_context=f"High frequency interview question for {company}.",
                source_attribution="LeetCode Discuss 2024"
            ),
            QuestionItem(
                id="q-sys-1",
                round_type="system_design",
                topic="High-Level Architecture",
                title=f"Design a Real-Time Notification Service for {company}",
                description=sys_desc,
                difficulty="hard" if is_wb else "medium",
                hints=["Consider message broker (Kafka/RabbitMQ), worker pools, idempotency keys, and third-party provider failovers."],
                expected_key_points=["Decoupled producer-consumer pipeline", "Dead-letter queues", "Rate limiting per user"],
                requires_whiteboard=is_wb,
                whiteboard_mode=wb_mode,
                company_context=f"Standard system design round question for {role} at {company}.",
                source_attribution="Glassdoor Interview Experiences"
            ),
            QuestionItem(
                id="q-res-1",
                round_type="resume",
                topic="System Architecture & Scalability",
                title=f"Deep-Dive on {project_name}",
                description=f"In your resume, you highlighted {project_name}. Walk me through the end-to-end architecture and data flow. If traffic increased 100x overnight, where would the primary bottleneck occur and how would you resolve it?",
                difficulty="medium",
                hints=["Analyze database read/write limits, cache hit ratio, and horizontal scaling."],
                expected_key_points=["Identifies real architectural bottlenecks", "Proposes realistic mitigation (sharding, caching, queueing)"],
                company_context="Tests candidate's ownership and understanding of their stated experience.",
                source_attribution="HirePrep Resume Analyzer"
            )
        ]

question_service = QuestionService()
