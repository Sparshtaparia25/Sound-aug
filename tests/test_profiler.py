import os
import json
import numpy as np
import soundfile as sf
from backend.dsp.profiler import profile_audio

# Generate a dummy audio file (1s sine wave + some noise)
sr = 16000
duration = 1.0
t = np.linspace(0, duration, int(sr * duration), False)
# 440Hz sine wave (voiced speech proxy)
signal = 0.5 * np.sin(2 * np.pi * 440 * t)
# Add silence at the end
signal[int(0.8*sr):] = 0
# Add some white noise
noise = np.random.normal(0, 0.01, len(signal))
audio = signal + noise

sf.write('test_audio.wav', audio, sr)

# Profile the audio
import traceback
try:
    profile = profile_audio('test_audio.wav')
    print(profile.model_dump_json(indent=2))
except Exception as e:
    print(f"Error profiling audio:")
    traceback.print_exc()
