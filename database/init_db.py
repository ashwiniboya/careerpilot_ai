import sys
import os
from loguru import logger

# Add project root directory to path to enable module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, Base
# Import models to ensure they are registered with Base metadata
from database.models import User, UserProfile, Resume, ResumeVersion, CareerHistory, InterviewHistory, SkillTracking, Roadmap, RoadmapStep, JobApplication, Memory, TokenUsage

def init_db():
    logger.info("Initializing relational database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.success("Relational database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
