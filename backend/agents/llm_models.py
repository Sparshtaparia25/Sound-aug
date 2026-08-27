from pydantic import BaseModel, Field
from typing import Literal, List
from backend.agents.models import (
    IntentResponse, Intent, AmbiguityResponse,
    NoiseIntent, ChannelIntent, ProsodyIntent,
    LoudnessIntent, SeparationIntent
)

class LLMIntentResponse(BaseModel):
    status: Literal["READY", "NEEDS_CLARIFICATION", "UNSUPPORTED_TRANSFORMATION"] = Field(
        description="Must be READY for supported prompts, NEEDS_CLARIFICATION for vague prompts, UNSUPPORTED_TRANSFORMATION for unsupported capabilities."
    )
    
    target_environment: str = Field(default="", description="Target acoustic environment, e.g., 'auditorium', 'far_field'. Empty if not needed.")
    noise_type: str = Field(default="", description="Type of noise to add, e.g., 'traffic', 'crowd', 'train_station'. Empty if not needed.")
    noise_target_snr_db: float = Field(default=10.0, description="Target SNR in dB if noise is added.")
    
    channel_type: str = Field(default="", description="Channel type, e.g., 'telephone', 'mobile_phone'. Empty if not needed.")
    
    pitch_shift_semitones: float = Field(default=0.0, description="Pitch shift in semitones. 0.0 means no change.")
    time_stretch_rate: float = Field(default=1.0, description="Time stretch rate. 1.0 means no change.")
    
    target_lufs: float = Field(default=-23.0, description="Target LUFS for loudness normalization.")
    
    separation_required: bool = Field(default=False, description="True if source separation (e.g. isolating vocals) is requested.")
    separation_target: str = Field(default="vocals_only", description="Target stem to preserve if separation is required.")
    
    clarification_reason: str = Field(default="", description="Explanation if status is NEEDS_CLARIFICATION or UNSUPPORTED_TRANSFORMATION.")
    suggested_options: list[str] = Field(default_factory=list, description="Suggested options if status is NEEDS_CLARIFICATION.")

def map_llm_intent_to_domain(llm_resp: LLMIntentResponse) -> IntentResponse:
    if llm_resp.status in ["NEEDS_CLARIFICATION", "UNSUPPORTED_TRANSFORMATION"]:
        return IntentResponse(
            is_ambiguous=True,
            ambiguity_details=AmbiguityResponse(
                status=llm_resp.status,
                reason=llm_resp.clarification_reason,
                suggested_options=llm_resp.suggested_options
            ),
            intent=Intent()
        )
    
    # status == READY
    noise = NoiseIntent()
    if llm_resp.noise_type:
        noise = NoiseIntent(
            noise_type=llm_resp.noise_type,
            target_snr_db=llm_resp.noise_target_snr_db
        )
        
    channel = ChannelIntent()
    if llm_resp.channel_type:
        channel = ChannelIntent(channel_type=llm_resp.channel_type)
        
    prosody = ProsodyIntent()
    if llm_resp.pitch_shift_semitones != 0.0 or llm_resp.time_stretch_rate != 1.0:
        prosody = ProsodyIntent(
            pitch_semitones=llm_resp.pitch_shift_semitones,
            time_stretch_rate=llm_resp.time_stretch_rate
        )
        
    loudness = LoudnessIntent(target_lufs=llm_resp.target_lufs)
    
    separation = SeparationIntent()
    if llm_resp.separation_required:
        separation = SeparationIntent(
            required=llm_resp.separation_required,
            target=llm_resp.separation_target
        )
        
    intent = Intent(
        target_environment=llm_resp.target_environment,
        noise=noise,
        channel=channel,
        prosody=prosody,
        loudness=loudness,
        source_separation=separation
    )
    
    return IntentResponse(
        is_ambiguous=False,
        ambiguity_details=AmbiguityResponse(),
        intent=intent
    )
