from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.dsp.asset_manager import asset_manager
from backend.dsp.acoustics.room_profiles import ROOM_PROFILES
from backend.config import config

class ParameterBound(BaseModel):
    min_val: float
    max_val: float

class OperationDefinition(BaseModel):
    name: str
    family: str
    description: str
    required_parameters: List[str]
    optional_parameters: List[str]
    parameter_bounds: Dict[str, ParameterBound]
    allowed_profiles: List[str]
    expected_effects: List[str]

REGISTRY = {
    "rir_convolution": OperationDefinition(
        name="rir_convolution",
        family="Acoustic Environment Simulation",
        description="Applies a room impulse response via FFT convolution.",
        required_parameters=[],
        optional_parameters=["wet_mix"],
        parameter_bounds={
            "wet_mix": ParameterBound(min_val=0.0, max_val=1.0)
        },
        allowed_profiles=list(ROOM_PROFILES.keys()),
        expected_effects=["Reverberation ↑", "RT60 ↑", "Direct/reverberant ratio ↓"]
    ),
    "distance_simulation": OperationDefinition(
        name="distance_simulation",
        family="Acoustic Environment Simulation",
        description="Simulates increased source-to-microphone distance.",
        required_parameters=["distance_factor"],
        optional_parameters=[],
        parameter_bounds={
            "distance_factor": ParameterBound(min_val=1.0, max_val=5.0)
        },
        allowed_profiles=["far_field", "distant"],
        expected_effects=["Loudness ↓", "Direct/reverberant ratio ↓", "High-frequency energy ↓"]
    ),
    "noise_injection": OperationDefinition(
        name="noise_injection",
        family="Noise Injection",
        description="Mixes calibrated noise from a library to achieve a target SNR.",
        required_parameters=["target_snr_db"],
        optional_parameters=[],
        parameter_bounds={
            "target_snr_db": ParameterBound(min_val=0.0, max_val=40.0)
        },
        allowed_profiles=asset_manager.get_available_noise_profiles(),
        expected_effects=["SNR ↓", "Noise floor ↑"]
    ),
    "channel_simulation": OperationDefinition(
        name="channel_simulation",
        family="Channel / Device",
        description="Simulates device frequency response, band limitations, and channel effects.",
        required_parameters=[],
        optional_parameters=[],
        parameter_bounds={},
        allowed_profiles=["telephone", "mobile_phone", "low_quality_microphone", "radio"],
        expected_effects=["Spectral Bandwidth ↓", "Coloration changes"]
    ),
    "pitch_shift": OperationDefinition(
        name="pitch_shift",
        family="Prosodic Augmentation",
        description="Shifts the pitch by N semitones without affecting duration.",
        required_parameters=["semitones"],
        optional_parameters=[],
        parameter_bounds={
            "semitones": ParameterBound(min_val=-12.0, max_val=12.0)
        },
        allowed_profiles=[],
        expected_effects=["F0 changes", "Duration ≈ constant"]
    ),
    "time_stretch": OperationDefinition(
        name="time_stretch",
        family="Prosodic Augmentation",
        description="Changes playback speed by a factor without affecting pitch.",
        required_parameters=["rate"],
        optional_parameters=[],
        parameter_bounds={
            "rate": ParameterBound(min_val=0.5, max_val=2.0)
        },
        allowed_profiles=[],
        expected_effects=["Duration changes", "F0 ≈ constant"]
    ),
    "eq": OperationDefinition(
        name="eq",
        family="Signal-Level Augmentation",
        description="Applies a generic EQ.",
        required_parameters=[],
        optional_parameters=["low_shelf_db", "high_shelf_db"],
        parameter_bounds={
            "low_shelf_db": ParameterBound(min_val=-20.0, max_val=20.0),
            "high_shelf_db": ParameterBound(min_val=-20.0, max_val=20.0)
        },
        allowed_profiles=["telephone", "voice_bright", "voice_warm", "custom"],
        expected_effects=["Spectral balance changed"]
    ),
    "gain": OperationDefinition(
        name="gain",
        family="Signal-Level Augmentation",
        description="Applies linear gain in dB.",
        required_parameters=["gain_db"],
        optional_parameters=[],
        parameter_bounds={
            "gain_db": ParameterBound(min_val=-30.0, max_val=10.0)
        },
        allowed_profiles=[],
        expected_effects=["RMS ↑ or ↓", "Peak ↑ or ↓"]
    ),
    "compression": OperationDefinition(
        name="compression",
        family="Signal-Level Augmentation",
        description="Applies dynamic range compression.",
        required_parameters=["threshold_db", "ratio"],
        optional_parameters=["attack_ms", "release_ms", "makeup_gain_db"],
        parameter_bounds={
            "threshold_db": ParameterBound(min_val=-60.0, max_val=0.0),
            "ratio": ParameterBound(min_val=1.0, max_val=20.0),
            "attack_ms": ParameterBound(min_val=0.1, max_val=100.0),
            "release_ms": ParameterBound(min_val=10.0, max_val=1000.0),
            "makeup_gain_db": ParameterBound(min_val=0.0, max_val=24.0)
        },
        allowed_profiles=[],
        expected_effects=["Dynamic range ↓", "Peak controlled"]
    ),
    "loudness_normalization": OperationDefinition(
        name="loudness_normalization",
        family="Signal-Level Augmentation",
        description="Normalizes audio to a target LUFS.",
        required_parameters=["target_lufs"],
        optional_parameters=[],
        parameter_bounds={
            "target_lufs": ParameterBound(min_val=-40.0, max_val=-5.0)
        },
        allowed_profiles=[],
        expected_effects=["RMS changed", "Target LUFS matched"]
    )
}

if config.SEPARATION_ENABLED:
    REGISTRY["source_separation"] = OperationDefinition(
        name="source_separation",
        family="Machine Learning Processing",
        description="Separates background music from vocals to preserve speech.",
        required_parameters=[],
        optional_parameters=[],
        parameter_bounds={},
        allowed_profiles=["vocals_only", "speech_isolation"],
        expected_effects=["Background music ↓", "Vocals isolated"]
    )

def validate_operation(op_name: str, profile: Optional[str], params: Dict[str, Any]) -> bool:
    if op_name not in REGISTRY:
        raise ValueError(f"Unknown operation: {op_name}")
        
    defn = REGISTRY[op_name]
    
    if profile and profile not in defn.allowed_profiles and defn.allowed_profiles:
        raise ValueError(f"Profile '{profile}' not allowed for {op_name}. Allowed: {defn.allowed_profiles}")
        
    for req_param in defn.required_parameters:
        if req_param not in params:
            raise ValueError(f"Missing required parameter '{req_param}' for {op_name}")
            
    for param_name, param_val in params.items():
        if param_name in defn.parameter_bounds:
            bounds = defn.parameter_bounds[param_name]
            if not (bounds.min_val <= param_val <= bounds.max_val):
                raise ValueError(f"Parameter '{param_name}' value {param_val} out of bounds [{bounds.min_val}, {bounds.max_val}] for {op_name}")
                
    return True

