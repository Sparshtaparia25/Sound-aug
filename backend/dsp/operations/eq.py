import numpy as np
from pedalboard import Pedalboard, HighShelfFilter, LowShelfFilter
from typing import Dict, Any

def apply_eq(y: np.ndarray, sr: int, parameters: Dict[str, Any]) -> np.ndarray:
    low_shelf = parameters.get("low_shelf_db", 0.0)
    high_shelf = parameters.get("high_shelf_db", 0.0)
    
    board = Pedalboard([
        LowShelfFilter(cutoff_frequency_hz=250.0, gain_db=low_shelf),
        HighShelfFilter(cutoff_frequency_hz=4000.0, gain_db=high_shelf)
    ])
    
    y_pb = np.expand_dims(y, axis=0) if y.ndim == 1 else y.T
    effected = board(y_pb, sr, reset=False)
    return effected[0] if effected.ndim == 2 and effected.shape[0] == 1 else effected.T
