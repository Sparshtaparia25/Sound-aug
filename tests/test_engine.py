import os
import json
from backend.agents.models import TransformationPlan, TransformationOperation
from backend.dsp.profiler import profile_audio
from backend.dsp.engine import process_audio

# Create dummy input if it doesn't exist
if not os.path.exists('test_audio.wav'):
    import soundfile as sf
    import numpy as np
    sr = 16000
    t = np.linspace(0, 1, sr, False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t)
    signal[int(0.8*sr):] = 0.0 # 200ms of silence
    sf.write('test_audio.wav', signal, sr)

print("--- BEFORE PROFILING ---")
before_profile = profile_audio('test_audio.wav')
print(f"SNR: {before_profile.noise.estimated_snr:.2f} dB")

# Create a deterministic plan
plan = TransformationPlan(
    seed=12345,
    operations=[
        TransformationOperation(
            operation="noise_injection",
            profile="traffic",
            parameters={"target_snr_db": 10.0}
        )
    ]
)

print("\n--- EXECUTING ENGINE ---")
process_audio('test_audio.wav', 'test_audio_augmented.wav', plan)

print("\n--- AFTER PROFILING ---")
after_profile = profile_audio('test_audio_augmented.wav')
print(f"SNR: {after_profile.noise.estimated_snr:.2f} dB")
