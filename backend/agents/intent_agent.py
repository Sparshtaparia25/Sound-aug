from google import genai
from google.genai import types
from backend.agents.models import IntentResponse

def extract_intent(prompt: str) -> IntentResponse:
    import os
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    """Uses Gemini to parse a natural language prompt into a structured Semantic Intent or flag as ambiguous."""
    
    system_instruction = """
    You are an expert audio intent parser.
    Your job is to convert the user's natural language request into a structured Intent object.
    You do NOT select DSP parameters. You purely extract the semantic intent.
    
    If the prompt is too vague to safely infer an intent (e.g., "Make it sound better", "Change it"),
    set `is_ambiguous = true` and provide `ambiguity_details` with suggested options.
    Otherwise, set `is_ambiguous = false` and populate the `intent` object.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=f"User Prompt: {prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=IntentResponse,
            temperature=0.1
        )
    )
    
    return IntentResponse.model_validate_json(response.text)
