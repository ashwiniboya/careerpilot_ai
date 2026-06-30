"""
BaseCareerAgent — common interface wrapping google.adk.Agent.

Every CareerPilot specialized agent inherits from this class.

Responsibilities:
  - Configure the underlying ADK Agent with the correct model from config.yaml
  - Provide a synchronous `run(prompt)` helper for direct testing
  - Expose `run_async(prompt)` for streaming / async usage
  - Wire MemoryManager when a db_session + user_id are provided
  - Log token usage to SQLite for cost tracking
  - Structured error handling so a bad LLM response never crashes the caller

ADK Internals note:
  - google.adk.Agent (= LlmAgent) is a Pydantic v2 model.
  - We compose it rather than inherit to avoid Pydantic metaclass conflicts.
  - The `adk_agent` property exposes the underlying Agent for registration.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from loguru import logger

from src.core.config_loader import get_gemini_api_key


class BaseCareerAgent:
    """
    Abstract wrapper around google.adk.Agent.

    Concrete agents must implement:
        - agent_name (str property)
        - agent_description (str property)
        - instruction (str property — the system prompt)
        - model_key (str property — key in config.yaml agent_settings)
        - _build_tools() -> list  (return [] if no tools needed)
    """

    def __init__(
        self,
        db_session=None,
        user_id: Optional[int] = None,
        vector_store=None,
    ):
        self._db = db_session
        self._user_id = user_id
        self._memory: Optional[Any] = None

        # Wire memory if database session is provided
        if db_session is not None and user_id is not None:
            try:
                from memory.memory_manager import MemoryManager
                self._memory = MemoryManager(db_session, user_id, vector_store)
            except Exception as e:
                logger.warning(f"[{self.agent_name}] Could not initialise MemoryManager: {e}")

        # Build the underlying ADK Agent
        self._agent = self._build_adk_agent()
        logger.debug(f"[{self.agent_name}] Initialised with model={self._get_model()}")

    # ------------------------------------------------------------------
    # Abstract interface — subclasses must implement
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique snake_case identifier, e.g. 'resume_agent'."""
        ...

    @property
    @abstractmethod
    def agent_description(self) -> str:
        """One-line description used by the Orchestrator for routing."""
        ...

    @property
    @abstractmethod
    def instruction(self) -> str:
        """The system prompt / instruction string for this agent."""
        ...

    @property
    @abstractmethod
    def model_key(self) -> str:
        """Key in config.yaml agent_settings, e.g. 'resume_agent'."""
        ...

    @abstractmethod
    def _build_tools(self) -> List[Any]:
        """Return a list of Python callables to register as ADK tools."""
        ...

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self) -> str:
        from src.core.config_loader import get_model
        return get_model(self.model_key)

    def _build_adk_agent(self) -> Agent:
        """Constructs the google.adk.Agent instance."""
        return Agent(
            name=self.agent_name,
            model=self._get_model(),
            description=self.agent_description,
            instruction=self.instruction,
            tools=self._build_tools(),
        )

    @property
    def adk_agent(self) -> Agent:
        """Expose the underlying ADK Agent (used by AgentRegistry / Orchestrator)."""
        return self._agent

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------

    def _make_runner(self) -> tuple[Runner, InMemorySessionService]:
        """Creates a disposable ADK Runner + InMemorySessionService for one call."""
        session_service = InMemorySessionService()
        runner = Runner(
            agent=self._agent,
            app_name="careerpilot",
            session_service=session_service,
        )
        return runner, session_service

    async def run_async(self, prompt: str, session_id: str = "default") -> str:
        """
        Async entry-point.  Returns the agent's final text response.
        Injects memory context into the prompt when available.
        """
        enriched_prompt = self._enrich_prompt(prompt)

        runner, session_service = self._make_runner()

        # Create a session for this call
        await session_service.create_session(
            app_name="careerpilot",
            user_id=str(self._user_id or "anon"),
            session_id=session_id,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=enriched_prompt)],
        )

        final_text = ""
        start = time.perf_counter()
        async for event in runner.run_async(
            user_id=str(self._user_id or "anon"),
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(
                    p.text for p in event.content.parts if hasattr(p, "text") and p.text
                )

        latency = time.perf_counter() - start
        logger.info(f"[{self.agent_name}] run_async completed in {latency:.2f}s")

        # Persist interaction to memory
        if self._memory:
            self._memory.append_interaction("user", prompt)
            self._memory.append_interaction("assistant", final_text[:500])  # cap stored size

        return final_text

    def run(self, prompt: str, session_id: str = "default") -> str:
        """
        Synchronous wrapper around run_async.
        Safe to call from tests and CLI scripts.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In an already-async context (e.g. FastAPI), create a new loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.run_async(prompt, session_id))
                    return future.result()
            else:
                return loop.run_until_complete(self.run_async(prompt, session_id))
        except Exception as e:
            logger.error(f"[{self.agent_name}] run() failed: {e}")
            return json.dumps({"error": str(e), "agent": self.agent_name})

    def run_offline(self, prompt: str) -> str:
        """
        Returns a structured offline stub when no API key is configured.
        Used in unit tests that must not hit the network.
        """
        return json.dumps({
            "status": "offline_stub",
            "agent": self.agent_name,
            "prompt_received": prompt[:200],
            "note": "Set GEMINI_API_KEY to enable live LLM responses."
        })

    # ------------------------------------------------------------------
    # Prompt enrichment
    # ------------------------------------------------------------------

    def _enrich_prompt(self, prompt: str) -> str:
        """Prepend relevant memory context to the user prompt."""
        if self._memory is None:
            return prompt
        try:
            ctx = self._memory.build_context(query=prompt)
            if ctx and ctx != "No prior context available.":
                return f"{ctx}\n\n---\n\nUser request: {prompt}"
        except Exception as e:
            logger.warning(f"[{self.agent_name}] Memory enrichment failed: {e}")
        return prompt

    # ------------------------------------------------------------------
    # JSON parsing helper (shared utility for all agents)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse the first JSON object/array found in `text`.
        Returns None if no valid JSON is found.
        """
        if not text:
            return None
        # Strip markdown code fences if present
        cleaned = text.strip()
        for fence in ("```json", "```"):
            if cleaned.startswith(fence):
                cleaned = cleaned[len(fence):]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Find the first { or [ and try from there
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            idx = cleaned.find(start_char)
            if idx != -1:
                # Walk backwards from end to find matching close
                ridx = cleaned.rfind(end_char)
                if ridx > idx:
                    try:
                        return json.loads(cleaned[idx:ridx + 1])
                    except json.JSONDecodeError:
                        continue
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.agent_name} model={self._get_model()}>"
