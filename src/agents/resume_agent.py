"""
ResumeAgent — analyzes and rewrites resumes.

Uses the RESUME_AGENT_INSTRUCTION system prompt and exposes two MCP tools:
  - parse_resume (via MCP file_tools wrapper)
  - calculate_ats_score (lightweight version without LLM)
"""
from __future__ import annotations

from typing import Any, List

from config.prompts import RESUME_AGENT_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


def _parse_resume_tool(file_path: str) -> dict:
    """MCP-style tool: parse a local resume file and return structured data."""
    from custom_mcp.tools.resume_tools import parse_resume_content
    return parse_resume_content(file_path)


def _ats_score_tool(resume_content: str, job_description: str) -> dict:
    """MCP-style tool: compute ATS keyword match metrics."""
    from custom_mcp.tools.resume_tools import calculate_ats_metrics
    return calculate_ats_metrics(resume_content, job_description)


class ResumeAgent(BaseCareerAgent):
    """Specialized agent for resume analysis and improvement."""

    @property
    def agent_name(self) -> str:
        return "resume_agent"

    @property
    def agent_description(self) -> str:
        return (
            "Analyzes and rewrites resumes. Provides structural feedback, "
            "keyword recommendations, and ATS readiness ratings."
        )

    @property
    def instruction(self) -> str:
        return RESUME_AGENT_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "resume_agent"

    def _build_tools(self) -> List[Any]:
        return [_parse_resume_tool, _ats_score_tool]
