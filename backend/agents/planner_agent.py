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
    import os
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
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
        You MUST only select capabilities that exist in the Registry.
        You MUST include ALL `required_parameters` for each operation inside the `parameters` object (e.g. if using `noise_injection`, you MUST provide `target_snr_db`).
        The exact execution order will be strictly enforced by the Deterministic Engine Policy:
        (1) Source Separation -> (2) Environment/RIR -> (3) Noise -> (4) Distance -> (5) Channel -> (6) Prosody -> (7) EQ/Compression/Loudness.
        Make reasonable mappings (e.g., 'slightly deeper' -> -2 semitones, 'faster' -> rate=1.2).
        
        IMPORTANT: Your output MUST be valid JSON with the following structure:
        {
            "seed": 42,
            "operations": [
                {
                    "operation": "operation_name",
                    "reasoning": "Explanation of why this operation and parameters were chosen.",
                    "profile": "profile_name_or_empty",
                    "parameters": {"target_snr_db": 10.0}
                }
            ],
            "constraints": {}
        }
        """
    
    transformation_operation_schema = {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING", 
                "description": "Must be one of the registered operations."
            },
            "reasoning": {
                "type": "STRING",
                "description": "Your step-by-step thinking for selecting this operation and its parameters."
            },
            "profile": {
                "type": "STRING", 
                "description": "The exact strict string for the asset or profile name, e.g., 'auditorium'."
            },
            "parameters": {
                "type": "OBJECT", 
                "description": "Parameters matching the operation's requirements."
            }
        },
        "required": ["operation", "parameters", "reasoning", "profile"]
    }
    
    transformation_plan_schema = {
        "type": "OBJECT",
        "properties": {
            "seed": {"type": "INTEGER", "description": "Random seed."},
            "operations": {
                "type": "ARRAY",
                "items": transformation_operation_schema,
                "description": "Ordered list of operations."
            },
            "constraints": {
                "type": "OBJECT", 
                "description": "Global constraints."
            }
        },
        "required": ["operations"]
    }

    response = client.models.generate_content(
        model='models/gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=transformation_plan_schema,
            temperature=0.1
        )
    )
    return TransformationPlan.model_validate_json(response.text)
