from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Distribution(BaseModel):
    mean: float
    median: float
    std: float
    p10: float
    p90: float

class FileInfo(BaseModel):
    format: str
    duration: float
    sample_rate: int
    channels: int
    bit_depth: Optional[int] = None

class SignalQuality(BaseModel):
    peak: float
    rms: float
    lufs: Optional[float] = None
    crest_factor: float
    dynamic_range: float
    clipping_ratio: float
    dc_offset: float

class NoiseProfile(BaseModel):
    estimated_snr: float
    noise_floor: float
    snr_confidence: float

class TemporalProfile(BaseModel):
    speech_ratio: float
    silence_ratio: float

class SpectralProfile(BaseModel):
    spectral_centroid: Distribution
    spectral_bandwidth: Distribution
    spectral_rolloff: Distribution
    spectral_flatness: Distribution
    zero_crossing_rate: float

class CepstralProfile(BaseModel):
    mfcc_mean: List[float]
    mfcc_std: List[float]

class ProsodyProfile(BaseModel):
    f0: Optional[Distribution] = None
    voiced_ratio: float

class AcousticEnvironment(BaseModel):
    reverberation_estimate: float

class AudioProfile(BaseModel):
    file_info: FileInfo
    signal_quality: SignalQuality
    noise: NoiseProfile
    temporal: TemporalProfile
    spectral: SpectralProfile
    cepstral: CepstralProfile
    prosody: ProsodyProfile
    environment: AcousticEnvironment

# Keep the other old models for now to not break everything else yet, 
# although they will be updated in Phase 3.
class Intent(BaseModel):
    target_environment: str = Field(default="", description="The intended environment, e.g., 'large_auditorium', 'office'.")
    noise_type: str = Field(default="", description="The type of noise to add, e.g., 'traffic', 'crowd'.")
    noise_required: bool = Field(default=False, description="Whether noise injection is explicitly requested.")
    speaking_rate: str = Field(default="", description="Desired change in speaking rate, e.g., 'faster', 'slower'.")
    pitch_change: str = Field(default="", description="Desired change in pitch, e.g., 'higher', 'deeper'.")
    channel_profile: str = Field(default="", description="The target device or channel, e.g., 'telephone'.")

class AmbiguityResponse(BaseModel):
    status: str = Field(default="NEEDS_CLARIFICATION")
    reason: str = Field(default="", description="Explanation of why the prompt is ambiguous.")
    suggested_options: List[str] = Field(default_factory=list, description="List of suggested intents the user could select from.")
    
class IntentResponse(BaseModel):
    is_ambiguous: bool = Field(description="True if the prompt is too vague to safely infer an intent.")
    ambiguity_details: AmbiguityResponse
    intent: Intent
    
class TransformationOperation(BaseModel):
    operation: str = Field(description="Must be one of the registered operations (e.g., rir_convolution, noise_injection, eq, pitch_shift, time_stretch, gain).")
    profile: str = Field(default="", description="The asset or profile name, e.g., 'auditorium', 'traffic', 'telephone'.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters matching the operation's requirements and bounds.")

class TransformationPlan(BaseModel):
    seed: int = Field(default=42, description="Random seed for deterministic reproducible transformations.")
    operations: List[TransformationOperation] = Field(description="An ordered list of operations to execute sequentially.")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Global constraints such as max_peak_dbfs, min_snr_db.")

class QualityValidation(BaseModel):
    clipping_detected: bool
    snr_db: float = Field(default=0.0)
    transformation_success: bool
    feedback: str = Field(default="", description="Feedback on whether the audio matches the intent. Empty if successful.")
