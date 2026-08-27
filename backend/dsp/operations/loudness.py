import numpy as np
import pyloudnorm as pyln
from typing import Dict, Any

def apply_loudness_normalization(y: np.ndarray, sr: int, parameters: Dict[str, Any]) -> np.ndarray:
    target_lufs = parameters.get("target_lufs", -23.0)
    meter = pyln.Meter(sr)
    current_lufs = meter.integrated_loudness(y)
    
    # Avoid extreme gain changes if signal is pure silence
    if current_lufs == float('-inf') or np.isinf(current_lufs):
        return y
        
    y_norm = pyln.normalize.loudness(y, current_lufs, target_lufs)
    return y_norm
