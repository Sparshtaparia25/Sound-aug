import numpy as np
import pyroomacoustics as pra
from typing import Dict, Any, Tuple
from backend.dsp.acoustics.room_profiles import ROOM_PROFILES

def generate_rir(profile: str, seed: int, sr: int = 16000) -> Tuple[np.ndarray, Dict[str, Any]]:
    if profile not in ROOM_PROFILES:
        raise ValueError(f"Unknown room profile: {profile}")
        
    rng = np.random.default_rng(seed)
    prof_cfg = ROOM_PROFILES[profile]
    
    # Resolve dimensions
    dim_x = rng.uniform(prof_cfg["dim_ranges"]["x"][0], prof_cfg["dim_ranges"]["x"][1])
    dim_y = rng.uniform(prof_cfg["dim_ranges"]["y"][0], prof_cfg["dim_ranges"]["y"][1])
    dim_z = rng.uniform(prof_cfg["dim_ranges"]["z"][0], prof_cfg["dim_ranges"]["z"][1])
    room_dim = [dim_x, dim_y, dim_z]
    
    # Resolve target RT60
    target_rt60 = rng.uniform(prof_cfg["target_rt60_range"][0], prof_cfg["target_rt60_range"][1])
    
    # Compute required absorption and max order using inverse Sabine
    # Note: inverse_sabine returns (energy_absorption, max_order)
    absorption, max_order = pra.inverse_sabine(target_rt60, room_dim)
    
    # Optional: limit max_order for performance if it's too high
    max_order_cfg = prof_cfg.get("max_order", 10)
    max_order = min(max_order, max_order_cfg)
    
    # pyroomacoustics takes `materials` as pra.Material(energy_absorption)
    mat = pra.Material(absorption)
    
    room = pra.ShoeBox(room_dim, fs=sr, materials=mat, max_order=max_order)
    
    # Place source deterministically
    # Keep it at least 1m from walls if possible
    margin = 1.0
    src_x = rng.uniform(margin, max(margin + 0.1, dim_x - margin))
    src_y = rng.uniform(margin, max(margin + 0.1, dim_y - margin))
    src_z = rng.uniform(1.0, 2.0)  # typical speaking height
    room.add_source([src_x, src_y, src_z])
    
    # Place mic deterministically
    mic_x = rng.uniform(margin, max(margin + 0.1, dim_x - margin))
    mic_y = rng.uniform(margin, max(margin + 0.1, dim_y - margin))
    mic_z = rng.uniform(1.0, 2.0)
    
    mic_loc = np.c_[[mic_x, mic_y, mic_z]]
    room.add_microphone_array(pra.MicrophoneArray(mic_loc, room.fs))
    
    # Compute RIR
    room.compute_rir()
    rir = room.rir[0][0]
    
    try:
        actual_rt60 = float(room.measure_rt60()[0][0])
    except Exception:
        actual_rt60 = 0.0
    
    metadata = {
        "profile": profile,
        "seed": seed,
        "dimensions": [float(dim_x), float(dim_y), float(dim_z)],
        "absorption": float(absorption),
        "target_rt60": float(target_rt60),
        "actual_rt60": actual_rt60,
        "max_order": int(max_order),
        "source_pos": [float(src_x), float(src_y), float(src_z)],
        "mic_pos": [float(mic_x), float(mic_y), float(mic_z)],
    }
    
    return rir, metadata
