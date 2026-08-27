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

# New semantic intent models
class NoiseIntent(BaseModel):
    noise_type: str = Field(default="", description="Type of noise, e.g., 'traffic', 'crowd', 'train_station'. Empty if not needed.")
    target_snr_db: float = Field(default=10.0, description="Target SNR in dB.")

class ChannelIntent(BaseModel):
    channel_type: str = Field(default="", description="Channel type, e.g., 'telephone', 'mobile_phone'. Empty if not needed.")

class ProsodyIntent(BaseModel):
    pitch_semitones: float = Field(default=0.0, description="Pitch shift in semitones. 0.0 means no change.")
    time_stretch_rate: float = Field(default=1.0, description="Time stretch rate. 1.0 means no change.")

class LoudnessIntent(BaseModel):
    target_lufs: float = Field(default=-23.0, description="Target LUFS.")

class SeparationIntent(BaseModel):
    required: bool = Field(default=False, description="True if source separation is needed.")
    target: str = Field(default="vocals_only", description="Target stem to preserve.")

class Intent(BaseModel):
    target_environment: str = Field(default="", description="E.g., 'auditorium', 'far_field'. Empty if not needed.")
    noise: NoiseIntent = Field(default_factory=NoiseIntent)
    channel: ChannelIntent = Field(default_factory=ChannelIntent)
    prosody: ProsodyIntent = Field(default_factory=ProsodyIntent)
    loudness: LoudnessIntent = Field(default_factory=LoudnessIntent)
    source_separation: SeparationIntent = Field(default_factory=SeparationIntent)

class AmbiguityResponse(BaseModel):
    status: str = Field(default="NEEDS_CLARIFICATION", description="Either 'NEEDS_CLARIFICATION' or 'UNSUPPORTED_TRANSFORMATION'")
    reason: str = Field(default="", description="Explanation of why the prompt is ambiguous or unsupported.")
    suggested_options: List[str] = Field(default_factory=list, description="List of suggested intents the user could select from.")
    
class IntentResponse(BaseModel):
    is_ambiguous: bool = Field(description="True if the prompt is too vague or unsupported.")
    ambiguity_details: AmbiguityResponse = Field(default_factory=AmbiguityResponse)
    intent: Intent = Field(default_factory=Intent)
    
class TransformationOperation(BaseModel):
    operation: str = Field(description="Must be one of the registered operations (e.g., rir_convolution, noise_injection, eq, pitch_shift, time_stretch, gain, source_separation, distance_simulation, channel_simulation, compression, loudness_normalization).")

    profile: str = Field(default="", description="The asset or profile name, e.g., 'auditorium', 'traffic', 'telephone'.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters matching the operation's requirements and bounds.")

class TransformationPlan(BaseModel):
    seed: int = Field(default=42, description="Random seed for deterministic reproducible transformations.")
    operations: List[TransformationOperation] = Field(description="An ordered list of operations to execute sequentially.")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Global constraints such as max_peak_dbfs, min_snr_db.")

class QualityValidation(BaseModel):
    transformation_success: bool = Field(description="True if all operations passed deterministic QA and match semantic intent.")
    feedback: str = Field(default="", description="Detailed explanation of the QA results and any recommendations.")
    failed_operations: List[str] = Field(default_factory=list, description="List of operations that failed deterministic QA.")
