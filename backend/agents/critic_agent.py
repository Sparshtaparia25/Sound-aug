from google import genai
from google.genai import types
from .models import Intent, TransformationPlan, QualityValidation
from backend.dsp.qa import QA_Result
from typing import List
import os

def validate_transformation(
    intent: Intent, 
    plan: TransformationPlan, 
    qa_results: List[QA_Result]
) -> QualityValidation:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    """Uses Gemini to evaluate and explain the deterministic QA results."""
    
    qa_json = [r.model_dump() for r in qa_results]
    
    prompt = f"""
    You are an expert audio Quality Assurance Critic.
    The deterministic pipeline has run and provided PASS/FAIL results for each operation based on strict acoustic metrics.
    Your job is to read these results, determine overall success, and explain the outcome to the user.
    
    User Intent:
    {intent.model_dump_json(indent=2)}
    
    Transformation Plan applied:
    {plan.model_dump_json(indent=2)}
    
    Deterministic QA Results:
    {qa_json}
    
    If any operation failed its QA, the transformation is generally unsuccessful unless it's a minor warning.
    List failed operations explicitly. Provide a clear explanation of what happened.
    """
    
    response = client.models.generate_content(
        model='models/gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QualityValidation,
            temperature=0.1
        )
    )
    return QualityValidation.model_validate_json(response.text)
