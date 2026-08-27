import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
from backend.agents.models import Intent, AudioProfile, TransformationPlan
from backend.dsp.registry import REGISTRY


class ValidationErrorDetail(BaseModel):
    operation: str
    parameter: Optional[str] = None
    value: Any = None
    allowed_range: Optional[List[float]] = None
    reason: str

class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationErrorDetail] = []

def plan_transformation(intent: Intent, profile: AudioProfile, previous_plan: Optional[TransformationPlan] = None, validation_result: Optional[ValidationResult] = None) -> TransformationPlan:
    client = genai.Client()
    """Uses Gemini to generate an ordered list of registered DSP operations."""
    
    registry_schema = {name: op.model_dump() for name, op in REGISTRY.items()}
    
    prompt = f"""
    You are an expert audio DSP planner.
    Based on the Semantic Intent and the current Audio Profile, generate a precise Transformation Plan.
    You MUST select an ordered list of operations from the provided Transformation Registry.
    
    Transformation Registry:
    {json.dumps(registry_schema, indent=2)}
    
    Semantic Intent:
    {intent.model_dump_json(indent=2)}
    
    Input Profile:
    {profile.model_dump_json(indent=2)}
    """
    
    if previous_plan and validation_result:
        prompt += f"""
        
        WARNING: Your previous plan failed Registry Validation.
        
        Previous Plan:
        {previous_plan.model_dump_json(indent=2)}
        
        Validation Errors (MUST FIX):
        {validation_result.model_dump_json(indent=2)}
        
        Please generate a new plan correcting these specific errors.
        """
    else:
        prompt += """
        Generate specific registered operations with parameters strictly within the bounds.
        Order matters (e.g., Convolution before Noise, EQ after Noise).
        """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TransformationPlan,
            temperature=0.1
        )
    )
    return TransformationPlan.model_validate_json(response.text)
