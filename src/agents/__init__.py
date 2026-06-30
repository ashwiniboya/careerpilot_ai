"""CareerPilot Agent Registry."""
from src.agents.base_agent import BaseCareerAgent
from src.agents.resume_agent import ResumeAgent
from src.agents.ats_agent import ATSAgent
from src.agents.interview_agent import InterviewAgent
from src.agents.roadmap_agent import RoadmapAgent
from src.agents.app_agent import ApplicationAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.critic import CriticAgent

__all__ = [
    "BaseCareerAgent",
    "ResumeAgent",
    "ATSAgent",
    "InterviewAgent",
    "RoadmapAgent",
    "ApplicationAgent",
    "OrchestratorAgent",
    "CriticAgent",
]
