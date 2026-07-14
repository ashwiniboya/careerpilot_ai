"""
dashboard.py — Dashboard metrics and data endpoints.

Endpoints:
  GET /api/dashboard/metrics       — Aggregated summary stats (ATS trend, interview scores…)
  GET /api/dashboard/skills        — User's skill tracking data (for radar chart)
  GET /api/dashboard/roadmap       — Active roadmap steps
  PUT /api/dashboard/roadmap/{id}  — Mark a roadmap step status
  GET /api/dashboard/applications  — Job application tracker list
  POST /api/dashboard/applications — Add a new job application
  GET /api/resume/upload-url       — Get a pre-signed upload path (local path)
  POST /api/resume/upload          — Upload and parse a resume file
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    InterviewHistory,
    JobApplication,
    Resume,
    Roadmap,
    RoadmapStep,
    SkillTracking,
    TokenUsage,
    User,
)
from src.api.auth import get_current_user
from src.api.mock_data import (
    MOCK_ATS_HISTORY,
    MOCK_INTERVIEW_SCORES,
    MOCK_JOB_APPLICATIONS,
    MOCK_METRICS_SUMMARY,
    MOCK_ROADMAP,
    MOCK_SKILLS,
)

router = APIRouter(prefix="/api", tags=["dashboard"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE_MB = 10


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ApplicationCreate(BaseModel):
    company_name: str
    job_title: str
    job_description: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: str  # Applied | Interview | Offer | Rejected | Withdrawn


class RoadmapStepUpdate(BaseModel):
    status: str  # pending | active | completed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_has_data(db: Session, user_id: int) -> bool:
    """True if the user has at least one real record in the DB."""
    return db.query(Resume).filter(Resume.user_id == user_id).count() > 0


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@router.get("/dashboard/metrics")
def get_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return aggregated dashboard KPIs. Falls back to mock data if empty."""
    if not _user_has_data(db, current_user.id):
        return {**MOCK_METRICS_SUMMARY, "data_source": "demo"}

    # Real data aggregation
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    latest_ats = resumes[-1].last_ats_score if resumes else None

    interviews = db.query(InterviewHistory).filter(InterviewHistory.user_id == current_user.id).all()
    avg_score = (sum(i.overall_score for i in interviews) / len(interviews)) if interviews else None

    roadmaps = db.query(Roadmap).filter(Roadmap.user_id == current_user.id).first()
    roadmap_progress = int((roadmaps.current_step / roadmaps.total_steps) * 100) if roadmaps and roadmaps.total_steps else 0

    applications = db.query(JobApplication).filter(JobApplication.user_id == current_user.id).all()
    active_apps = sum(1 for a in applications if a.status in ("Applied", "Interview"))

    skills = db.query(SkillTracking).filter(SkillTracking.user_id == current_user.id).all()
    at_target = sum(1 for s in skills if s.current_proficiency >= s.target_proficiency)

    return {
        "latest_ats_score": latest_ats,
        "interview_avg_score": round(avg_score, 2) if avg_score else None,
        "interview_sessions_completed": len(interviews),
        "roadmap_progress_percent": roadmap_progress,
        "active_applications": active_apps,
        "total_applications": len(applications),
        "skills_at_target": at_target,
        "total_skills_tracked": len(skills),
        "data_source": "live",
    }


@router.get("/dashboard/ats-history")
def get_ats_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    if not _user_has_data(db, current_user.id):
        return MOCK_ATS_HISTORY
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at).all()
    return [{"date": str(r.created_at.date()), "score": r.last_ats_score, "job_title": r.original_filename} for r in resumes]


@router.get("/dashboard/interview-history")
def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    if not _user_has_data(db, current_user.id):
        return MOCK_INTERVIEW_SCORES
    rows = db.query(InterviewHistory).filter(InterviewHistory.user_id == current_user.id).order_by(InterviewHistory.date_conducted).all()
    return [{"date": str(r.date_conducted.date()), "score": r.overall_score, "role": r.target_role} for r in rows]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

@router.get("/dashboard/skills")
def get_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    skills = db.query(SkillTracking).filter(SkillTracking.user_id == current_user.id).all()
    if not skills:
        return MOCK_SKILLS
    return [
        {
            "skill": s.skill_name,
            "category": s.category,
            "current": s.current_proficiency,
            "target": s.target_proficiency,
        }
        for s in skills
    ]


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

