import os
import json
from backend.agents.planner_agent import plan_transformation
from backend.agents.models import (
    Intent, AudioProfile, FileInfo, SignalQuality, NoiseProfile,
    TemporalProfile, SpectralProfile, CepstralProfile, ProsodyProfile,
    AcousticEnvironment, Distribution
)

# Dummy distribution
dummy_dist = Distribution(mean=0.0, median=0.0, std=0.0, p10=0.0, p90=0.0)

profile = AudioProfile(
    file_info=FileInfo(format="wav", duration=10.0, sample_rate=44100, channels=1),
    signal_quality=SignalQuality(peak=-3.0, rms=-12.0, lufs=-14.0, crest_factor=9.0, dynamic_range=60.0, clipping_ratio=0.0, dc_offset=0.0),
    noise=NoiseProfile(estimated_snr=40.0, noise_floor=-60.0, snr_confidence=1.0),
    temporal=TemporalProfile(speech_ratio=0.8, silence_ratio=0.2),
    spectral=SpectralProfile(
        spectral_centroid=dummy_dist,
        spectral_bandwidth=dummy_dist,
        spectral_rolloff=dummy_dist,
        spectral_flatness=dummy_dist,
        zero_crossing_rate=0.05
    ),
    cepstral=CepstralProfile(mfcc_mean=[0.0]*13, mfcc_std=[0.1]*13),
    prosody=ProsodyProfile(voiced_ratio=0.6),
    environment=AcousticEnvironment(reverberation_estimate=0.1)
)

intent = Intent(
    target_environment="auditorium",
    noise={"noise_type": "", "target_snr_db": 10.0},
    channel={"channel_type": ""},
    prosody={"pitch_semitones": 0.0, "time_stretch_rate": 1.0},
    loudness={"target_lufs": -23.0},
    source_separation={"required": False, "target": "vocals_only"}
)

try:
    print("Running planner agent...")
    plan = plan_transformation(intent, profile)
    print("\nSUCCESS! Generated Plan:")
    print(plan.model_dump_json(indent=2))
except Exception as e:
    print(f"\nFAILED: {e}")
