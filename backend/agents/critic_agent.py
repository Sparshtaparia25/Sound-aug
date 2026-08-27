from google import genai
from google.genai import types
from .models import IntentUnderstanding, TransformationPlan, QualityValidation

import os
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def validate_transformation(
    intent: IntentUnderstanding, 
    plan: TransformationPlan, 
    original_profile: dict, 
    new_profile: dict
) -> QualityValidation:
    """Uses Gemini to evaluate if the new audio profile matches the user intent and transformation plan."""
    
    prompt = f"""
    You are an expert audio Quality Assurance Critic.
    Evaluate whether the applied audio transformation was successful and meets the User Intent without excessive degradation.
    
    User Intent:
    {intent.model_dump_json(indent=2)}
    
    Transformation Plan applied:
    {plan.model_dump_json(indent=2)}
    
    Original Audio Profile:
    {original_profile}
    
    New Audio Profile:
    {new_profile}
    
    Ensure that:
    1. Clipping is not detected (or minimal).
    2. SNR is acceptable (unless heavy noise was intentionally added).
    3. The changes in RMS/duration/etc align with the intent.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QualityValidation,
            temperature=0.1
        )
    )
    return QualityValidation.model_validate_json(response.text)
