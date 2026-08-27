from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

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
        required_parameters=["wet_mix"],
        optional_parameters=[],
        parameter_bounds={
            "wet_mix": ParameterBound(min_val=0.0, max_val=1.0)
        },
        allowed_profiles=["auditorium", "classroom", "office"],
        expected_effects=["Reverberation ↑", "RT60 ↑", "Direct/reverberant ratio ↓"]
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
        allowed_profiles=["traffic", "cafe", "crowd", "office"],
        expected_effects=["SNR ↓", "Noise floor ↑"]
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
        description="Applies a bandpass filter or generic EQ.",
        required_parameters=["highpass_freq", "lowpass_freq"],
        optional_parameters=[],
        parameter_bounds={
            "highpass_freq": ParameterBound(min_val=20.0, max_val=8000.0),
            "lowpass_freq": ParameterBound(min_val=100.0, max_val=20000.0)
        },
        allowed_profiles=["telephone", "custom"],
        expected_effects=["Spectral Bandwidth ↓"]
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
    )
}

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
