import numpy as np
from typing import Dict, Any

def apply_gain(y: np.ndarray, sr: int, parameters: Dict[str, Any]) -> np.ndarray:
    gain_db = parameters.get("gain_db", 0.0)
    scale = 10 ** (gain_db / 20.0)
    return y * scale
