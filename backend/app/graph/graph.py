import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import InterviewState
from app.graph.nodes.supervisor import supervisor_node
from app.graph.nodes.resume_parser import resume_parser_node
from app.graph.nodes.profile_scraper import profile_scraper_node
from app.graph.nodes.question_researcher import question_researcher_node
from app.graph.nodes.interview_conductor import interview_conductor_node
from app.graph.nodes.evaluate_response import evaluate_response_node
from app.graph.nodes.feedback_generator import feedback_generator_node

logger = logging.getLogger("hireprep.graph")

def route_by_phase(state: InterviewState) -> str:
    """Routes from supervisor to the corresponding phase node."""
    phase = state.get("phase", "setup")
    if phase == "setup":
        return "resume_parser"
    elif phase == "scrape":
        return "profile_scraper"
    elif phase == "prep":
        return "question_researcher"
    elif phase == "interview":
        return "interview_conductor"
    elif phase == "awaiting_candidate":
        return END
    elif phase == "evaluate":
        return "evaluate_response"
    elif phase == "feedback":
        return "feedback_generator"
    elif phase == "done":
        return END
    return END

def build_interview_graph():
    """
    Constructs and compiles the full multi-agent state graph for HirePrep_AI.
    """
    workflow = StateGraph(InterviewState)

    # 1. Register All Agent Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("resume_parser", resume_parser_node)
    workflow.add_node("profile_scraper", profile_scraper_node)
    workflow.add_node("question_researcher", question_researcher_node)
    workflow.add_node("interview_conductor", interview_conductor_node)
    workflow.add_node("evaluate_response", evaluate_response_node)
    workflow.add_node("feedback_generator", feedback_generator_node)

    # 2. Set Entry Point to Supervisor
    workflow.set_entry_point("supervisor")

    # 3. Add Conditional Edges from Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_by_phase,
        {
            "resume_parser": "resume_parser",
            "profile_scraper": "profile_scraper",
            "question_researcher": "question_researcher",
            "interview_conductor": "interview_conductor",
            "evaluate_response": "evaluate_response",
            "feedback_generator": "feedback_generator",
            END: END
        }
    )

    # 4. Connect Worker Nodes back to Supervisor
    workflow.add_edge("resume_parser", "supervisor")
    workflow.add_edge("profile_scraper", "supervisor")
    workflow.add_edge("question_researcher", "supervisor")
    workflow.add_edge("interview_conductor", "supervisor")
    workflow.add_edge("evaluate_response", "supervisor")
    workflow.add_edge("feedback_generator", "supervisor")

    # 5. Compile with In-Memory Checkpointer (easily switched to PostgresSaver for Supabase)
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    logger.info("HirePrep_AI LangGraph workflow successfully compiled.")
    return app

# Singleton compiled graph instance
interview_graph = build_interview_graph()
