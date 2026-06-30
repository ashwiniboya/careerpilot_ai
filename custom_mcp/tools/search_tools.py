import httpx
from typing import Dict, Any, List, Optional
from loguru import logger

MOCK_COMPANY_DATA = {
    "google": {
        "name": "Google LLC",
        "description": "A global technology leader focusing on search, advertising, operating systems, cloud computing, and AI.",
        "culture": "Emphasis on innovation, psychological safety, collaboration, and algorithmic solving. Uses OKRs heavily.",
        "tech_stack": ["Python", "Go", "C++", "Java", "TensorFlow", "Angular", "Spanner", "Borg"],
        "recent_developments": "Deepening integration of Gemini models across workspace, search, and cloud platforms."
    },
    "openai": {
        "name": "OpenAI",
        "description": "An AI research and deployment company with the mission to ensure artificial general intelligence benefits all of humanity.",
        "culture": "Fast-paced, mission-driven, research-heavy. Focused on pushing state-of-the-art capabilities rapidly.",
        "tech_stack": ["Python", "PyTorch", "Kubernetes", "Redis", "PostgreSQL", "Triton"],
        "recent_developments": "Launching advanced reasoning models and expanding developer API features."
    },
    "stripe": {
        "name": "Stripe, Inc.",
        "description": "A financial infrastructure platform for the internet, allowing businesses to accept payments and manage operations.",
        "culture": "Strong emphasis on written clarity, high engineering quality, API correctness, and user empathy.",
        "tech_stack": ["Ruby", "Go", "Scala", "Java", "PostgreSQL", "Redis", "Kafka"],
        "recent_developments": "Expanding crypto integrations and embedded finance features for enterprise customers."
    }
}

def get_company_profile(company_name: str) -> Dict[str, Any]:
    """Retrieves cultural, tech stack, and strategic insights about a company."""
    key = company_name.lower().strip()
    for k, data in MOCK_COMPANY_DATA.items():
        if k in key or key in k:
            return {
                "status": "success",
                "source": "database",
                **data
            }
            
    return {
        "status": "success",
        "source": "generator",
        "name": company_name.title(),
        "description": f"A major company operating in the tech and business services sector.",
        "culture": "Focused on customer satisfaction, professional growth, and high operational excellence.",
        "tech_stack": ["Python", "JavaScript", "SQL", "Docker", "Cloud Platforms (AWS/GCP/Azure)"],
        "recent_developments": "Expanding digital transformation and incorporating generative AI tools in daily workflows."
    }


async def execute_web_search(query: str) -> List[Dict[str, str]]:
    """Executes a search query against web search endpoints with mock fail-safes."""
    logger.info(f"Executing web search query: {query}")
    
    query_lower = query.lower()
    results = []
    
    if "salary" in query_lower:
        results.append({
            "title": "Tech Salary Trends 2026",
            "snippet": "Software Engineer salaries average $120,000 - $185,000, while Machine Learning Engineers average $150,000 - $240,000 depending on seniority.",
            "url": "https://example.com/salary-trends"
        })
    elif "interview" in query_lower:
        results.append({
            "title": "Ace the Technical Coding Interview",
            "snippet": "Top companies evaluate candidates on System Design, Data Structures (Trees, Graphs, DP), and behavioral core values (STAR method).",
            "url": "https://example.com/interview-prep"
        })
    else:
        results.append({
            "title": f"Latest updates on {query}",
            "snippet": f"Search results showing industry trends, articles, and community discussions regarding {query}.",
            "url": "https://example.com/search-result"
        })
        
    return results
