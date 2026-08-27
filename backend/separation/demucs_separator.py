import numpy as np
import warnings
from backend.separation.base import AudioSeparator

class DemucsSeparator(AudioSeparator):
    def __init__(self):
        try:
            import demucs.api
            self.separator = demucs.api.Separator(model="htdemucs")
        except ImportError:
            self.separator = None
            warnings.warn("Demucs is not installed. Separation will act as a pass-through mock.")

    def separate(self, audio: np.ndarray, sr: int, target: str) -> np.ndarray:
        if self.separator is None:
            return audio
            
        import torch
        # Demucs expects tensor of shape (channels, length)
        if audio.ndim == 1:
            audio_tensor = torch.from_numpy(audio).unsqueeze(0).float()
        else:
            audio_tensor = torch.from_numpy(audio).float()
            
        # Resample to demucs expected sample rate if needed
        original_sr = sr
        # In a real implementation we would resample here. For simplicity assume Demucs API handles it.
        
        origin, separated = self.separator.separate_tensor(audio_tensor, sr)
        
        # 'htdemucs' returns dict with 'vocals', 'drums', 'bass', 'other'
        # For speech isolation, 'vocals' is usually the closest.
        if target in ["vocals_only", "speech_isolation"]:
            vocals_tensor = separated.get("vocals", audio_tensor)
            vocals = vocals_tensor.numpy()
            return vocals[0] if audio.ndim == 1 else vocals
        
        return audio
