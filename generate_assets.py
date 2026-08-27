import os
import numpy as np
import soundfile as sf

def generate_noise(output_path, duration=10.0, sr=16000, noise_type='white'):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    if noise_type == 'white':
        noise = np.random.normal(0, 1, len(t))
    elif noise_type == 'pink': # approximation for "traffic"
        # extremely naive pink noise approximation via cumsum
        noise = np.cumsum(np.random.normal(0, 0.1, len(t)))
        # Highpass to avoid DC drift
        from scipy.signal import butter, lfilter
        b, a = butter(1, 20 / (sr / 2), btype='high')
        noise = lfilter(b, a, noise)
    
    # Normalize
    noise = noise / np.max(np.abs(noise))
    sf.write(output_path, noise, sr)

def generate_rir(output_path, rt60=2.0, sr=16000):
    # Model: direct sound + exponential decay noise
    duration = max(rt60, 0.1)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # Envelope: exp(-t * lambda) where lambda gives -60dB at rt60
    # -60 dB is a factor of 10^(-60/20) = 0.001
    # exp(-rt60 * lam) = 0.001 -> lam = -ln(0.001) / rt60
    lam = -np.log(0.001) / rt60
    envelope = np.exp(-t * lam)
    
    # Dense late reverberation (noise)
    dense_reverb = np.random.normal(0, 1, len(t)) * envelope
    
    # Direct sound + early reflections (spikes)
    dense_reverb[0] = 100.0 # direct
    dense_reverb[int(0.02 * sr)] = 50.0 # early reflection 1 at 20ms
    dense_reverb[int(0.05 * sr)] = 25.0 # early reflection 2 at 50ms
    
    # Normalize
    rir = dense_reverb / np.max(np.abs(dense_reverb))
    sf.write(output_path, rir, sr)

if __name__ == '__main__':
    base_dir = "backend/dsp/assets"
    
    noise_dir = os.path.join(base_dir, "noise", "traffic")
    os.makedirs(noise_dir, exist_ok=True)
    generate_noise(os.path.join(noise_dir, "synthetic_01.wav"), noise_type='pink')
    
    rir_dir = os.path.join(base_dir, "rir", "auditorium")
    os.makedirs(rir_dir, exist_ok=True)
    generate_rir(os.path.join(rir_dir, "synthetic_01.wav"), rt60=2.5)
    
    print("Test assets generated.")
