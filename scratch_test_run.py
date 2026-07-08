import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv()

from src.agents.resume_agent import ResumeAgent

try:
    agent = ResumeAgent()
    print("ResumeAgent instantiated successfully!")
    res = agent.run("Test prompt")
    print("Response:", res)
except Exception as e:
    print("Execution failed:", e)
