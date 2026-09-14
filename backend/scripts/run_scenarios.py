import asyncio
import json
import os
from pprint import pprint
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from app.graph.nodes.evaluate_response import evaluate_response_node
from app.graph.nodes.interview_conductor import interview_conductor_node

# Basic mock config
config = {"configurable": {}}

async def run_turn(state, candidate_answer):
    print(f"\n[{state.get('current_round', 'cs_fundamentals').upper()} - Q{state.get('current_question_idx', 0) + 1}] CANDIDATE: {candidate_answer}")
    
    state["latest_candidate_response"] = candidate_answer
    if "transcript" not in state:
        state["transcript"] = []
    
    # 2. Evaluate Response
    eval_result = await evaluate_response_node(state)
    state.update(eval_result)
    
    print(f"[EVALUATOR] Intent: {eval_result.get('intent', 'N/A')} | Score: {eval_result.get('current_score')} | Depth: {eval_result.get('answer_depth')}")
    print(f"[EVALUATOR] Behaviors Proposed: {eval_result.get('behavioral_strategies')}")
    print(f"[EVALUATOR] Validated (recent_behaviors): {eval_result.get('recent_behaviors', [])[-2:]}")
    if eval_result.get('new_memory_items'):
        print(f"[EVALUATOR] Added Memories: {len(eval_result.get('new_memory_items', []))}")
        
    # 3. Interview Conductor
    conductor_result = await interview_conductor_node(state, config)
    state.update(conductor_result)
    
    print("\n[INTERVIEWER RESPONSE]")
    print(conductor_result.get('latest_interviewer_response'))
    
    return state

def create_base_state():
    return {
        "company": "HirePrep",
        "role": "Backend Engineer",
        "interviewer_persona": "standard",
        "questions": [
            {"title": "Polymorphism", "description": "Explain runtime polymorphism.", "round_type": "cs_fundamentals", "expected_key_points": ["method overriding", "dynamic dispatch"]},
            {"title": "Inheritance", "description": "Explain inheritance vs composition.", "round_type": "cs_fundamentals", "expected_key_points": ["is-a vs has-a", "coupling"]},
            {"title": "System Design", "description": "Design a URL shortener.", "round_type": "system_design", "expected_key_points": ["Base62", "Hash collisions"]}
        ],
        "current_question_idx": 0,
        "difficulty_level": "medium",
        "score_history": [],
        "transcript": [],
        "conversation_memory": [],
        "recent_behaviors": [],
        "follow_up_count": 0,
        "candidate_conversational_state": {},
        "resume_data": {"skills": ["Java", "Python", "Kafka"], "projects": [{"name": "Data Pipeline", "tech_stack": ["Kafka", "Spark"]}]}
    }

async def run_scenarios():
    with open("scenario_results.md", "w", encoding="utf-8") as f:
        import sys
        
        # Redirect stdout to both file and terminal
        class Tee(object):
            def __init__(self, *files):
                self.files = files
            def write(self, obj):
                for f in self.files:
                    try:
                        f.write(obj)
                    except UnicodeEncodeError:
                        f.write(obj.encode('cp1252', errors='replace').decode('cp1252'))
                    f.flush()
            def flush(self):
                for f in self.files:
                    f.flush()
        
        sys.stdout = Tee(sys.stdout, f)
        
        print("# Test 1: Strong Candidate")
        state = create_base_state()
        state = await run_turn(state, "I know runtime polymorphism. It occurs through method overriding and dynamic method dispatch.")
        state = await run_turn(state, "When a subclass provides a specific implementation of a method that is already provided by its parent class, that's overriding. At runtime, the JVM uses the vtable to resolve the exact method to call based on the actual object type, not the reference type.")

        print("\n\n# Test 2: Struggling Candidate")
        state = create_base_state()
        state = await run_turn(state, "Runtime polymorphism means the compiler decides which method to execute.")
        state = await run_turn(state, "I guess it means you can have multiple methods with the same name. Like overloading.")
        
        print("\n\n# Test 3 & 4: Resume Project Latching (Kafka)")
        state = create_base_state()
        state = await run_turn(state, "For asynchronous processing, I used Kafka to decouple my microservices in the data pipeline project.")
        
        print("\n\n# Test 5: Nervous Candidate")
        state = create_base_state()
        state = await run_turn(state, "I'm not sure... sorry... give me a second.")
        state = await run_turn(state, "I think it has to do with... um... classes?")
        
        print("\n\n# Test 6: Long Rambling Answer")
        state = create_base_state()
        state = await run_turn(state, "Well, polymorphism is a big topic. Back when I worked at my previous company we used C++ a lot, and we had these massive class hierarchies. We used virtual functions. Virtual functions are how you do it. But we also used templates for compile time polymorphism. I really like templates, they are super fast. Oh, but for runtime, it's method overriding. Yeah, overriding.")
        
        print("\n\n# Test 7: Stronger Memory Correctness Test")
        state = create_base_state()
        state = await run_turn(state, "I used Redis for caching to reduce latency, and Kafka for asynchronous processing so we could handle bursty traffic.")
        # Fast forward, ask a generic question where memory can be referenced
        state['current_question_idx'] = 2
        state = await run_turn(state, "So for this URL shortener, how would you handle high read traffic and separate the read/write load?")
        
        print("\n\n# Test 8: Long-form Interview Simulation (10+ Turns)")
        state = create_base_state()
        turns = [
            "Hi, I'm ready.",
            "Runtime polymorphism is method overriding. Dynamic dispatch handles it.",
            "Um... the vtable stores function pointers, I think.", # A bit weak/hesitant
            "For inheritance, it means one class extends another.",
            "Wait, composition is has-a, right? I usually prefer composition because it avoids tight coupling.", # Strong
            "I used Kafka in my last project for that exact reason.", # Personalization
            "Ah... I'm blanking... sorry give me a moment.", # Hesitation
            "Yeah, we used Kafka to decouple the email service.", 
            "Actually, speaking of databases, we used Postgres. But for the URL shortener I'd probably use a NoSQL database.",
            "I'd use Base62 encoding to generate the short URL hashes."
        ]
        for idx, t in enumerate(turns):
            if idx == 2: state['current_question_idx'] = 1
            if idx == 7: state['current_question_idx'] = 2
            state = await run_turn(state, t)

        sys.stdout = sys.__stdout__

if __name__ == "__main__":
    asyncio.run(run_scenarios())
