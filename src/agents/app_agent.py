"""
ApplicationAgent — job matcher and cover letter generator.

Matches the user's profile against job listings, scores compatibility,
and drafts personalized cover letters for target positions.
"""
from __future__ import annotations

from typing import Any, List, Optional

from config.prompts import APPLICATION_AGENT_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


def _search_jobs_tool(
    skills: list,
    target_role: Optional[str] = None,
    location: str = "Remote",
) -> dict:
    """Tool: query job database for positions matching the candidate profile."""
    from custom_mcp.tools.job_tools import find_jobs
    jobs = find_jobs(skills, target_role, location)
    return {"status": "success", "jobs": jobs}


def _get_company_insights_tool(company_name: str) -> dict:
    """Tool: fetch company description, culture, and tech stack."""
    from custom_mcp.tools.search_tools import get_company_profile
    return get_company_profile(company_name)


class ApplicationAgent(BaseCareerAgent):
    """Agent for job matching, compatibility scoring, and cover letter generation."""

    @property
    def agent_name(self) -> str:
        return "application_agent"

    @property
    def agent_description(self) -> str:
        return (
            "Matches job listings to the candidate's profile, scores compatibility, "
            "and writes personalized, compelling cover letters for target positions."
        )

    @property
    def instruction(self) -> str:
        return APPLICATION_AGENT_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "app_agent"

    def _build_tools(self) -> List[Any]:
        return [_search_jobs_tool, _get_company_insights_tool]
