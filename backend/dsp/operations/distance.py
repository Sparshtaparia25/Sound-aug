import numpy as np
from pedalboard import Pedalboard, HighpassFilter, LowpassFilter, Gain
from typing import Dict, Any

def apply_distance_simulation(y: np.ndarray, sr: int, profile: str, parameters: Dict[str, Any]) -> np.ndarray:
    distance_factor = parameters.get("distance_factor", 2.0)
    
    # Simple distance model: attenuation (inverse square law approximation) and HF loss
    attenuation_db = -20 * np.log10(distance_factor)
    hf_cutoff = max(2000, 16000 / distance_factor)
    
    board = Pedalboard([
        LowpassFilter(cutoff_frequency_hz=hf_cutoff),
        Gain(gain_db=attenuation_db)
    ])
    
    y_pb = np.expand_dims(y, axis=0) if y.ndim == 1 else y.T
    effected = board(y_pb, sr, reset=False)
    
    return effected[0] if effected.ndim == 2 and effected.shape[0] == 1 else effected.T
