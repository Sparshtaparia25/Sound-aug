import os
import random
import numpy as np
import librosa
import soundfile as sf
import scipy.signal
from pedalboard import Pedalboard, HighpassFilter, LowpassFilter, Gain

from backend.agents.models import TransformationPlan
from backend.dsp.registry import validate_operation

ASSET_DIR = "backend/dsp/assets"

def process_audio(input_path: str, output_path: str, plan: TransformationPlan):
    """Executes deterministic audio transformations based on the registry."""
    
    # Set seed for deterministic reproducibility
    np.random.seed(plan.seed)
    random.seed(plan.seed)
    
    # Load audio
    y, sr = librosa.load(input_path, sr=None)
    
    for op in plan.operations:
        # Validate operation against registry
        validate_operation(op.operation, op.profile, op.parameters)
        
        # 1. RIR Convolution
        if op.operation == "rir_convolution":
            wet_mix = op.parameters.get("wet_mix", 0.5)
            rir_path = os.path.join(ASSET_DIR, "rir", op.profile, "synthetic_01.wav")
            if os.path.exists(rir_path):
                rir, _ = librosa.load(rir_path, sr=sr)
                convolved = scipy.signal.fftconvolve(y, rir, mode='full')
                # Match length back to original (simplification for early reflections focused mixing)
                convolved = convolved[:len(y)]
                # Mix dry/wet
                y = (1.0 - wet_mix) * y + wet_mix * convolved
            else:
                print(f"Warning: RIR asset {rir_path} not found.")

        # 2. Noise Injection (RMS Calibrated)
        elif op.operation == "noise_injection":
            target_snr = op.parameters.get("target_snr_db", 10.0)
            noise_path = os.path.join(ASSET_DIR, "noise", op.profile, "synthetic_01.wav")
            if os.path.exists(noise_path):
                noise, _ = librosa.load(noise_path, sr=sr)
                
                # Match noise length to signal
                if len(noise) < len(y):
                    repeats = int(np.ceil(len(y) / len(noise)))
                    noise = np.tile(noise, repeats)
                noise = noise[:len(y)]
                
                # Calculate required gain for target SNR
                ps = np.mean(y**2)
                pn = np.mean(noise**2)
                if pn > 0:
                    scale = np.sqrt(ps / (pn * (10 ** (target_snr / 10.0))))
                    y = y + scale * noise
            else:
                print(f"Warning: Noise asset {noise_path} not found.")

        # 3. Prosodic - Pitch Shift
        elif op.operation == "pitch_shift":
            semitones = op.parameters.get("semitones", 0.0)
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
            
        # 4. Prosodic - Time Stretch
        elif op.operation == "time_stretch":
            rate = op.parameters.get("rate", 1.0)
            y = librosa.effects.time_stretch(y, rate=rate)
            
        # 5. EQ / Bandpass
        elif op.operation == "eq":
            hp = op.parameters.get("highpass_freq", 20.0)
            lp = op.parameters.get("lowpass_freq", sr / 2.0 - 100)
            board = Pedalboard([HighpassFilter(hp), LowpassFilter(lp)])
            y_pb = np.expand_dims(y, axis=0) if y.ndim == 1 else y.T
            effected = board(y_pb, sr, reset=False)
            y = effected[0] if effected.ndim == 2 and effected.shape[0] == 1 else effected.T
            
        # 6. Gain
        elif op.operation == "gain":
            gain_db = op.parameters.get("gain_db", 0.0)
            board = Pedalboard([Gain(gain_db=gain_db)])
            y_pb = np.expand_dims(y, axis=0) if y.ndim == 1 else y.T
            effected = board(y_pb, sr, reset=False)
            y = effected[0] if effected.ndim == 2 and effected.shape[0] == 1 else effected.T
            
    # Prevent hard clipping by normalizing if peak > 1.0
    peak = np.max(np.abs(y))
    if peak > 1.0:
        y = y / peak

    # Save output
    sf.write(output_path, y, sr)
    
    return True
