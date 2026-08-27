import numpy as np
import librosa
from typing import Dict, Any, Tuple
from backend.dsp.asset_manager import asset_manager
import math
import os

def apply_noise(y: np.ndarray, sr: int, profile: str, parameters: Dict[str, Any], seed: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    target_snr = parameters.get("target_snr_db", 10.0)
    
    asset_meta = asset_manager.get_noise_asset(profile, seed)
    noise_path = os.path.join("backend", "dsp", "assets", "noise", asset_meta["file"])
    
    if not os.path.exists(noise_path):
        raise FileNotFoundError(f"Noise asset not found: {noise_path}")
        
    noise, _ = librosa.load(noise_path, sr=sr)
    
    rng = np.random.default_rng(seed)
    
    if len(noise) > len(y):
        max_start = len(noise) - len(y)
        start_idx = rng.integers(0, max_start + 1)
        noise = noise[start_idx:start_idx + len(y)]
    elif len(noise) < len(y):
        repeats = int(np.ceil(len(y) / len(noise)))
        noise = np.tile(noise, repeats)
        noise = noise[:len(y)]
        
    ps = np.mean(y**2)
    pn = np.mean(noise**2)
    
    scale = 0.0
    measured_injected_snr = float('inf')
    
    if pn > 1e-10 and ps > 1e-10:
        scale = np.sqrt(ps / (pn * (10 ** (target_snr / 10.0))))
        scaled_pn = np.mean((scale * noise)**2)
        if scaled_pn > 1e-10:
            measured_injected_snr = 10 * np.log10(ps / scaled_pn)
    
    y_out = y + scale * noise
    
    metadata = {
        "profile": profile,
        "seed": seed,
        "target_snr_db": target_snr,
        "measured_injected_snr": float(measured_injected_snr),
        "scaling_factor": float(scale),
        "asset_id": asset_meta["id"],
        "source": asset_meta.get("source", "unknown"),
        "license": asset_meta.get("license", "unknown")
    }
        
    return y_out, metadata
