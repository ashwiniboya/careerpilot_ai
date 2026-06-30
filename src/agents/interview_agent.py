"""
InterviewAgent — stateful mock interview conductor.

Uses the INTERVIEW_AGENT_INSTRUCTION system prompt.
Generates contextually appropriate questions and evaluates candidate answers
using a structured scoring rubric (Communication, Technical Accuracy, Structure, Depth).
"""
from __future__ import annotations

from typing import Any, List

from config.prompts import INTERVIEW_AGENT_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


def _get_company_insights_tool(company_name: str) -> dict:
    """Tool: fetch company culture, tech stack, and recent updates for interview prep."""
    from custom_mcp.tools.search_tools import get_company_profile
    return get_company_profile(company_name)


def _web_search_tool(query: str) -> dict:
    """Tool: search the web for interview questions or company information."""
    import asyncio
    from custom_mcp.tools.search_tools import execute_web_search

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, execute_web_search(query))
                return {"results": future.result()}
        return {"results": loop.run_until_complete(execute_web_search(query))}
    except Exception as e:
        return {"results": [], "error": str(e)}


class InterviewAgent(BaseCareerAgent):
    """Stateful mock interview agent with dynamic question generation and answer evaluation."""

    @property
    def agent_name(self) -> str:
        return "interview_agent"

    @property
    def agent_description(self) -> str:
        return (
            "Conducts realistic mock interviews for any target role and company. "
            "Generates behavioral, technical, and situational questions, "
            "then scores and provides feedback on candidate answers."
        )

    @property
    def instruction(self) -> str:
        return INTERVIEW_AGENT_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "interview_agent"

    def _build_tools(self) -> List[Any]:
        return [_get_company_insights_tool, _web_search_tool]
