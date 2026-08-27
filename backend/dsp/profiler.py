import librosa
import numpy as np
import pyloudnorm as pyln
from backend.agents.models import (
    AudioProfile, Distribution, FileInfo, SignalQuality, 
    NoiseProfile, TemporalProfile, SpectralProfile, 
    CepstralProfile, ProsodyProfile, AcousticEnvironment
)

def calc_dist(arr: np.ndarray) -> Distribution:
    if len(arr) == 0:
        return Distribution(mean=0.0, median=0.0, std=0.0, p10=0.0, p90=0.0)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return Distribution(mean=0.0, median=0.0, std=0.0, p10=0.0, p90=0.0)
    return Distribution(
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        std=float(np.std(arr)),
        p10=float(np.percentile(arr, 10)),
        p90=float(np.percentile(arr, 90))
    )

def profile_audio(file_path: str) -> AudioProfile:
    """Analyze the input audio using rigorous DSP metrics."""
    # Load audio
    y, sr = librosa.load(file_path, sr=None, mono=False)
    
    # File Info
    channels = y.shape[0] if y.ndim > 1 else 1
    y_mono = librosa.to_mono(y) if y.ndim > 1 else y
    duration = librosa.get_duration(y=y_mono, sr=sr)
    
    file_info = FileInfo(
        format=file_path.split('.')[-1].upper(),
        duration=duration,
        sample_rate=sr,
        channels=channels,
        bit_depth=16 # Defaulting for now, soundfile could provide this
    )
    
    # VAD & Temporal
    # Split audio into non-mute (speech) and mute (silence/noise)
    non_mute_intervals = librosa.effects.split(y_mono, top_db=30)
    
    speech_samples = 0
    noise_frames_list = []
    
    last_end = 0
    for start, end in non_mute_intervals:
        speech_samples += (end - start)
        if start > last_end:
            noise_frames_list.append(y_mono[last_end:start])
        last_end = end
        
    if last_end < len(y_mono):
        noise_frames_list.append(y_mono[last_end:])
        
    speech_ratio = speech_samples / len(y_mono) if len(y_mono) > 0 else 0
    silence_ratio = 1.0 - speech_ratio
    
    temporal = TemporalProfile(
        speech_ratio=float(speech_ratio),
        silence_ratio=float(silence_ratio)
    )
    
    # Noise & SNR
    signal_power = np.mean(y_mono**2)
    if len(noise_frames_list) > 0:
        noise_audio = np.concatenate(noise_frames_list)
        noise_power = np.mean(noise_audio**2)
        noise_floor = float(np.sqrt(noise_power))
        
        if noise_power > 0:
            snr = 10 * np.log10(signal_power / noise_power)
        else:
            snr = 50.0 # High SNR if no noise power
        confidence = float(len(noise_audio) / len(y_mono)) # Higher confidence if we found enough noise regions
    else:
        # No silence found, fallback
        snr = 30.0 
        noise_floor = 1e-4
        confidence = 0.1
        
    noise_profile = NoiseProfile(
        estimated_snr=float(snr),
        noise_floor=noise_floor,
        snr_confidence=confidence
    )
    
    # Signal Quality
    peak = float(np.max(np.abs(y_mono)))
    rms = float(np.sqrt(signal_power))
    crest_factor = peak / rms if rms > 0 else 1.0
    
    # LUFS using pyloudnorm
    meter = pyln.Meter(sr) 
    try:
        lufs = float(meter.integrated_loudness(y_mono))
    except ValueError:
        lufs = -70.0 # fallback for silence
        
    dc_offset = float(np.mean(y_mono))
    clipping_ratio = float(np.sum(np.abs(y_mono) >= 0.99) / len(y_mono))
    # Simple dynamic range estimation
    dynamic_range = float(20 * np.log10(peak / (noise_floor + 1e-9)))

    quality = SignalQuality(
        peak=peak,
        rms=rms,
        lufs=lufs,
        crest_factor=crest_factor,
        dynamic_range=dynamic_range,
        clipping_ratio=clipping_ratio,
        dc_offset=dc_offset
    )
    
    # Spectral
    S, phase = librosa.magphase(librosa.stft(y_mono))
    centroid = librosa.feature.spectral_centroid(S=S)[0]
    bandwidth = librosa.feature.spectral_bandwidth(S=S)[0]
    rolloff = librosa.feature.spectral_rolloff(S=S)[0]
    flatness = librosa.feature.spectral_flatness(S=S)[0]
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y_mono)[0]))
    
    spectral = SpectralProfile(
        spectral_centroid=calc_dist(centroid),
        spectral_bandwidth=calc_dist(bandwidth),
        spectral_rolloff=calc_dist(rolloff),
        spectral_flatness=calc_dist(flatness),
        zero_crossing_rate=zcr
    )
    
    # Cepstral
    mfccs = librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=13)
    mfcc_mean = [float(np.mean(m)) for m in mfccs]
    mfcc_std = [float(np.std(m)) for m in mfccs]
    
    cepstral = CepstralProfile(
        mfcc_mean=mfcc_mean,
        mfcc_std=mfcc_std
    )
    
    # Prosody (F0)
    f0, voiced_flag, voiced_probs = librosa.pyin(y_mono, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
    
    f0_dist = calc_dist(f0[voiced_flag]) if np.any(voiced_flag) else None
    v_ratio = float(np.sum(voiced_flag) / len(voiced_flag)) if len(voiced_flag) > 0 else 0.0
    
    prosody = ProsodyProfile(
        f0=f0_dist,
        voiced_ratio=v_ratio
    )
    
    # Acoustic Environment
    # Naive reverb estimation: finding decay rate in non-speech sections. 
    # For phase 1, keep simple placeholder.
    environment = AcousticEnvironment(
        reverberation_estimate=0.1
    )
    
    return AudioProfile(
        file_info=file_info,
        signal_quality=quality,
        noise=noise_profile,
        temporal=temporal,
        spectral=spectral,
        cepstral=cepstral,
        prosody=prosody,
        environment=environment
    )
