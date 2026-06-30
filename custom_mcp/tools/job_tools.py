from typing import List, Dict, Any, Optional

MOCK_JOBS = [
    {
        "id": "job_001",
        "company": "Google",
        "title": "Senior Software Engineer, Core Infra",
        "location": "Sunnyvale, CA",
        "salary_range": "$180,000 - $240,000",
        "skills": ["Python", "Go", "C++", "System Design", "Docker", "Kubernetes", "gRPC"],
        "description": "Build high-performance, scalable distributed systems handling petabytes of data. Experience with containers and orchestration required."
    },
    {
        "id": "job_002",
        "company": "OpenAI",
        "title": "Machine Learning Engineer, Alignment",
        "location": "San Francisco, CA",
        "salary_range": "$220,000 - $310,000",
        "skills": ["Python", "PyTorch", "Transformers", "NLP", "TensorFlow", "Git"],
        "description": "Develop and align large language models. Fine-tuning experience, solid understanding of attention mechanisms and deep learning are essential."
    },
    {
        "id": "job_003",
        "company": "Stripe",
        "title": "Staff Backend Engineer, API Platforms",
        "location": "Remote",
        "salary_range": "$190,000 - $250,000",
        "skills": ["Ruby", "Go", "SQL", "REST API", "PostgreSQL", "System Design", "Microservices"],
        "description": "Scale Stripe's core financial API processing engines. Strong system design and REST design practices required."
    },
    {
        "id": "job_004",
        "company": "Meta",
        "title": "Product Engineer, Reels AI",
        "location": "New York, NY",
        "salary_range": "$170,000 - $220,000",
        "skills": ["JavaScript", "TypeScript", "React", "Python", "GraphQL", "HTML", "CSS"],
        "description": "Craft modern frontend interfaces and recommend algorithm pipelines for Reels. Strong React/TypeScript and product sense needed."
    },
    {
        "id": "job_005",
        "company": "DataBricks",
        "title": "Data Engineer, Solutions Architecture",
        "location": "Remote",
        "salary_range": "$150,000 - $200,000",
        "skills": ["Python", "SQL", "Spark", "Scala", "AWS", "GCP", "Kubernetes"],
        "description": "Build pipelines and scale data lakes for enterprise clients. Expertise in Spark, databases, and cloud infrastructures is key."
    }
]

def find_jobs(skills: List[str], target_role: Optional[str] = None, location: Optional[str] = "Remote") -> List[Dict[str, Any]]:
    """Filters mock jobs based on candidate skills, title matching, and location preferences."""
    matched_jobs = []
    
    # Normalize inputs
    skills_norm = [s.lower() for s in skills]
    role_norm = target_role.lower() if target_role else None
    loc_norm = location.lower() if location else None

    for job in MOCK_JOBS:
        # Calculate skill match percentage
        job_skills = [s.lower() for s in job["skills"]]
        matching_skills = [s for s in skills_norm if s in job_skills]
        
        # Calculate match percentage
        match_pct = 0.0
        if job_skills:
            match_pct = round((len(matching_skills) / len(job_skills)) * 100, 1)

        # Filters
        role_match = True
        if role_norm:
            role_match = (role_norm in job["title"].lower()) or (job["title"].lower() in role_norm)
            
        loc_match = True
        if loc_norm and loc_norm != "remote":
            loc_match = loc_norm in job["location"].lower() or "remote" in job["location"].lower()
        elif loc_norm == "remote":
            loc_match = "remote" in job["location"].lower()

        if role_match and loc_match:
            job_copy = job.copy()
            job_copy["match_percentage"] = match_pct
            job_copy["matched_skills"] = [s.title() for s in matching_skills]
            matched_jobs.append(job_copy)

    # Sort by match percentage descending
    matched_jobs.sort(key=lambda x: x["match_percentage"], reverse=True)
    return matched_jobs
