"""
OrchestratorAgent — central dispatcher for the CareerPilot multi-agent system.

Responsibilities:
  1. Parse user intent from natural language input
  2. Route to appropriate sub-agent(s) based on intent
  3. Enrich sub-agent prompts with memory context
  4. Collect and synthesize sub-agent responses
  5. Run all responses through CriticAgent before returning
  6. Persist interaction to the memory engine

Architecture: Plan → Execute → Criticize (self-correcting loop, max 2 correction passes)
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

from config.prompts import ORCHESTRATOR_INSTRUCTION
from src.agents.base_agent import BaseCareerAgent


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

_INTENT_MAP: Dict[str, str] = {
    "resume":     "resume_agent",
    "cv":         "resume_agent",
    "ats":        "ats_agent",
    "applicant":  "ats_agent",
    "keyword":    "ats_agent",
    "interview":  "interview_agent",
    "mock":       "interview_agent",
    "question":   "interview_agent",
    "roadmap":    "roadmap_agent",
    "learning":   "roadmap_agent",
    "plan":       "roadmap_agent",
    "career path":"roadmap_agent",
    "job":        "application_agent",
    "cover":      "application_agent",
    "apply":      "application_agent",
    "salary":     "application_agent",
}


def _detect_intent(prompt: str) -> str:
    """Simple keyword-based intent classifier. Returns target agent name."""
    lower = prompt.lower()
    for keyword, agent in _INTENT_MAP.items():
        if keyword in lower:
            return agent
    return "general"   # orchestrator handles directly


# ---------------------------------------------------------------------------
# OrchestratorAgent
# ---------------------------------------------------------------------------

class OrchestratorAgent(BaseCareerAgent):
    """
    Master routing and synthesis agent.

    Lazy-loads sub-agents on first use to avoid circular imports
    and to allow running the orchestrator without all agents present.
    """

    def __init__(self, db_session=None, user_id: Optional[int] = None, vector_store=None):
        super().__init__(db_session=db_session, user_id=user_id, vector_store=vector_store)
        self._sub_agents: Dict[str, BaseCareerAgent] = {}
        self._critic: Optional[Any] = None

    # ------------------------------------------------------------------
    # Abstract interface implementation
    # ------------------------------------------------------------------

    @property
    def agent_name(self) -> str:
        return "orchestrator"

    @property
    def agent_description(self) -> str:
        return (
            "Central dispatcher that understands user intent, coordinates specialized "
            "career agents, and synthesizes results into coherent career guidance."
        )

    @property
    def instruction(self) -> str:
        return ORCHESTRATOR_INSTRUCTION

    @property
    def model_key(self) -> str:
        return "orchestrator"

    def _build_tools(self) -> List[Any]:
        # Orchestrator delegates tools to sub-agents; it has none of its own
        return []

    # ------------------------------------------------------------------
    # Sub-agent registry
    # ------------------------------------------------------------------

    def _get_agent(self, agent_name: str) -> Optional[BaseCareerAgent]:
        """Lazily loads a sub-agent by name."""
        if agent_name in self._sub_agents:
            return self._sub_agents[agent_name]

        try:
            kwargs = dict(
                db_session=self._db,
                user_id=self._user_id,
            )
            if agent_name == "resume_agent":
                from src.agents.resume_agent import ResumeAgent
                agent = ResumeAgent(**kwargs)
            elif agent_name == "ats_agent":
                from src.agents.ats_agent import ATSAgent
                agent = ATSAgent(**kwargs)
            elif agent_name == "interview_agent":
                from src.agents.interview_agent import InterviewAgent
                agent = InterviewAgent(**kwargs)
            elif agent_name == "roadmap_agent":
                from src.agents.roadmap_agent import RoadmapAgent
                agent = RoadmapAgent(**kwargs)
            elif agent_name == "application_agent":
                from src.agents.app_agent import ApplicationAgent
                agent = ApplicationAgent(**kwargs)
            else:
                return None

            self._sub_agents[agent_name] = agent
            return agent
        except Exception as e:
            logger.error(f"[orchestrator] Failed to load agent '{agent_name}': {e}")
            return None

    def _get_critic(self):
        if self._critic is None:
            try:
                from src.agents.critic import CriticAgent
                self._critic = CriticAgent(
                    db_session=self._db,
                    user_id=self._user_id,
                )
            except Exception as e:
                logger.warning(f"[orchestrator] Could not load CriticAgent: {e}")
        return self._critic

    # ------------------------------------------------------------------
    # High-level orchestration entry-points
    # ------------------------------------------------------------------

    def chat(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Primary synchronous chat interface.

        Returns:
            {
                "response": <final text for the user>,
                "agent_used": <which agent handled the request>,
                "critic_approved": <bool>,
                "critic_issues": <list>,
            }
        """
        start = time.perf_counter()
        intent = _detect_intent(user_message)
        logger.info(f"[orchestrator] Intent detected: '{intent}' for prompt: {user_message[:80]}")

        # Route to sub-agent or handle directly
        if intent != "general":
            agent = self._get_agent(intent)
            if agent:
                raw_response = agent.run(user_message, session_id=session_id)
                agent_used = intent
            else:
                raw_response = self.run(user_message, session_id=session_id)
                agent_used = "orchestrator"
        else:
            raw_response = self.run(user_message, session_id=session_id)
            agent_used = "orchestrator"

        # Critic review — self-correcting loop (max 2 passes)
        critic = self._get_critic()
        if critic:
            review = critic.review(
                agent_name=agent_used,
                response=raw_response,
                original_prompt=user_message,
                session_id=f"{session_id}_critic",
            )
            final_response = review["response"]
            critic_approved = review.get("approved", True)
            critic_issues = review.get("issues_found", [])

            # One correction pass if critic rejected
            if not critic_approved and review.get("severity") == "Critical":
                logger.warning(f"[orchestrator] Critic rejected response. Attempting correction…")
                correction_prompt = (
                    f"The following response had critical issues: {review.get('issues_found')}\n\n"
                    f"Original response:\n{raw_response}\n\n"
                    f"Please provide a corrected version addressing the issues. "
                    f"Original user question: {user_message}"
                )
                agent = self._get_agent(agent_used) or self
                corrected = agent.run(correction_prompt, session_id=f"{session_id}_retry")
                review2 = critic.review(
                    agent_name=agent_used,
                    response=corrected,
                    original_prompt=user_message,
                    session_id=f"{session_id}_critic2",
                )
                final_response = review2["response"]
                critic_approved = review2.get("approved", True)
                critic_issues = review2.get("issues_found", [])
        else:
            final_response = raw_response
            critic_approved = True
            critic_issues = []

        elapsed = time.perf_counter() - start
        logger.info(f"[orchestrator] chat() completed in {elapsed:.2f}s. Agent: {agent_used}")

        return {
            "response": final_response,
            "agent_used": agent_used,
            "critic_approved": critic_approved,
            "critic_issues": critic_issues,
            "latency_s": round(elapsed, 3),
        }

    async def chat_stream(
        self, user_message: str, session_id: str = "default"
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Async streaming chat — yields token dicts for SSE.

        Yields:
            {"token": str, "agent": str, "done": bool}
        """
        intent = _detect_intent(user_message)
        agent = self._get_agent(intent) if intent != "general" else None
        agent_name = intent if agent else "orchestrator"
        active_agent = agent or self

        enriched = active_agent._enrich_prompt(user_message)

        runner, session_service = active_agent._make_runner()
        await session_service.create_session(
            app_name="careerpilot",
            user_id=str(self._user_id or "anon"),
            session_id=session_id,
        )

        from google.genai import types as genai_types
        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=enriched)],
        )

        full_text = ""
        async for event in runner.run_async(
            user_id=str(self._user_id or "anon"),
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        full_text += part.text
                        yield {"token": part.text, "agent": agent_name, "done": False}

        yield {"token": "", "agent": agent_name, "done": True, "full_response": full_text}