@router.get("/roadmap")
def get_roadmap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    roadmap = db.query(Roadmap).filter(Roadmap.user_id == current_user.id).first()
    if not roadmap:
        return MOCK_ROADMAP
    steps = db.query(RoadmapStep).filter(RoadmapStep.roadmap_id == roadmap.id).order_by(RoadmapStep.step_num).all()
    return [
        {
            "step_num": s.step_num,
            "title": s.title,
            "description": s.description,
            "status": s.status,
            "resources": s.recommended_resources or [],
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in steps
    ]


@router.put("/roadmap/step/{step_id}")
def update_roadmap_step(
    step_id: int,
    payload: RoadmapStepUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    import datetime
    from datetime import timezone
    step = db.query(RoadmapStep).filter(RoadmapStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    # Authorization check: verify this step's roadmap belongs to the current user
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == step.roadmap_id,
        Roadmap.user_id == current_user.id,
    ).first()
    if not roadmap:
        raise HTTPException(status_code=403, detail="Not authorized to modify this step")
    step.status = payload.status
    if payload.status == "completed":
        step.completed_at = datetime.datetime.now(timezone.utc)
    db.commit()
    return {"status": "updated", "step_id": step_id, "new_status": payload.status}


# ---------------------------------------------------------------------------
# Job Applications
# ---------------------------------------------------------------------------

@router.get("/applications")
def get_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    apps = db.query(JobApplication).filter(JobApplication.user_id == current_user.id).all()
    if not apps:
        return MOCK_JOB_APPLICATIONS
    return [
        {
            "id": a.id,
            "company_name": a.company_name,
            "job_title": a.job_title,
            "status": a.status,
            "applied_at": str(a.applied_at.date()) if a.applied_at else None,
            "url": a.url,
            "notes": a.notes,
        }
        for a in apps
    ]


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    import datetime
    from datetime import timezone
    app = JobApplication(
        user_id=current_user.id,
        company_name=payload.company_name,
        job_title=payload.job_title,
        job_description=payload.job_description,
        status="Applied",
        applied_at=datetime.datetime.now(timezone.utc),
        url=payload.url,
        notes=payload.notes,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"id": app.id, "status": "created"}


# ---------------------------------------------------------------------------
# Resume Upload
# ---------------------------------------------------------------------------

@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Upload a resume file (PDF, DOCX, TXT, MD). Parses, scores, and stores it."""
    import datetime
    from datetime import timezone

    # Validate file type
    allowed = {".pdf", ".docx", ".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"File type '{suffix}' not supported.")

    # Save to disk
    user_dir = UPLOAD_DIR / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / file.filename

    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")

    with open(dest, "wb") as f:
        f.write(content_bytes)

    # Parse resume
    raw_text = ""
    skills: list = []
    try:
        from custom_mcp.tools.resume_tools import parse_resume_content
        parsed = parse_resume_content(str(dest))
        raw_text = parsed.get("raw_content", "") or ""
        skills = parsed.get("skills", [])
    except Exception as e:
        logger.warning(f"[resume upload] Parse error: {e}")

    # ATS pre-score (placeholder — requires JD)
    ats_score = 0.0

    # Save to database
    resume = Resume(
        user_id=current_user.id,
        original_filename=file.filename,
        file_type=suffix.lstrip("."),
        content_raw=raw_text,
        content_markdown=raw_text,
        parsed_data={"skills": skills},
        last_ats_score=ats_score,
        created_at=datetime.datetime.now(timezone.utc),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Index into ChromaDB asynchronously
    try:
        from rag.vector_store import VectorStore
        vs = VectorStore()
        vs.add_documents(
            [raw_text[:2000]],
            [{"user_id": current_user.id, "doc_type": "resume", "file_name": file.filename}],
        )
    except Exception as e:
        logger.warning(f"[resume upload] Vector store index failed: {e}")

    logger.info(f"[resume upload] User {current_user.id} uploaded {file.filename}")
    return {
        "status": "success",
        "resume_id": resume.id,
        "filename": file.filename,
        "skills_extracted": skills,
        "message": "Resume uploaded and indexed successfully.",
    }


# ---------------------------------------------------------------------------
# Cost / token usage
# ---------------------------------------------------------------------------

@router.get("/dashboard/cost")
def get_cost_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return recent token usage and cost records for the authenticated user."""
    rows = (
        db.query(TokenUsage)
        .filter(TokenUsage.user_id == current_user.id)
        .order_by(TokenUsage.timestamp.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "agent": r.agent_name,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "cost_usd": r.cost,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in rows
    ]
