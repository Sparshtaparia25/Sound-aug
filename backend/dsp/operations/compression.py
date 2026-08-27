import numpy as np
from pedalboard import Pedalboard, Compressor
from typing import Dict, Any

def apply_compression(y: np.ndarray, sr: int, parameters: Dict[str, Any]) -> np.ndarray:
    threshold = parameters.get("threshold_db", -20.0)
    ratio = parameters.get("ratio", 4.0)
    attack = parameters.get("attack_ms", 5.0)
    release = parameters.get("release_ms", 100.0)
    makeup = parameters.get("makeup_gain_db", 0.0)
    
    board = Pedalboard([
        Compressor(threshold_db=threshold, ratio=ratio, attack_ms=attack, release_ms=release)
    ])
    
    y_pb = np.expand_dims(y, axis=0) if y.ndim == 1 else y.T
    effected = board(y_pb, sr, reset=False)
    
    if makeup > 0.0:
        effected = effected * (10 ** (makeup / 20.0))
        
    return effected[0] if effected.ndim == 2 and effected.shape[0] == 1 else effected.T
