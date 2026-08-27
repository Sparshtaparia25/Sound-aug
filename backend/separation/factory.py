from backend.separation.base import AudioSeparator
from backend.separation.demucs_separator import DemucsSeparator

_separator_instance = None

def get_separator() -> AudioSeparator:
    global _separator_instance
    if _separator_instance is None:
        _separator_instance = DemucsSeparator()
    return _separator_instance
