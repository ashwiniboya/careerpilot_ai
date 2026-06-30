"""
ATSAgent — detailed ATS (Applicant Tracking System) scoring agent.

Calculates keyword match rates, identifies missing critical keywords,
flags formatting issues, and provides remediation recommendations.
"""
from __future__ import annotations

from typing import Any, List

from config.prompts import ATS_AGENT_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


def _calculate_ats_score_tool(resume_content: str, job_description: str) -> dict:
    """Tool: compute ATS keyword match metrics between resume and job description."""
    from custom_mcp.tools.resume_tools import calculate_ats_metrics
    return calculate_ats_metrics(resume_content, job_description)


def _extract_skills_tool(text: str) -> list:
    """Tool: extract a list of skills from any block of text."""
    from custom_mcp.tools.resume_tools import extract_skills
    return extract_skills(text)


class ATSAgent(BaseCareerAgent):
    """Specialized agent for ATS compatibility analysis."""

    @property
    def agent_name(self) -> str:
        return "ats_agent"

    @property
    def agent_description(self) -> str:
        return (
            "Evaluates resumes against job descriptions for ATS compatibility. "
            "Computes keyword match rates, identifies missing terms, and flags formatting issues."
        )

    @property
    def instruction(self) -> str:
        return ATS_AGENT_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "ats_agent"

    def _build_tools(self) -> List[Any]:
        return [_calculate_ats_score_tool, _extract_skills_tool]
