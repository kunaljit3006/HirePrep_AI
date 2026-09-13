import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.config import settings

logger = logging.getLogger("hireprep.llm")

# Model routing priority per agent
AGENT_MODELS = {
    "resume_parser": [
        "groq/openai/gpt-oss-20b",
        "groq/qwen/qwen3.6-27b",
        "gemini/gemini-2.5-flash"
    ],
    "profile_scraper": [
        "groq/openai/gpt-oss-20b",
        "groq/qwen/qwen3.6-27b",
        "gemini/gemini-2.5-flash"
    ],
    "question_researcher": [
        "groq/openai/gpt-oss-120b",
        "groq/openai/gpt-oss-20b",
        "gemini/gemini-2.5-flash"
    ],
    "interview_conductor": [
        "groq/openai/gpt-oss-20b",
        "groq/qwen/qwen3.6-27b",
        "gemini/gemini-2.5-flash"
    ],
    "evaluate_response": [
        "gemini/gemini-2.5-flash",
        "groq/llama3-8b-8192",
        "groq/openai/gpt-oss-20b",
        "groq/qwen/qwen3.6-27b"
    ],
    "feedback_generator": [
        "groq/openai/gpt-oss-120b",
        "groq/openai/gpt-oss-20b",
        "gemini/gemini-2.5-flash"
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
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Any:
        """
        Execute an LLM call through LiteLLM with multi-provider fallback.
        If all providers fail or no API keys are provided, falls back to simulated agent responses.
        If stream=True, returns an AsyncGenerator. Otherwise returns a string.
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
                        "temperature": temperature,
                        "stream": stream
                    }
                    if response_format:
                        kwargs["response_format"] = response_format
                    if max_tokens:
                        kwargs["max_tokens"] = max_tokens

                    response = await litellm.acompletion(**kwargs)
                    
                    if stream:
                        async def stream_generator():
                            async for chunk in response:
                                if getattr(chunk, "choices", None) and len(chunk.choices) > 0:
                                    delta = chunk.choices[0].delta
                                    if getattr(delta, "content", None):
                                        yield delta.content
                        logger.info(f"Agent '{agent_name}' successfully started streaming model '{model}'")
                        return stream_generator()
                    else:
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
        fallback_text = self._generate_fallback(agent_name, messages)
        
        if stream:
            async def fallback_stream():
                # Yield fallback word by word to simulate streaming
                import asyncio
                import re
                words = re.split(r'(\s+)', fallback_text)
                for w in words:
                    yield w
                    await asyncio.sleep(0.02)
            return fallback_stream()
            
        return fallback_text

    def _generate_fallback(self, agent_name: str, messages: List[Dict[str, str]]) -> str:
        """
        Provides realistic, structured fallbacks for development and testing
        when external API keys are unavailable.
        """
        last_message = messages[-1]["content"] if messages else ""
        all_content = " ".join([m.get("content", "") for m in messages]).lower()

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
            if "probing their mention of:" in all_content:
                topic = all_content.split("probing their mention of:")[-1].strip().split("\n")[0]
                if any(w in topic.lower() for w in ["thread", "concurrency", "mutex", "lock", "race"]):
                    return f"Got it. You brought up {topic} there—how did you prevent race conditions or handle synchronization when multiple threads write to shared memory?"
                elif any(w in topic.lower() for w in ["redis", "caching", "cache"]):
                    return f"Understood. You mentioned {topic}—why did you opt for Redis specifically over an in-memory cache, and how do you handle cache invalidation and stale reads?"
                elif any(w in topic.lower() for w in ["kafka", "queue", "rabbitmq"]):
                    return f"Makes sense. You mentioned {topic}—how do you ensure message delivery guarantees and prevent duplicate processing if a consumer fails?"
                return f"Fair point. You mentioned {topic} in your explanation—could you walk me through why you chose that specifically over alternatives, and what trade-offs you considered?"
            return (
                "Thank you for sharing that. Let's move to our next section. "
                "Could you walk me through your design approach, starting with the core data flow and key components?"
            )

        elif agent_name == "evaluate_response":
            candidate_text = ""
            for m in messages:
                content = m.get("content", "")
                if "Candidate Said / Presented:" in content:
                    candidate_text = content.split("Candidate Said / Presented:")[-1].split("Instructions:")[0].split("Evaluation Schema")[0].split("Return pure JSON:")[0].lower()
                    break
                elif "Candidate Said:" in content:
                    candidate_text = content.split("Candidate Said:")[-1].split("Instructions:")[0].split("Evaluation Schema")[0].split("Return pure JSON:")[0].lower()
                    break
                elif "Candidate Answer:" in content:
                    candidate_text = content.split("Candidate Answer:")[-1].split("Instructions:")[0].split("Evaluation Schema")[0].split("Return pure JSON:")[0].lower()
                    break
            target_text = candidate_text if candidate_text else all_content

            # Check if candidate is verifying their thought process / approach ("right track" co-pilot)
            is_approach_phrase = any(phrase in target_text for phrase in [
                "right track", "thinking of using", "thinking about", "am i on the",
                "approach is", "my plan is", "plan to use", "would it make sense to use",
                "thinking of starting with", "heading in the right direction", "on the right path"
            ])
            if is_approach_phrase:
                if any(w in target_text for w in ["two pointer", "two-pointer", "hash map", "hashmap", "hash table", "sliding window", "binary search", "queue", "redis"]):
                    affirmation = (
                        "Yes, exactly! You are on the right track with that approach. "
                        "That will give you optimal time and space efficiency. Go ahead and start implementing it!"
                    )
                    status = "on_track"
                else:
                    affirmation = (
                        "Yes, you are on a good track! The high-level intuition is sound. "
                        "Go ahead and proceed, and keep edge cases in mind as you construct the logic."
                    )
                    status = "on_track"

                return json.dumps({
                    "intent": "approach_check",
                    "affirmation_content": affirmation,
                    "track_status": status,
                    "clarification_answer": None,
                    "hint_content": None,
                    "score": None,
                    "feedback": "Candidate proactively verified algorithmic intuition and approach with the interviewer.",
                    "difficulty_adjustment": "same",
                    "probe_topic": None
                })

            # Check if candidate is asking for a hint
            is_hint_phrase = any(phrase in target_text for phrase in [
                "hint", "stuck", "nudge", "guidance", "help on",
                "how to approach", "clue", "suggest a direction", "small pointer", "give me a pointer"
            ])
            if is_hint_phrase:
                hint_tier = 1
                for m in messages:
                    c = m.get("content", "")
                    if "Current Tier: 2/3" in c:
                        hint_tier = 2
                    elif "Current Tier: 3/3" in c:
                        hint_tier = 3

                if hint_tier == 1:
                    hint_msg = "Sure! Here is a quick pointer: Consider using a Hash Map or Two Pointers to trade a small amount of memory for instant O(1) lookups."
                elif hint_tier == 2:
                    hint_msg = "Take a closer look at what state needs to be maintained: tracking the complement (target - current) allows you to check if the pair has already been visited."
                else:
                    hint_msg = "Here is the concrete approach: as you iterate through the array, insert each number into your hash map after checking if target - current exists."

                return json.dumps({
                    "intent": "hint_request",
                    "clarification_answer": None,
                    "hint_content": hint_msg,
                    "score": None,
                    "feedback": f"Candidate effectively leveraged a Tier {hint_tier} hint to proceed.",
                    "difficulty_adjustment": "same",
                    "probe_topic": None
                })

            # Check if candidate is asking a clarifying question / cross-asking
            is_clarification_phrase = any(phrase in target_text for phrase in [
                "brute force", "optimal", "direct optimal", "do we have to", "should i write",
                "can i assume", "are duplicates", "can there be", "pseudocode", "start with brute",
                "clarify", "is it okay if", "time complexity requirement"
            ])
            has_question_structure = any(token in target_text for token in ["?", "should", "can", "do we", "or"])

            if is_clarification_phrase and has_question_structure:
                if any(w in target_text for w in ["brute force", "optimal", "direct"]):
                    clarification_text = (
                        "Good question! Feel free to outline the brute force intuition briefly in 30 seconds so we are aligned on the baseline, "
                        "but please implement the optimal solution directly in code. Go ahead whenever you are ready!"
                    )
                elif any(w in target_text for w in ["duplicate", "negative", "integer", "range", "constraint"]):
                    clarification_text = (
                        "Great clarifying question. You can assume the input contains valid integers within standard memory limits, "
                        "and there are no special formatting quirks. Please proceed with your implementation."
                    )
                else:
                    clarification_text = (
                        "That is a fair clarifying question! Feel free to make standard production-grade assumptions and explain them as you build out your solution."
                    )

                return json.dumps({
                    "intent": "clarification",
                    "clarification_answer": clarification_text,
                    "score": None,
                    "feedback": "Candidate actively gathered requirements and clarified expectations before implementation.",
                    "difficulty_adjustment": "same",
                    "probe_topic": None
                })

            probe = None
            if any(w in target_text for w in ["multithreading", "threading", "threads", "concurrency", "mutex", "lock", "race condition", "deadlock"]):
                probe = "multithreading synchronization and race conditions"
            elif any(w in target_text for w in ["redis", "caching", "cache", "memcached"]):
                probe = "Redis caching strategy and cache invalidation"
            elif any(w in target_text for w in ["kafka", "queue", "rabbitmq", "pubsub", "pub/sub"]):
                probe = "Kafka messaging guarantees and consumer lag"
            elif any(w in target_text for w in ["sharding", "replication", "partition", "indexing", "b-tree"]):
                probe = "database sharding and indexing trade-offs"
            elif any(w in target_text for w in ["microservices", "microservice", "docker", "kubernetes"]):
                probe = "microservices decoupling and failure isolation"
            return json.dumps({
                "intent": "answer",
                "clarification_answer": None,
                "score": 75.0,
                "feedback": "Demonstrates practical engineering perspective and awareness of systems trade-offs.",
                "difficulty_adjustment": "same",
                "probe_topic": probe
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
