from typing import List, Dict, Any

MOCK_COURSES = {
    "python": [
        {"title": "Complete Python BootCamp", "platform": "Udemy", "duration": "22 hours", "rating": 4.7},
        {"title": "Python for Everybody Specialization", "platform": "Coursera / Michigan", "duration": "3 months", "rating": 4.8}
    ],
    "fastapi": [
        {"title": "FastAPI: The Complete Course", "platform": "Udemy", "duration": "10 hours", "rating": 4.6},
        {"title": "Build APIs with FastAPI", "platform": "TestDriven.io", "duration": "15 hours", "rating": 4.9}
    ],
    "docker": [
        {"title": "Docker Mastery: The Complete Toolset", "platform": "Udemy", "duration": "21 hours", "rating": 4.8},
        {"title": "Getting Started with Containers", "platform": "Pluralsight", "duration": "6 hours", "rating": 4.5}
    ],
    "kubernetes": [
        {"title": "Certified Kubernetes Administrator (CKA)", "platform": "Mumshad Mannambeth / KodeKloud", "duration": "32 hours", "rating": 4.9},
        {"title": "Kubernetes: Up and Running", "platform": "O'Reilly Book", "duration": "N/A", "rating": 4.7}
    ],
    "pytorch": [
        {"title": "Deep Learning with PyTorch", "platform": "Udacity", "duration": "6 weeks", "rating": 4.7},
        {"title": "PyTorch for Deep Learning BootCamp", "platform": "ZeroToMastery", "duration": "25 hours", "rating": 4.8}
    ],
    "system design": [
        {"title": "Grokking the System Design Interview", "platform": "DesignGurus.io", "duration": "Self-paced", "rating": 4.9},
        {"title": "System Design Interview by Alex Xu", "platform": "Book / ByteByteGo", "duration": "N/A", "rating": 4.9}
    ]
}

def recommend_courses(skills: List[str]) -> List[Dict[str, Any]]:
    """Suggests learning resources, books, and courses based on a list of targeted skills."""
    recommendations = []
    
    for skill in skills:
        key = skill.lower().strip()
        matched_key = None
        for course_key in MOCK_COURSES:
            if course_key in key or key in course_key:
                matched_key = course_key
                break
                
        if matched_key:
            for course in MOCK_COURSES[matched_key]:
                recommendations.append({
                    "skill": skill,
                    **course
                })
                
    if not recommendations:
        for skill in skills[:3]:
            recommendations.append({
                "skill": skill,
                "title": f"Mastering {skill}: Core Concepts & Real-World Projects",
                "platform": "Coursera / LinkedIn Learning",
                "duration": "12 hours",
                "rating": 4.6
            })
            
    return recommendations


def generate_roadmap_structure(current_skills: List[str], target_role: str) -> List[Dict[str, Any]]:
    """Creates a step-by-step career development learning path skeleton based on skills gaps."""
    role_skills = {
        "machine learning engineer": ["Python", "PyTorch", "TensorFlow", "scikit-learn", "Docker", "System Design"],
        "data scientist": ["Python", "scikit-learn", "SQL", "Pandas", "Math & Stats", "Data Visualization"],
        "backend engineer": ["Python", "Go", "FastAPI", "SQL", "PostgreSQL", "Docker", "System Design", "Microservices"],
        "frontend engineer": ["JavaScript", "TypeScript", "React", "HTML", "CSS", "Next.js", "Redux"]
    }
    
    role_key = target_role.lower().strip()
    target_skills = []
    
    for r, skills in role_skills.items():
        if r in role_key or role_key in r:
            target_skills = skills
            break
            
    if not target_skills:
        target_skills = ["System Design", "Docker", "Python", "REST API", "SQL"]

    current_lower = [s.lower() for s in current_skills]
    missing_skills = [s for s in target_skills if s.lower() not in current_lower]
    
    steps = []
    step_num = 1
    
    steps.append({
        "step_num": step_num,
        "title": f"Foundation Review: {target_role.title()}",
        "description": f"Benchmark current proficiency and align project scope. Current skills identified: {', '.join(current_skills) if current_skills else 'None'}.",
        "recommended_resources": [
            {"title": "Role Overview & Skill Assessment", "platform": "CareerPilot AI", "url": "/dashboard"}
        ]
    })
    step_num += 1

    for skill in missing_skills:
        courses = recommend_courses([skill])
        steps.append({
            "step_num": step_num,
            "title": f"Learn {skill}",
            "description": f"Master core frameworks, libraries, and best practices relating to {skill}.",
            "recommended_resources": courses[:2]
        })
        step_num += 1

    steps.append({
        "step_num": step_num,
        "title": "Capstone Project & Portfolio Build",
        "description": "Develop a comprehensive, production-grade project integrating all newly acquired skills. Deploy and write a technical blog post.",
        "recommended_resources": [
            {"title": "Open Source Project Templates", "platform": "GitHub", "url": "https://github.com"}
        ]
    })
    step_num += 1
    
    steps.append({
        "step_num": step_num,
        "title": "Resume Optimization & Job Application",
        "description": "Tailor resume using ATS Optimizer tool, draft target cover letters, and begin active cold outreach.",
        "recommended_resources": [
            {"title": "ATS Scoring Tool", "platform": "CareerPilot AI", "url": "/resume"}
        ]
    })

    return steps
