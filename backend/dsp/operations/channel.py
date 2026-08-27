import numpy as np
from pedalboard import Pedalboard, HighpassFilter, LowpassFilter, Compressor, Gain
from typing import Dict, Any

def apply_channel_simulation(y: np.ndarray, sr: int, profile: str, parameters: Dict[str, Any]) -> np.ndarray:
    effects = []
    
    if profile == "telephone":
        effects = [
            HighpassFilter(cutoff_frequency_hz=300),
            LowpassFilter(cutoff_frequency_hz=3400),
            Compressor(threshold_db=-20.0, ratio=4.0)
        ]
    elif profile == "mobile_phone":
        effects = [
            HighpassFilter(cutoff_frequency_hz=200),
            LowpassFilter(cutoff_frequency_hz=4500),
            Compressor(threshold_db=-15.0, ratio=3.0)
        ]
    elif profile == "low_quality_microphone":
        effects = [
            HighpassFilter(cutoff_frequency_hz=100),
            LowpassFilter(cutoff_frequency_hz=7000),
            Compressor(threshold_db=-10.0, ratio=2.0)
        ]
    elif profile == "radio":
        effects = [
            HighpassFilter(cutoff_frequency_hz=500),
            LowpassFilter(cutoff_frequency_hz=2500),
            Compressor(threshold_db=-25.0, ratio=8.0)
        ]
    
    if not effects:
        return y
        
    board = Pedalboard(effects)
    y_pb = np.expand_dims(y, axis=0) if y.ndim == 1 else y.T
    effected = board(y_pb, sr, reset=False)
    
    return effected[0] if effected.ndim == 2 and effected.shape[0] == 1 else effected.T
