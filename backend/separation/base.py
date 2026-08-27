import numpy as np
from abc import ABC, abstractmethod

class AudioSeparator(ABC):
    @abstractmethod
    def separate(self, audio: np.ndarray, sr: int, target: str) -> np.ndarray:
        """
        Separates the target stem from the mixed audio.
        :param audio: The input audio mixed signal.
        :param sr: The sample rate.
        :param target: The target stem (e.g. 'vocals_only', 'speech_isolation').
        :return: The isolated audio array.
        """
        pass
