from google.genai import types
for name, field in types.GenerateContentResponseUsageMetadata.model_fields.items():
    print(f"  {name}: {field.annotation}")
