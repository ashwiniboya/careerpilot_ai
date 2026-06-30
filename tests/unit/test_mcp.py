import pytest
import os
from custom_mcp.tools.resume_tools import parse_resume_content, calculate_ats_metrics, extract_skills
from custom_mcp.tools.job_tools import find_jobs
from custom_mcp.tools.search_tools import get_company_profile
from custom_mcp.tools.tracking_tools import recommend_courses, generate_roadmap_structure

def test_extract_skills():
    text = "Experienced Senior Software Engineer. Proficient in Python, FastAPI, Docker, and Kubernetes. Some experience in PyTorch and React."
    skills = extract_skills(text)
    
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "Kubernetes" in skills
    assert "React" in skills
    assert "PyTorch" in skills
    assert "Java" not in skills


def test_resume_parser_mock_file(tmp_path):
    resume_file = tmp_path / "jane_resume.md"
    content = """# Jane Developer
Email: jane.dev@example.com
Phone: 123-456-7890

## Professional Experience
Software Engineer at Google (2022 - Present)
- Developed APIs in Python and FastAPI.
- Configured PostgreSQL database models.

## Education
B.S. in Computer Science from MIT (2018-2022)
"""
    resume_file.write_text(content, encoding="utf-8")

    parsed = parse_resume_content(str(resume_file))
    
    assert parsed["status"] == "success"
    assert parsed["email"] == "jane.dev@example.com"
    assert parsed["phone"] == "123-456-7890"
    assert "Python" in parsed["skills"]
    assert "FastAPI" in parsed["skills"]
    assert "PostgreSQL" in parsed["skills"]


def test_calculate_ats_metrics():
    resume = "John is an experienced Backend Developer skilled in Python, SQL, Docker, and System Design."
    job_desc = "Looking for a Software Engineer skilled in Python, Docker, Kubernetes, and REST API."
    
    metrics = calculate_ats_metrics(resume, job_desc)
    
    assert metrics["overall_score"] > 0.0
    assert "Python" in metrics["matching_keywords"]
    assert "Docker" in metrics["matching_keywords"]
    assert "Kubernetes" in metrics["missing_keywords"]
    assert len(metrics["suggestions"]) > 0


def test_job_matcher():
    skills = ["Python", "PyTorch", "Transformers", "Git"]
    jobs = find_jobs(skills, target_role="Machine Learning Engineer", location="San Francisco")
    
    assert len(jobs) >= 1
    assert jobs[0]["company"] == "OpenAI"
    assert "Python" in jobs[0]["matched_skills"]
    assert jobs[0]["match_percentage"] > 0.0


def test_company_insights():
    insights = get_company_profile("Google")
    
    assert insights["status"] == "success"
    assert insights["name"] == "Google LLC"
    assert "TensorFlow" in insights["tech_stack"]
    
    fallback = get_company_profile("Acme Corp")
    assert fallback["name"] == "Acme Corp"
    assert "Python" in fallback["tech_stack"]


def test_course_recommendations():
    skills = ["Python", "Docker"]
    recommendations = recommend_courses(skills)
    
    assert len(recommendations) >= 2
    skills_covered = {r["skill"] for r in recommendations}
    assert "Python" in skills_covered
    assert "Docker" in skills_covered


def test_generate_roadmap():
    skills = ["Python", "SQL"]
    steps = generate_roadmap_structure(skills, "Backend Engineer")
    
    assert len(steps) >= 3
    # Step 1 should be Foundation
    assert "Foundation Review" in steps[0]["title"]
    # Should include learning steps for missing skills like FastAPI or System Design
    titles = [s["title"] for s in steps]
    assert any("Learn FastAPI" in t or "Learn System Design" in t for t in titles)
