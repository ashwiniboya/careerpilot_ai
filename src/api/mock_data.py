"""
mock_data.py — Fallback data used by the dashboard API when no real data exists.

Provides realistic-looking seed data so the frontend looks populated
on first run, before any real user interactions have taken place.
"""
from __future__ import annotations

from typing import Any, Dict, List


MOCK_ATS_HISTORY: List[Dict[str, Any]] = [
    {"date": "2026-06-01", "score": 54.2, "job_title": "Backend Engineer"},
    {"date": "2026-06-08", "score": 67.5, "job_title": "Senior Python Dev"},
    {"date": "2026-06-15", "score": 73.0, "job_title": "ML Engineer"},
    {"date": "2026-06-22", "score": 81.3, "job_title": "Staff Engineer"},
]

MOCK_INTERVIEW_SCORES: List[Dict[str, Any]] = [
    {"date": "2026-06-05", "score": 3.1, "role": "Backend Engineer", "company": "StartupX"},
    {"date": "2026-06-12", "score": 3.6, "role": "Senior Dev", "company": "TechCorp"},
    {"date": "2026-06-19", "score": 4.0, "role": "ML Engineer", "company": "AI Labs"},
    {"date": "2026-06-25", "score": 4.4, "role": "Staff Engineer", "company": "BigTech"},
]

MOCK_SKILLS: List[Dict[str, Any]] = [
    {"skill": "Python", "category": "Technical", "current": 4, "target": 5},
    {"skill": "System Design", "category": "Domain", "current": 2, "target": 4},
    {"skill": "Docker", "category": "DevOps", "current": 3, "target": 4},
    {"skill": "Machine Learning", "category": "Technical", "current": 3, "target": 5},
    {"skill": "SQL", "category": "Database", "current": 4, "target": 4},
    {"skill": "Communication", "category": "Soft Skill", "current": 3, "target": 5},
]

MOCK_ROADMAP: List[Dict[str, Any]] = [
    {
        "step_num": 1,
        "title": "Foundation Review",
        "description": "Reinforce core Python, data structures, and algorithms.",
        "status": "completed",
        "resources": ["LeetCode", "Python Docs"],
    },
    {
        "step_num": 2,
        "title": "System Design Fundamentals",
        "description": "Study distributed systems, CAP theorem, and database design.",
        "status": "active",
        "resources": ["Designing Data-Intensive Applications", "System Design Primer"],
    },
    {
        "step_num": 3,
        "title": "Machine Learning Essentials",
        "description": "Cover supervised learning, model evaluation, and PyTorch basics.",
        "status": "pending",
        "resources": ["fast.ai", "Hands-On ML with Scikit-Learn"],
    },
    {
        "step_num": 4,
        "title": "Portfolio Projects",
        "description": "Build two end-to-end projects to demonstrate skills.",
        "status": "pending",
        "resources": ["GitHub", "Kaggle"],
    },
]

MOCK_JOB_APPLICATIONS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "company_name": "OpenAI",
        "job_title": "ML Engineer",
        "status": "Applied",
        "applied_at": "2026-06-20",
        "url": "https://openai.com/careers",
    },
    {
        "id": 2,
        "company_name": "Anthropic",
        "job_title": "Research Engineer",
        "status": "Interview",
        "applied_at": "2026-06-15",
        "url": "https://anthropic.com/careers",
    },
    {
        "id": 3,
        "company_name": "DeepMind",
        "job_title": "Software Engineer",
        "status": "Rejected",
        "applied_at": "2026-06-10",
        "url": "https://deepmind.google/careers",
    },
]

MOCK_METRICS_SUMMARY: Dict[str, Any] = {
    "latest_ats_score": 81.3,
    "ats_score_trend": "+27.1 since June",
    "interview_avg_score": 3.8,
    "interview_sessions_completed": 4,
    "roadmap_progress_percent": 25,
    "roadmap_total_steps": 4,
    "roadmap_completed_steps": 1,
    "active_applications": 2,
    "total_applications": 3,
    "skills_at_target": 1,
    "total_skills_tracked": 6,
}
