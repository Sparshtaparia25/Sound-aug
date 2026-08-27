from google import genai
from google.genai import types
import json
from backend.agents.models import IntentResponse
from backend.agents.llm_models import LLMIntentResponse, map_llm_intent_to_domain

def _check_no_refs(schema: dict):
    if isinstance(schema, dict):
        if "$ref" in schema or "$defs" in schema:
            raise ValueError("Configuration Error: Schema contains $ref or $defs which is not supported by Gemini.")
        for k, v in schema.items():
            _check_no_refs(v)
    elif isinstance(schema, list):
        for item in schema:
            _check_no_refs(item)

def extract_intent(prompt: str) -> IntentResponse:
    import os
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    """Uses Gemini to parse a natural language prompt into a structured Semantic Intent or flag as ambiguous."""
    
    schema = LLMIntentResponse.model_json_schema()
    _check_no_refs(schema)
    
    system_instruction = """
    You are an expert audio intent parser.
    Your job is to convert the user's natural language request into a structured Semantic Intent object.
    
    If the prompt requests an UNSUPPORTED capability (e.g., accent removal, speaker identity conversion, translation, speech generation), 
    set `status = "UNSUPPORTED_TRANSFORMATION"`, and explain why in `clarification_reason`.
    
    If the prompt is too vague (e.g., "Make it sound better"), set `status = "NEEDS_CLARIFICATION"`, 
    provide an explanation in `clarification_reason`, and provide `suggested_options`.
    
    Otherwise, set `status = "READY"` and deeply populate the intent properties.
    Distinguish between environments ("Make it sound like a train station") and noise ("Add train station background noise").
    """
    
    response = client.models.generate_content(
        model='models/gemini-3.6-flash',
        contents=f"User Prompt: {prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=LLMIntentResponse,
            temperature=0.1
        )
    )
    
    llm_response = LLMIntentResponse.model_validate_json(response.text)
    return map_llm_intent_to_domain(llm_response)
