"""
RoadmapAgent — personalized career roadmap generator.

Synthesizes the user's current skills, target role, timeline, and
weekly commitment to produce a time-bound, phased learning roadmap.
"""
from __future__ import annotations

from typing import Any, List

from config.prompts import ROADMAP_AGENT_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


def _generate_roadmap_tool(current_skills: list, target_role: str) -> dict:
    """Tool: generate a structured career roadmap skeleton."""
    from custom_mcp.tools.tracking_tools import generate_roadmap_structure
    steps = generate_roadmap_structure(current_skills, target_role)
    return {"status": "success", "steps": steps}


def _recommend_courses_tool(skills: list) -> dict:
    """Tool: recommend courses and resources for a list of skills to acquire."""
    from custom_mcp.tools.tracking_tools import recommend_courses
    return {"status": "success", "courses": recommend_courses(skills)}


def _web_search_tool(query: str) -> dict:
    """Tool: search for learning resources and market trends."""
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


class RoadmapAgent(BaseCareerAgent):
    """Generates phased, time-bound career learning roadmaps."""

    @property
    def agent_name(self) -> str:
        return "roadmap_agent"

    @property
    def agent_description(self) -> str:
        return (
            "Builds personalized, time-bound career roadmaps. "
            "Identifies skill gaps, sequences learning logically, "
            "and recommends specific resources for each phase."
        )

    @property
    def instruction(self) -> str:
        return ROADMAP_AGENT_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "roadmap_agent"

    def _build_tools(self) -> List[Any]:
        return [_generate_roadmap_tool, _recommend_courses_tool, _web_search_tool]
