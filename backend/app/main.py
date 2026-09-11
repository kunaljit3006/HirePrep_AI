import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.connection import init_db
from app.routes.resume import router as resume_router
from app.routes.profile import router as profile_router
from app.routes.question import router as question_router
from app.routes.interview import router as interview_router
from app.routes.feedback import router as feedback_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("hireprep.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("Initializing HirePrep_AI database tables...")
    await init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("HirePrep_AI Backend shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Multi-Agent AI Mock Interview Platform Backend powered by FastAPI and LangGraph",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Feature Routers
app.include_router(resume_router)
app.include_router(profile_router)
app.include_router(question_router)
app.include_router(interview_router)
app.include_router(feedback_router)

@app.get("/", tags=["System"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "agents": [
            "Resume Parser (Agent 1)",
            "Profile Scraper (Agent 2)",
            "Question Researcher (Agent 3)",
            "Interview Conductor (Agent 4)",
            "Feedback Generator (Agent 5)"
        ],
        "features": {
            "anti_cheat_code_editor": "active",
            "camera_body_language_analysis": "active",
            "selective_profile_scraping": "active",
            "langgraph_state_machine": "active",
            "realtime_websockets": "active"
        }
    }

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "timestamp": settings.VERSION}
