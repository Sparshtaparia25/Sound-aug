import os
import pytest
from backend.agents.intent_agent import extract_intent

# Skip this entire module if GEMINI_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY is not set"
)

def test_intent_ready_auditorium():
    prompt = "Make it sound like a large auditorium."
    resp = extract_intent(prompt)
    assert resp.is_ambiguous is False
    assert resp.intent.target_environment.lower() == "auditorium"
    assert resp.intent.noise.noise_type == ""
    assert resp.intent.source_separation.required is False

def test_intent_needs_clarification():
    prompt = "Make it sound better."
    resp = extract_intent(prompt)
    assert resp.is_ambiguous is True
    assert resp.ambiguity_details.status == "NEEDS_CLARIFICATION"

def test_intent_unsupported_transformation():
    prompt = "Remove the speaker's accent."
    resp = extract_intent(prompt)
    assert resp.is_ambiguous is True
    assert resp.ambiguity_details.status == "UNSUPPORTED_TRANSFORMATION"
