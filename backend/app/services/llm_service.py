import os
import json
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("hireprep.llm")

# Model routing priority per agent
AGENT_MODELS = {
    "resume_parser": [
        "huggingface/google/gemma-4-12b",
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.0-flash"
    ],
    "profile_scraper": [
        "huggingface/mistralai/Mistral-Small-3.2",
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.0-flash"
    ],
    "question_researcher": [
        "openrouter/deepseek/deepseek-r1",
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.0-flash"
    ],
    "interview_conductor": [
        "groq/meta-llama/Llama-4-Scout",
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.0-flash"
    ],
    "evaluate_response": [
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.0-flash"
    ],
    "feedback_generator": [
        "groq/Qwen/Qwen3-Coder",
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.0-flash",
        "openrouter/deepseek/deepseek-r1"
    ],
}

class LLMService:
    def __init__(self):
        # Set environment variables for litellm if present
        if settings.GROQ_API_KEY:
            os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
        if settings.HUGGINGFACE_API_KEY:
            os.environ["HUGGINGFACE_API_KEY"] = settings.HUGGINGFACE_API_KEY
        if settings.OPENROUTER_API_KEY:
            os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
        if settings.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

    async def call(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Execute an LLM call through LiteLLM with multi-provider fallback.
        If all providers fail or no API keys are provided, falls back to simulated agent responses.
        """
        candidate_models = AGENT_MODELS.get(agent_name, ["groq/llama-3.3-70b-versatile", "gemini/gemini-2.0-flash"])
        
        # Try LiteLLM acompletion across candidate models
        try:
            import litellm
            litellm.suppress_debug_info = True
            for model in candidate_models:
                # Only attempt if provider key or test configuration exists
                provider = model.split("/")[0]
                has_key = (
                    (provider == "groq" and settings.GROQ_API_KEY) or
                    (provider == "huggingface" and settings.HUGGINGFACE_API_KEY) or
                    (provider == "openrouter" and settings.OPENROUTER_API_KEY) or
                    (provider == "gemini" and settings.GEMINI_API_KEY)
                )
                if not has_key:
                    continue

                try:
                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature
                    }
                    if response_format:
                        kwargs["response_format"] = response_format

                    response = await litellm.acompletion(**kwargs)
                    content = response.choices[0].message.content
                    if content:
                        logger.info(f"Agent '{agent_name}' successfully called model '{model}'")
                        return content
                except Exception as e:
                    logger.warning(f"Model '{model}' failed for agent '{agent_name}': {e}. Trying fallback...")
                    continue
        except ImportError:
            logger.warning("litellm not imported, proceeding with fallback")

        # Context-aware deterministic fallback for local dev / offline testing
        return self._generate_fallback(agent_name, messages)

    def _generate_fallback(self, agent_name: str, messages: List[Dict[str, str]]) -> str:
        """
        Provides realistic, structured fallbacks for development and testing
        when external API keys are unavailable.
        """
        last_message = messages[-1]["content"] if messages else ""

        if agent_name == "resume_parser":
            return json.dumps({
                "candidate_name": "Priya Sharma",
                "email": "priya.sharma@example.com",
                "phone": "+91 9876543210",
                "summary": "Full Stack Engineer with 3+ years experience building scalable backend microservices and modern React applications.",
                "skills": {
                    "Languages": ["Python", "JavaScript", "TypeScript", "SQL"],
                    "Frameworks": ["FastAPI", "Django", "React", "Next.js", "Node.js"],
                    "Databases & Cloud": ["PostgreSQL", "Redis", "Docker", "AWS", "Git"]
                },
                "experience": [
                    {
                        "title": "Software Engineer",
                        "company": "TechCorp India",
                        "duration": "2022 - Present",
                        "highlights": [
                            "Built async REST and WebSocket APIs serving 200k+ daily requests.",
                            "Optimized database indexing and caching, cutting p95 query latency by 45%."
                        ]
                    }
                ],
                "projects": [
                    {
                        "name": "CloudScale Distributed Cache",
                        "description": "High-throughput in-memory cache system built using Python and Raft consensus.",
                        "tech_stack": ["Python", "FastAPI", "Redis", "Docker"],
                        "repo_url": "https://github.com/priyasharma/cloudscale-cache",
                        "highlights": ["Benchmarked at 15,000 requests/sec with sub-millisecond response."]
                    }
                ],
                "education": [
                    {
                        "degree": "B.Tech in Computer Science",
                        "institution": "National Institute of Technology",
                        "year": "2022",
                        "gpa": "8.8/10"
                    }
                ],
                "coding_profiles": {
                    "github": "https://github.com/priyasharma",
                    "leetcode": "https://leetcode.com/u/priya_coder",
                    "codeforces": "https://codeforces.com/profile/priyacodes"
                }
            })

        elif agent_name == "question_researcher":
            return json.dumps([
                {
                    "id": "dsa-01",
                    "round_type": "coding",
                    "topic": "Algorithms & HashMaps",
                    "title": "Longest Substring Without Repeating Characters",
                    "description": "Given a string s, find the length of the longest substring without duplicate characters.",
                    "difficulty": "medium",
                    "hints": ["Consider a sliding window approach with two pointers.", "Track the last seen index of each character."],
                    "expected_key_points": ["O(N) time complexity", "O(min(N, M)) space complexity", "Sliding window optimization"],
                    "starter_code": {
                        "python": "class Solution:\n    def lengthOfLongestSubstring(self, s: str) -> int:\n        # Write your code here\n        pass\n"
                    },
                    "test_cases": [
                        {"input": "abcabcbb", "expected_output": "3", "is_hidden": False},
                        {"input": "bbbbb", "expected_output": "1", "is_hidden": False},
                        {"input": "pwwkew", "expected_output": "3", "is_hidden": True}
                    ],
                    "company_context": "Frequently asked in SDE-1 interviews for Google, Amazon, and Uber.",
                    "source_attribution": "LeetCode Discuss & Glassdoor 2024"
                },
                {
                    "id": "resume-01",
                    "round_type": "resume",
                    "topic": "Project Architecture",
                    "title": "Deep-Dive on CloudScale Distributed Cache",
                    "description": "You mentioned building a distributed cache using Python and Raft consensus. Can you explain how you handled node failover and network partitions?",
                    "difficulty": "medium",
                    "hints": ["Explain leader election and log replication."],
                    "expected_key_points": ["Split-brain prevention", "Heartbeat mechanisms", "Quorum consensus"],
                    "company_context": "Probes technical ownership and deep understanding of resume claims.",
                    "source_attribution": "HirePrep Resume Analyzer"
                },
                {
                    "id": "behavioral-01",
                    "round_type": "behavioral",
                    "topic": "Conflict Resolution & Ownership",
                    "title": "Handling Disagreement on Architecture",
                    "description": "Tell me about a time you had a technical disagreement with a senior engineer or team member regarding a system design decision. How did you resolve it?",
                    "difficulty": "medium",
                    "hints": ["Use STAR method (Situation, Task, Action, Result).", "Focus on data and user needs, not ego."],
                    "expected_key_points": ["Active listening", "Benchmarking/prototyping to validate ideas", "Team cohesion"],
                    "company_context": "Amazon Leadership Principle: Have Backbone; Disagree and Commit.",
                    "source_attribution": "Reddit r/cscareerquestions"
                }
            ])

        elif agent_name == "interview_conductor":
            return (
                "Thank you for sharing that. I see from your resume that you built a distributed caching system using Python and Raft. "
                "Could you walk me through the specific trade-offs you considered between consistency and latency when designing the replication protocol?"
            )

        elif agent_name == "evaluate_response":
            return json.dumps({
                "score": 75.0,
                "feedback": "Strong understanding of distributed systems trade-offs and CAP theorem.",
                "difficulty_adjustment": "harder",
                "key_strengths": ["Clear articulation of CAP theorem", "Addressed network latency implications"],
                "areas_to_improve": ["Could have detailed split-brain election timeouts further"]
            })

        elif agent_name == "feedback_generator":
            return json.dumps({
                "overall_score": 82.5,
                "letter_grade": "A",
                "hire_recommendation": "Strong Hire",
                "summary": "Candidate demonstrated solid grasp of core data structures, distributed systems concepts, and communicated articulately throughout the mock interview.",
                "top_strengths": [
                    "Optimal O(N) sliding window implementation in the coding section",
                    "Sound knowledge of Raft consensus and practical trade-offs",
                    "Consistent eye contact and confident verbal delivery"
                ],
                "top_weaknesses": [
                    "Minor pause when discussing network partition edge cases",
                    "Could optimize space complexity explanations earlier in coding"
                ]
            })

        return "Response generated successfully."

llm_service = LLMService()
