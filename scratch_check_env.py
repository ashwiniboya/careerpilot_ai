import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

print("GEMINI_API_KEY present:", bool(os.getenv("GEMINI_API_KEY")))
try:
    import google.adk as adk
    print("google.adk successfully imported!")
    print("adk dir:", dir(adk))
    from google.adk import Agent
    print("Agent fields:", Agent.model_fields.keys() if hasattr(Agent, "model_fields") else dir(Agent))
except Exception as e:
    print("Import error:", e)
