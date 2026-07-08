import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv()

# We need a dummy agent to run
from src.agents.resume_agent import ResumeAgent

async def main():
    agent = ResumeAgent()
    prompt = "Hello"
    session_id = "test"
    enriched_prompt = agent._enrich_prompt(prompt)

    runner, session_service = agent._make_runner()
    await session_service.create_session(
        app_name="careerpilot",
        user_id="test_user",
        session_id=session_id,
    )

    from google.genai import types as genai_types
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=enriched_prompt)],
    )

    print("Running runner.run_async...")
    try:
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session_id,
            new_message=content,
        ):
            print("\n--- Event ---")
            print("Type:", type(event))
            print("Attributes:", dir(event))
            # Try to print some common attributes if they exist
            for attr in ['content', 'message', 'tool_calls', 'metrics', 'usage', 'response', 'usage_metadata']:
                if hasattr(event, attr):
                    print(f"  {attr}:", getattr(event, attr))
            if hasattr(event, 'is_final_response'):
                print("  is_final_response():", event.is_final_response())
    except Exception as e:
        print("Error during execution:", e)

if __name__ == "__main__":
    asyncio.run(main())
