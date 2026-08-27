import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # Resource Limits
    MAX_AUDIO_FILE_SIZE_MB: int = int(os.getenv("MAX_AUDIO_FILE_SIZE_MB", 20))
    MAX_AUDIO_DURATION_SECONDS: int = int(os.getenv("MAX_AUDIO_DURATION_SECONDS", 60))
    MAX_BATCH_FILES: int = int(os.getenv("MAX_BATCH_FILES", 20))
    MAX_BATCH_DURATION_SECONDS: int = int(os.getenv("MAX_BATCH_DURATION_SECONDS", 600))
    
    # Decoding / Memory Limits
    MAX_SAMPLE_RATE: int = int(os.getenv("MAX_SAMPLE_RATE", 96000))
    MAX_CHANNELS: int = int(os.getenv("MAX_CHANNELS", 2))
    
    # Logic Limits
    MAX_PLAN_RETRIES: int = int(os.getenv("MAX_PLAN_RETRIES", 3))
    
    # Storage
    STORAGE_ROOT: str = os.getenv("STORAGE_ROOT", "storage")
    ARTIFACT_RETENTION_DAYS: int = int(os.getenv("ARTIFACT_RETENTION_DAYS", 7))

    class Config:
        env_file = ".env"
        extra = "ignore"

config = Settings()
