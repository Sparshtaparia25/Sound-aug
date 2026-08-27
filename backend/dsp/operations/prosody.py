import numpy as np
import librosa
from typing import Dict, Any

def apply_pitch_shift(y: np.ndarray, sr: int, parameters: Dict[str, Any]) -> np.ndarray:
    semitones = parameters.get("semitones", 0.0)
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)

def apply_time_stretch(y: np.ndarray, sr: int, parameters: Dict[str, Any]) -> np.ndarray:
    rate = parameters.get("rate", 1.0)
    return librosa.effects.time_stretch(y, rate=rate)
