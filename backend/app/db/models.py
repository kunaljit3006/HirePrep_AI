import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class UserModel(Base):
    """
    Prepared for future Auth & User Management.
    All features reference user_id which seamlessly connects to this model.
    """
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(32), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    github_handle = Column(String(128), nullable=True)
    leetcode_handle = Column(String(128), nullable=True)
    codeforces_handle = Column(String(128), nullable=True)
    target_role = Column(String(128), nullable=True, default="Full Stack Software Engineer")
    target_company = Column(String(128), nullable=True, default="Google")
    target_location = Column(String(128), nullable=True, default="India")
    experience_level = Column(String(64), nullable=True, default="Mid")
    metadata_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class ResumeModel(Base):
    __tablename__ = "resumes"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=False)
    detected_profiles = Column(JSON, nullable=True)  # e.g., ["github", "leetcode", "kaggle"]
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

class ProfileModel(Base):
    __tablename__ = "profiles"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    platform = Column(String(64), nullable=False)  # github, leetcode, codeforces, kaggle
    handle = Column(String(128), nullable=False)
    data = Column(JSON, nullable=False)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)

class QuestionBankModel(Base):
    __tablename__ = "question_banks"

    id = Column(String(64), primary_key=True, index=True)
    company = Column(String(128), index=True, nullable=False)
    role = Column(String(128), index=True, nullable=False)
    location = Column(String(128), nullable=False)
    experience_level = Column(String(64), nullable=False)
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InterviewModel(Base):
    __tablename__ = "interviews"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    company = Column(String(128), nullable=False)
    role = Column(String(128), nullable=False)
    location = Column(String(128), default="India")
    duration_min = Column(Integer, default=30)
    difficulty = Column(String(32), default="medium")
    status = Column(String(32), default="scheduled")  # scheduled, in_progress, completed
    current_round = Column(String(64), default="behavioral")
    current_question_idx = Column(Integer, default=0)
    questions = Column(JSON, nullable=False)
    resume_id = Column(String(64), nullable=True)
    resume_data = Column(JSON, nullable=True)
    candidate_name = Column(String(255), nullable=True)
    architecture_diagram = Column(JSON, nullable=True)
    interviewer_persona = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

class InterviewMessageModel(Base):
    __tablename__ = "interview_messages"

    id = Column(String(64), primary_key=True, index=True)
    interview_id = Column(String(64), index=True, nullable=False)
    role = Column(String(32), nullable=False)  # interviewer, candidate, system
    content = Column(Text, nullable=False)
    round_type = Column(String(64), nullable=True)
    question_idx = Column(Integer, nullable=True)
    timestamp = Column(Float, nullable=False)

class ProctoringViolationModel(Base):
    __tablename__ = "proctoring_violations"

    id = Column(String(64), primary_key=True, index=True)
    interview_id = Column(String(64), index=True, nullable=False)
    violation_type = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(Float, nullable=False)

class FeedbackReportModel(Base):
    __tablename__ = "feedback_reports"

    id = Column(String(64), primary_key=True, index=True)
    interview_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(64), index=True, nullable=False)
    overall_score = Column(Float, nullable=False)
    letter_grade = Column(String(8), nullable=False)
    hire_recommendation = Column(String(32), nullable=False)
    section_scores = Column(JSON, nullable=False)
    communication = Column(JSON, nullable=False)
    body_language = Column(JSON, nullable=False)
    code_quality = Column(JSON, nullable=True)
    architecture_report = Column(JSON, nullable=True)
    proctoring = Column(JSON, nullable=False)
    strengths = Column(JSON, nullable=False)
    weaknesses = Column(JSON, nullable=False)
    roadmap = Column(JSON, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
