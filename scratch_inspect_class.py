import inspect
from google.adk.events.event import Event
from google.adk.runners import Runner

print("Event fields:")
for name, field in Event.model_fields.items():
    print(f"  {name}: {field.annotation}")

print("\nRunner fields:")
print(dir(Runner))
