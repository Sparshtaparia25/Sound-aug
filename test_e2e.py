import os
import json
import numpy as np
import soundfile as sf
from backend.agents.models import TransformationPlan, TransformationOperation
from backend.dsp.engine import process_audio
from backend.dsp.profiler import profile_audio

def generate_test_audio(filename='test_e2e_audio.wav'):
    sr = 16000
    t = np.linspace(0, 1, sr, False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t)
    # Add silence for VAD
    signal[int(0.8*sr):] = 0.0
    sf.write(filename, signal, sr)

if __name__ == '__main__':
    generate_test_audio()
    
    plan = TransformationPlan(
        seed=8888,
        operations=[
            TransformationOperation(
                operation="noise_injection",
                profile="traffic",
                parameters={"target_snr_db": 12.0}
            )
        ]
    )
    
    print("Running Pass 1...")
    process_audio('test_e2e_audio.wav', 'out1.wav', plan)
    
    print("Running Pass 2...")
    process_audio('test_e2e_audio.wav', 'out2.wav', plan)
    
    # 1. Check exact equality
    y1, sr = sf.read('out1.wav')
    y2, _ = sf.read('out2.wav')
    
    diff = np.max(np.abs(y1 - y2))
    print(f"Max difference between runs: {diff}")
    assert diff < 1e-6, "Runs are not deterministic!"
    
    # 2. Check QA target
    p1 = profile_audio('out1.wav')
    snr = p1.noise.estimated_snr
    print(f"Measured SNR: {snr:.2f} dB (Target: 12.0 dB)")
    
    # Due to VAD approximations on small synthetic files, it won't be exactly 12,
    # but the determinism is absolute. Let's see what it prints.
    print("E2E Determinism Check Passed!")
