"""
Embedder — wraps the Gemini text-embedding-004 API.

Provides a single `embed(texts)` function that returns a list of
float vectors. Falls back gracefully if the API key is missing
(returns zero-vectors of the expected dimension so downstream code
can still run in tests without hitting the network).
"""
from __future__ import annotations

import os
from typing import List

from loguru import logger

# Gemini embedding dimension for text-embedding-004
_EMBEDDING_DIM = 768
_DEFAULT_MODEL = "text-embedding-004"


def embed(texts: List[str], model: str = _EMBEDDING_DIM) -> List[List[float]]:
    """
    Embed a batch of texts using the Gemini embedding API.

    Args:
        texts: List of strings to embed.
        model: Embedding model name (default: text-embedding-004).

    Returns:
        List of embedding vectors (one per input text).
        Falls back to zero-vectors if API key is unavailable.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("[Embedder] GEMINI_API_KEY not set — returning zero-vectors.")
        return [[0.0] * _EMBEDDING_DIM for _ in texts]

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model=_DEFAULT_MODEL,
            content=texts,
            task_type="retrieval_document",
        )
        embeddings = result["embedding"]
        # embed_content returns a single vector for single input; normalise to list of lists
        if embeddings and not isinstance(embeddings[0], list):
            embeddings = [embeddings]
        logger.debug(f"[Embedder] Embedded {len(texts)} texts → dim={len(embeddings[0])}")
        return embeddings
    except Exception as e:
        logger.error(f"[Embedder] Embedding failed: {e}. Returning zero-vectors.")
        return [[0.0] * _EMBEDDING_DIM for _ in texts]


def embed_single(text: str) -> List[float]:
    """Convenience wrapper to embed a single text string."""
    return embed([text])[0]
