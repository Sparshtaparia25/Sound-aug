import random
import numpy as np
import librosa
import soundfile as sf
import json

from backend.agents.models import TransformationPlan
from backend.dsp.registry import validate_operation
from backend.config import config
from backend.dsp.operations import (
    apply_rir, apply_noise, apply_distance_simulation,
    apply_channel_simulation, apply_compression, apply_eq,
    apply_gain, apply_loudness_normalization,
    apply_pitch_shift, apply_time_stretch
)

if config.SEPARATION_ENABLED:
    from backend.separation.factory import get_separator

PRECEDENCE = {
    "source_separation": 10,
    
    "rir_convolution": 20,
    "distance_simulation": 21,
    
    "noise_injection": 30,
    
    "channel_simulation": 40,
    
    "pitch_shift": 50,
    "time_stretch": 51,
    
    "eq": 60,
    "compression": 61,
    "gain": 62,
    "loudness_normalization": 63
}

def process_audio(input_path: str, output_path: str, plan: TransformationPlan):
    """Executes deterministic audio transformations based on the registry."""
    
    np.random.seed(plan.seed)
    random.seed(plan.seed)
    
    y, sr = librosa.load(input_path, sr=None)
    
    # Sort operations by strictly defined precedence
    sorted_ops = sorted(
        plan.operations, 
        key=lambda op: PRECEDENCE.get(op.operation, 100)
    )
    
    trace_metadata = []
    
    for op in sorted_ops:
        validate_operation(op.operation, op.profile, op.parameters)
        
        op_trace = {
            "operation": op.operation,
            "profile": op.profile,
            "parameters_in": op.parameters
        }
        
        if op.operation == "source_separation":
            if not config.SEPARATION_ENABLED:
                raise ValueError("Source separation is not enabled in this environment.")
            separator = get_separator()
            y = separator.separate(y, sr, op.profile)
            
        elif op.operation == "rir_convolution":
            y, meta = apply_rir(y, sr, op.profile, op.parameters, plan.seed)
            op_trace["metadata"] = meta
            
        elif op.operation == "distance_simulation":
            y = apply_distance_simulation(y, sr, op.profile, op.parameters)
            
        elif op.operation == "noise_injection":
            y, meta = apply_noise(y, sr, op.profile, op.parameters, plan.seed)
            op_trace["metadata"] = meta
            
        elif op.operation == "channel_simulation":
            y = apply_channel_simulation(y, sr, op.profile, op.parameters)
            
        elif op.operation == "pitch_shift":
            y = apply_pitch_shift(y, sr, op.parameters)
            
        elif op.operation == "time_stretch":
            y = apply_time_stretch(y, sr, op.parameters)
            
        elif op.operation == "eq":
            y = apply_eq(y, sr, op.parameters)
            
        elif op.operation == "compression":
            y = apply_compression(y, sr, op.parameters)
            
        elif op.operation == "gain":
            y = apply_gain(y, sr, op.parameters)
            
        elif op.operation == "loudness_normalization":
            y = apply_loudness_normalization(y, sr, op.parameters)
            
        trace_metadata.append(op_trace)

    # Prevent hard clipping by normalizing if peak > 1.0
    peak = np.max(np.abs(y))
    if peak > 1.0:
        y = y / peak

    # Save output
    sf.write(output_path, y, sr)
    
    # Save trace alongside
    trace_path = output_path + ".trace.json"
    with open(trace_path, 'w') as f:
        json.dump(trace_metadata, f, indent=2)
    
    return True
