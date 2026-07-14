import datetime
from datetime import timezone as _tz
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc), onupdate=lambda: datetime.datetime.now(_tz.utc))

    # Relationships
    profiles = relationship("UserProfile", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    career_history = relationship("CareerHistory", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("InterviewHistory", back_populates="user", cascade="all, delete-orphan")
    skills = relationship("SkillTracking", back_populates="user", cascade="all, delete-orphan")
    roadmaps = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    token_usage = relationship("TokenUsage", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_role = Column(String, nullable=True)
    target_industry = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    target_salary = Column(Float, nullable=True)
    preferences = Column(JSON, nullable=True)  # Store user settings, preferences as JSON
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc), onupdate=lambda: datetime.datetime.now(_tz.utc))

    user = relationship("User", back_populates="profiles")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    content_raw = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)  # Structured JSON (skills, experience, etc.)
    last_ats_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))

    user = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    version_num = Column(Integer, nullable=False)
    content_markdown = Column(Text, nullable=False)
    changes_made = Column(JSON, nullable=True)  # Description of edits made by agents
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))

    resume = relationship("Resume", back_populates="versions")


class CareerHistory(Base):
    __tablename__ = "career_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    skills_used = Column(JSON, nullable=True)  # List of skills utilized in this job

    user = relationship("User", back_populates="career_history")


class InterviewHistory(Base):
    __tablename__ = "interview_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_role = Column(String, nullable=False)
    date_conducted = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))
    overall_score = Column(Float, default=0.0)
    performance_feedback = Column(JSON, nullable=True)  # Detail comments per category
    transcript = Column(JSON, nullable=True)  # Q&A conversation history

    user = relationship("User", back_populates="interviews")


class SkillTracking(Base):
    __tablename__ = "skill_tracking"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)  # Technical, Soft Skill, Domain
    current_proficiency = Column(Integer, default=1)  # 1 to 5
    target_proficiency = Column(Integer, default=5)   # 1 to 5
    last_assessed_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc), onupdate=lambda: datetime.datetime.now(_tz.utc))

    user = relationship("User", back_populates="skills")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_role = Column(String, nullable=False)
    current_step = Column(Integer, default=1)
    total_steps = Column(Integer, default=0)
    status = Column(String, default="active")  # active, completed, paused
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))

    user = relationship("User", back_populates="roadmaps")
    steps = relationship("RoadmapStep", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False)
    step_num = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    recommended_resources = Column(JSON, nullable=True)  # Course URLs, Books, Projects
    status = Column(String, default="pending")  # pending, in_progress, completed
    completed_at = Column(DateTime, nullable=True)

    roadmap = relationship("Roadmap", back_populates="steps")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String, index=True, nullable=False)
    job_title = Column(String, nullable=False)
    job_description = Column(Text, nullable=True)
    status = Column(String, default="applied")  # applied, interviewing, offered, rejected
    applied_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))
    tailored_cover_letter = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="applications")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_type = Column(String, index=True, nullable=False)  # short_term, long_term, preference, goal
    key = Column(String, index=True, nullable=False)
    val = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc), onupdate=lambda: datetime.datetime.now(_tz.utc))

    user = relationship("User", back_populates="memories")


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(_tz.utc))

    user = relationship("User", back_populates="token_usage")
