"""
chat.py — Real-time chat and WebSocket interview endpoints.

Endpoints:
  POST /api/chat/stream          — SSE streaming conversational chat
  POST /api/chat                 — Synchronous single-turn chat
  WS   /ws/interview/{session}   — Stateful WebSocket mock interview
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from src.api.auth import get_current_user

router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_orchestrator(user: User, db: Session):
    """Lazy-initialise OrchestratorAgent per request."""
    try:
        from src.agents.orchestrator import OrchestratorAgent
        return OrchestratorAgent(db_session=db, user_id=user.id)
    except Exception as e:
        logger.error(f"[chat] Failed to initialise OrchestratorAgent: {e}")
        return None


# ---------------------------------------------------------------------------
# SSE Streaming Chat
# ---------------------------------------------------------------------------

async def _sse_generator(orchestrator, message: str, session_id: str) -> AsyncIterator[str]:
    """Yield SSE-formatted token events."""
    try:
        async for chunk in orchestrator.chat_stream(message, session_id=session_id):
            data = json.dumps(chunk)
            yield f"data: {data}\n\n"
    except Exception as e:
        logger.error(f"[sse] Streaming error: {e}")
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events streaming chat.

    Each event payload: {"token": str, "agent": str, "done": bool}
    """
    orchestrator = _get_orchestrator(current_user, db)
    if orchestrator is None:
        return StreamingResponse(
            iter([f"data: {json.dumps({'error': 'Orchestrator unavailable', 'done': True})}\n\n"]),
            media_type="text/event-stream",
        )
    return StreamingResponse(
        _sse_generator(orchestrator, payload.message, payload.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ---------------------------------------------------------------------------
# Synchronous Chat (for simpler clients / testing)
# ---------------------------------------------------------------------------

@router.post("/api/chat")
async def chat_sync(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Single-turn synchronous chat. Returns the full response in one payload."""
    orchestrator = _get_orchestrator(current_user, db)
    if orchestrator is None:
        return {"error": "Orchestrator unavailable", "response": None}

    try:
        result = orchestrator.chat(payload.message, session_id=payload.session_id)
        return result
    except Exception as e:
        logger.error(f"[chat_sync] Error: {e}")
        return {"error": str(e), "response": None}


# ---------------------------------------------------------------------------
# WebSocket Interview
# ---------------------------------------------------------------------------

@router.websocket("/ws/interview/{session_id}")
async def websocket_interview(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Stateful WebSocket mock interview session.

    Protocol:
      1. Client connects and sends: {"action": "start", "target_role": "...", "company": "..."}
      2. Server sends the first interview question as JSON.
      3. Client sends candidate answer: {"action": "answer", "text": "..."}
      4. Server evaluates and sends next question or session summary.
      5. Session ends when all questions complete or client disconnects.
    """
    await websocket.accept()
    logger.info(f"[ws/interview] Client connected: session={session_id}")

    interview_agent = None
    question_count = 0
    max_questions = 5

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "")

            if action == "start":
                target_role = msg.get("target_role", "Software Engineer")
                company = msg.get("company", "")

                # Lazy-load interview agent
                if interview_agent is None:
                    try:
                        from src.agents.interview_agent import InterviewAgent
                        interview_agent = InterviewAgent(db_session=db)
                    except Exception as e:
                        await websocket.send_json({"error": f"Could not start interview: {e}"})
                        continue

                # Generate first question
                prompt = (
                    f"Start a mock interview for the role: {target_role}."
                    + (f" Company: {company}." if company else "")
                    + " Generate the first question in the required JSON format."
                )
                response = interview_agent.run(prompt, session_id=session_id)
                question_count += 1
                await websocket.send_json({
                    "type": "question",
                    "question_num": question_count,
                    "data": response,
                })

            elif action == "answer":
                if interview_agent is None:
                    await websocket.send_json({"error": "Interview not started. Send action=start first."})
                    continue

                answer_text = msg.get("text", "")
                eval_prompt = (
                    f"The candidate answered: {answer_text}\n\n"
                    "Evaluate this answer using the required JSON format. "
                    f"If this was question {question_count} of {max_questions}, "
                    f"{'set next_question_id to null (session complete)' if question_count >= max_questions else 'generate the next question ID'}."
                )
                response = interview_agent.run(eval_prompt, session_id=session_id)
                question_count += 1

                payload = {"type": "evaluation", "data": response}
                if question_count > max_questions:
                    payload["type"] = "session_complete"
                await websocket.send_json(payload)

            elif action == "end":
                await websocket.send_json({"type": "goodbye", "message": "Interview session ended. Check your dashboard for results."})
                break

            else:
                await websocket.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info(f"[ws/interview] Client disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"[ws/interview] Error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
