import pytest
from backend.agents.llm_models import LLMIntentResponse, map_llm_intent_to_domain
from backend.agents.models import IntentResponse

def test_model_construction():
    resp = LLMIntentResponse(status="READY", target_environment="auditorium")
    assert resp.status == "READY"
    assert resp.target_environment == "auditorium"

def test_json_serialization():
    resp = LLMIntentResponse(status="READY", target_environment="auditorium")
    json_str = resp.model_dump_json()
    assert "READY" in json_str
    assert "auditorium" in json_str

def test_schema_generation_no_refs():
    schema = LLMIntentResponse.model_json_schema()
    
    def check_no_refs(s: dict):
        if isinstance(s, dict):
            assert "$ref" not in s
            assert "$defs" not in s
            for v in s.values():
                check_no_refs(v)
        elif isinstance(s, list):
            for item in s:
                check_no_refs(item)
                
    check_no_refs(schema)

def test_ready_maps_correctly():
    llm_resp = LLMIntentResponse(
        status="READY",
        target_environment="hall",
        noise_type="traffic",
        noise_target_snr_db=5.0
    )
    
    domain_resp = map_llm_intent_to_domain(llm_resp)
    
    assert domain_resp.is_ambiguous is False
    assert domain_resp.intent.target_environment == "hall"
    assert domain_resp.intent.noise.noise_type == "traffic"
    assert domain_resp.intent.noise.target_snr_db == 5.0
    assert domain_resp.intent.channel.channel_type == ""
    assert domain_resp.intent.prosody.pitch_semitones == 0.0

def test_needs_clarification_maps_correctly():
    llm_resp = LLMIntentResponse(
        status="NEEDS_CLARIFICATION",
        clarification_reason="Vague prompt.",
        suggested_options=["A", "B"]
    )
    
    domain_resp = map_llm_intent_to_domain(llm_resp)
    
    assert domain_resp.is_ambiguous is True
    assert domain_resp.ambiguity_details.status == "NEEDS_CLARIFICATION"
    assert domain_resp.ambiguity_details.reason == "Vague prompt."
    assert domain_resp.ambiguity_details.suggested_options == ["A", "B"]

def test_unsupported_transformation_maps_correctly():
    llm_resp = LLMIntentResponse(
        status="UNSUPPORTED_TRANSFORMATION",
        clarification_reason="Cannot translate."
    )
    
    domain_resp = map_llm_intent_to_domain(llm_resp)
    
    assert domain_resp.is_ambiguous is True
    assert domain_resp.ambiguity_details.status == "UNSUPPORTED_TRANSFORMATION"
    assert domain_resp.ambiguity_details.reason == "Cannot translate."

def test_default_values_normalize():
    llm_resp = LLMIntentResponse(status="READY")
    domain_resp = map_llm_intent_to_domain(llm_resp)
    
    assert domain_resp.is_ambiguous is False
    assert domain_resp.intent.target_environment == ""
    assert domain_resp.intent.noise.noise_type == ""
    assert domain_resp.intent.channel.channel_type == ""
    assert domain_resp.intent.prosody.pitch_semitones == 0.0
    assert domain_resp.intent.prosody.time_stretch_rate == 1.0
    assert domain_resp.intent.loudness.target_lufs == -23.0
    assert domain_resp.intent.source_separation.required is False
