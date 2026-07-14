"""Central configuration loader — reads config.yaml and exposes typed settings."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.yaml"


def _load_yaml() -> Dict[str, Any]:
    if not _CONFIG_PATH.exists():
        logger.warning(f"config.yaml not found at {_CONFIG_PATH}. Using defaults.")
        return {}
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


_CFG = _load_yaml()


def get_model(agent_key: str) -> str:
    """Return the configured model name for a given agent key, with a sensible default."""
    agent_cfg = _CFG.get("agent_settings", {}).get(agent_key, {})
    if "model" in agent_cfg:
        return agent_cfg["model"]
    # Fall back to default_subagent
    return _CFG.get("models", {}).get("default_subagent", {}).get("name", "gemini-2.5-flash")


def get_orchestrator_model() -> str:
    return _CFG.get("models", {}).get("orchestrator", {}).get("name", "gemini-2.5-pro")


def get_critic_model() -> str:
    return _CFG.get("models", {}).get("critic", {}).get("name", "gemini-2.5-pro")


def get_embedding_model() -> str:
    return _CFG.get("models", {}).get("embedding", {}).get("name", "text-embedding-004")


def get_rag_config() -> Dict[str, Any]:
    return _CFG.get("rag", {})


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", _CFG.get("database", {}).get("url", "sqlite:///data/careerpilot.db"))


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")
