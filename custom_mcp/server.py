import os
import sys
from typing import List, Dict, Any, Optional
from loguru import logger
from mcp.server.fastmcp import FastMCP

# Add parent directory to sys.path to resolve imports when running as standalone script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_mcp.tools.resume_tools import parse_resume_content, calculate_ats_metrics
from custom_mcp.tools.job_tools import find_jobs
from custom_mcp.tools.search_tools import get_company_profile, execute_web_search
from custom_mcp.tools.tracking_tools import recommend_courses, generate_roadmap_structure

# 1. Initialize FastMCP Server
mcp = FastMCP("CareerPilot Server")

# Configure logger to output only to stderr to avoid corrupting stdio transport
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))

# 2. Expose Tools using @mcp.tool decorators
@mcp.tool()
def parse_resume(file_path: str) -> Dict[str, Any]:
    """
    Parses a local resume file (PDF, DOCX, TXT, MD) and extracts contact info, skills, and experience sections.
    
    Args:
        file_path: The absolute path to the local resume file.
        
    Returns:
        A dictionary containing status, extracted email, phone, skills, and raw sections.
    """
    logger.info(f"MCP Tool 'parse_resume' invoked for: {file_path}")
    try:
        return parse_resume_content(file_path)
    except Exception as e:
        logger.error(f"MCP parse_resume error: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def calculate_ats_score(resume_content: str, job_description: str) -> Dict[str, Any]:
    """
    Evaluates matching scores, missing keywords, and readability metrics of a resume against a job description.
    
    Args:
        resume_content: Raw text or markdown content of the candidate's resume.
        job_description: Target job description text.
        
    Returns:
        A dictionary with overall_score, matching_keywords, missing_keywords, readability, and suggestions.
    """
    logger.info("MCP Tool 'calculate_ats_score' invoked.")
    try:
        return calculate_ats_metrics(resume_content, job_description)
    except Exception as e:
        logger.error(f"MCP calculate_ats_score error: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def search_jobs(skills: List[str], target_role: Optional[str] = None, location: Optional[str] = "Remote") -> Dict[str, Any]:
    """
    Queries mock/live job databases for jobs matching user skills, roles, and locations.
    
    Args:
        skills: List of current skills (e.g. ['Python', 'SQL']).
        target_role: Target job title.
        location: Location preference (default is 'Remote').
        
    Returns:
        A dictionary containing a list of matched jobs with percentages and matched skills.
    """
    logger.info(f"MCP Tool 'search_jobs' invoked. Role: {target_role}, Location: {location}")
    try:
        jobs = find_jobs(skills, target_role, location)
        return {"status": "success", "jobs": jobs}
    except Exception as e:
        logger.error(f"MCP search_jobs error: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_company_insights(company_name: str) -> Dict[str, Any]:
    """
    Retrieves cultural description, technology stack, and recent strategic updates about a target company.
    
    Args:
        company_name: Name of the company to research.
        
    Returns:
        A dictionary containing company description, tech stack, and cultural profile.
    """
    logger.info(f"MCP Tool 'get_company_insights' invoked for: {company_name}")
    try:
        return get_company_profile(company_name)
    except Exception as e:
        logger.error(f"MCP get_company_insights error: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def web_search(query: str) -> Dict[str, Any]:
    """
    Executes a web search to retrieve relevant career trends, interview questions, or company data.
    
    Args:
        query: Raw search query string.
        
    Returns:
        A dictionary containing list of matches with title, snippet, and URLs.
    """
    logger.info(f"MCP Tool 'web_search' invoked for query: {query}")
    try:
        results = await execute_web_search(query)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"MCP web_search error: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def recommend_learning_resources(skills: List[str]) -> Dict[str, Any]:
    """
    Suggests online tutorials, books, and courses based on candidate skill gaps.
    
    Args:
        skills: List of skills to acquire.
        
    Returns:
        A dictionary containing suggested course titles, platforms, durations, and ratings.
    """
    logger.info(f"MCP Tool 'recommend_learning_resources' invoked.")
    try:
        courses = recommend_courses(skills)
        return {"status": "success", "courses": courses}
    except Exception as e:
        logger.error(f"MCP recommend_learning_resources error: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def generate_roadmap(current_skills: List[str], target_role: str) -> Dict[str, Any]:
    """
    Generates a structured career roadmap outlining milestones to bridge skills gaps.
    
    Args:
        current_skills: List of candidate's current skills.
        target_role: Intended career path or target job role.
        
    Returns:
        A dictionary detailing step-by-step milestones, instructions, and materials.
    """
    logger.info(f"MCP Tool 'generate_roadmap' invoked. Target: {target_role}")
    try:
        steps = generate_roadmap_structure(current_skills, target_role)
        return {"status": "success", "steps": steps}
    except Exception as e:
        logger.error(f"MCP generate_roadmap error: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run()
