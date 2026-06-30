"""
CriticAgent — quality assurance reviewer for all agent outputs.

Evaluates responses from other agents before they reach the user,
checking for factual accuracy, specificity, safety, and JSON validity.
The Orchestrator calls this agent after every sub-agent response.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from config.prompts import CRITIC_AGENT_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


class CriticAgent(BaseCareerAgent):
    """
    Safety & Quality verification agent.

    Usage:
        critic = CriticAgent()
        result = critic.review(agent_name="resume_agent", response="...")
        if result["approved"]:
            send_to_user(result.get("response"))
        else:
            re_run_agent(result["revised_response"])
    """

    @property
    def agent_name(self) -> str:
        return "critic_agent"

    @property
    def agent_description(self) -> str:
        return (
            "Reviews agent outputs for factual accuracy, specificity, safety, "
            "completeness, and tone before they are presented to the user."
        )

    @property
    def instruction(self) -> str:
        return CRITIC_AGENT_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "critic"

    def _build_tools(self) -> List[Any]:
        # Critic does not need external tools — it reasons over provided text
        return []

    # ------------------------------------------------------------------
    # High-level review interface
    # ------------------------------------------------------------------

    def review(
        self,
        agent_name: str,
        response: str,
        original_prompt: Optional[str] = None,
        session_id: str = "critic_review",
    ) -> Dict[str, Any]:
        """
        Synchronous review entry-point.

        Args:
            agent_name: Name of the agent whose output is being reviewed.
            response:   The raw response text to evaluate.
            original_prompt: The user prompt that triggered the response (optional context).
            session_id: ADK session identifier.

        Returns:
            dict with keys:
                approved (bool), confidence (float), issues_found (list),
                severity (str), revised_response (str|None), explanation (str),
                response (str)  ← the final text to use
        """
        review_prompt = self._build_review_prompt(agent_name, response, original_prompt)
        raw = self.run(review_prompt, session_id=session_id)

        parsed = self.parse_json_response(raw)
        if parsed is None:
            # Fallback: approve with warning if LLM response can't be parsed
            logger.warning(f"[{self.agent_name}] Could not parse critic response — defaulting to approve.")
            parsed = {
                "approved": True,
                "confidence": 0.5,
                "issues_found": ["Critic response was unparseable"],
                "severity": "Warning",
                "revised_response": None,
                "explanation": "Critic output was not valid JSON; auto-approved with caution.",
            }

        # Attach the final usable response for the caller's convenience
        if parsed.get("approved", True):
            parsed["response"] = response
        else:
            parsed["response"] = parsed.get("revised_response") or response

        logger.info(
            f"[{self.agent_name}] Review of '{agent_name}': "
            f"approved={parsed.get('approved')}, severity={parsed.get('severity')}"
        )
        return parsed

    # ------------------------------------------------------------------
    # Offline stub for environments without API key
    # ------------------------------------------------------------------

    def review_offline(self, agent_name: str, response: str) -> Dict[str, Any]:
        """Offline fallback — approves the response without LLM evaluation."""
        return {
            "approved": True,
            "confidence": 1.0,
            "issues_found": [],
            "severity": "Minor",
            "revised_response": None,
            "explanation": "Offline mode: critic skipped.",
            "response": response,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_review_prompt(
        agent_name: str,
        response: str,
        original_prompt: Optional[str],
    ) -> str:
        prompt_ctx = f"\n\nOriginal user request:\n{original_prompt}" if original_prompt else ""
        return (
            f"Agent under review: **{agent_name}**{prompt_ctx}\n\n"
            f"Agent response to evaluate:\n---\n{response}\n---\n\n"
            "Please evaluate this response according to your review criteria "
            "and respond with the structured JSON evaluation."
        )
