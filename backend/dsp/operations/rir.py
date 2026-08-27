import numpy as np
import scipy.signal
from typing import Dict, Any, Tuple
from backend.dsp.acoustics.rir_generator import generate_rir

def apply_rir(y: np.ndarray, sr: int, profile: str, parameters: Dict[str, Any], seed: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    wet_mix = parameters.get("wet_mix", 0.5)
    
    # Generate RIR procedurally in memory
    rir, metadata = generate_rir(profile, seed, sr)
    
    # FFT Convolution (RIR and y)
    convolved = scipy.signal.fftconvolve(y, rir, mode='full')
    convolved = convolved[:len(y)]  # Match original length
    
    # Mix
    y_out = (1.0 - wet_mix) * y + wet_mix * convolved
    
    # Add operation info to metadata
    metadata["wet_mix"] = wet_mix
    metadata["rir_duration_seconds"] = len(rir) / sr
    
    return y_out, metadata
