import re
from typing import Dict, Any, List
from rag.document_parser import DocumentParser
from loguru import logger

COMMON_SKILLS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "ruby", "php", "sql", "html", "css",
    "fastapi", "django", "flask", "express", "nest.js", "next.js", "react", "vue", "angular", "svelte",
    "tensorflow", "pytorch", "keras", "scikit-learn", "numpy", "pandas", "spacy", "nltk", "transformers",
    "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "git", "jenkins", "terraform", "ansible",
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "elasticsearch", "cassandra", "graphql",
    "agile", "scrum", "project management", "system design", "microservices", "rest api", "grpc", "websockets"
}

def extract_skills(text: str) -> List[str]:
    """Helper function to extract skills from text using pre-defined dictionary matching."""
    if not text:
        return []
    
    # Simple tokenization
    tokens = re.findall(r'\b[\w\.\-]+\b', text.lower())
    found_skills = set()
    
    # Check single word skills
    for token in tokens:
        if token in COMMON_SKILLS:
            found_skills.add(token)
            
    # Check multi-word skills (like "project management", "system design")
    normalized_text = text.lower()
    for skill in COMMON_SKILLS:
        if " " in skill and skill in normalized_text:
            found_skills.add(skill)
            
    # Capitalize appropriately for presentation
    presentation_mapping = {s: s.title() for s in found_skills}
    # Specific overrides
    override_caps = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript", "java": "Java",
        "c++": "C++", "c#": "C#", "go": "Go", "rust": "Rust", "sql": "SQL", "html": "HTML", "css": "CSS",
        "fastapi": "FastAPI", "django": "Django", "flask": "Flask", "next.js": "Next.js", "nest.js": "Nest.js",
        "react": "React", "vue": "Vue", "angular": "Angular", "svelte": "Svelte", "aws": "AWS", "gcp": "GCP",
        "azure": "Azure", "ci/cd": "CI/CD", "git": "Git", "rest api": "REST API", "grpc": "gRPC", "websockets": "WebSockets",
        "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB", "sqlite": "SQLite", "pytorch": "PyTorch"
    }
    
    return [override_caps.get(s, presentation_mapping[s]) for s in found_skills]


def parse_resume_content(file_path: str) -> Dict[str, Any]:
    """Extracts raw text and structures key attributes from a resume file."""
    try:
        raw_text = DocumentParser.parse_file(file_path)
    except Exception as e:
        logger.error(f"Failed to load resume file: {e}")
        raise ValueError(f"Could not read resume file: {e}")

    # Extract email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
    email = email_match.group(0) if email_match else None

    # Extract phone
    phone_match = re.search(r'\(?\b[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b', raw_text)
    phone = phone_match.group(0) if phone_match else None

    # Extract skills
    skills = extract_skills(raw_text)

    # Basic segment splitting (Experience, Education, Projects)
    sections = {"experience": [], "education": [], "projects": []}
    lines = raw_text.split("\n")
    current_section = None
    
    for line in lines:
        cleaned = line.strip().lower()
        if any(h in cleaned for h in ["experience", "work history", "employment"]):
            current_section = "experience"
            continue
        elif any(h in cleaned for h in ["education", "academic"]):
            current_section = "education"
            continue
        elif any(h in cleaned for h in ["projects", "personal work", "key projects"]):
            current_section = "projects"
            continue
            
        if current_section and line.strip():
            sections[current_section].append(line.strip())

    return {
        "status": "success",
        "email": email,
        "phone": phone,
        "skills": skills,
        "experience": sections["experience"][:15],
        "education": sections["education"][:5],
        "projects": sections["projects"][:10],
        "raw_content": raw_text
    }


def calculate_ats_metrics(resume_content: str, job_description: str) -> Dict[str, Any]:
    """Matches resume text against a job description, computing scoring indicators."""
    if not resume_content or not job_description:
        return {
            "overall_score": 0.0,
            "matching_keywords": [],
            "missing_keywords": [],
            "readability_score": 0.0,
            "suggestions": ["Both resume and job description content must be provided."]
        }
        
    resume_skills = set(s.lower() for s in extract_skills(resume_content))
    job_skills = set(s.lower() for s in extract_skills(job_description))
    
    matching_skills = resume_skills.intersection(job_skills)
    missing_skills = job_skills.difference(resume_skills)
    
    # Calculate matching score based on skill overlap
    if job_skills:
        skill_score = (len(matching_skills) / len(job_skills)) * 100
    else:
        skill_score = 50.0
        
    # Calculate simple word overlap score
    def get_words(text):
        return re.findall(r'\b[a-zA-Z]{3,15}\b', text.lower())
        
    res_words = set(get_words(resume_content))
    job_words = set(get_words(job_description))
    
    word_overlap = res_words.intersection(job_words)
    if job_words:
        keyword_score = (len(word_overlap) / len(job_words)) * 100
    else:
        keyword_score = 50.0
        
    overall_score = round((skill_score * 0.7) + (keyword_score * 0.3), 1)
    overall_score = max(0.0, min(100.0, overall_score))
    
    sentences = re.split(r'[.!?]+', resume_content)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = get_words(resume_content)
    
    avg_sentence_len = len(words) / len(sentences) if sentences else 15
    readability = max(10, min(100, round(100 - (avg_sentence_len * 1.5), 1)))

    suggestions = []
    if missing_skills:
        suggestions.append(f"Add missing target skills: {', '.join(s.title() for s in list(missing_skills)[:5])}.")
    if len(words) < 200:
        suggestions.append("Your resume seems brief. Expand experience bullet points with quantitative results.")
    elif len(words) > 1000:
        suggestions.append("Your resume is very long. Condense formatting to focus on key contributions.")
    if readability < 40:
        suggestions.append("Simplify sentence structures to improve ATS parsing readability.")

    return {
        "overall_score": overall_score,
        "matching_keywords": [s.title() for s in matching_skills],
        "missing_keywords": [s.title() for s in missing_skills],
        "readability_score": readability,
        "suggestions": suggestions
    }
