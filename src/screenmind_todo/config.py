from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="ScreenMind Todo", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./screenmind.db", alias="DATABASE_URL")
    capture_interval_seconds: int = Field(default=15, alias="CAPTURE_INTERVAL_SECONDS")
    ocr_min_text_length: int = Field(default=20, alias="OCR_MIN_TEXT_LENGTH")
    task_cooldown_minutes: int = Field(default=30, alias="TASK_COOLDOWN_MINUTES")
    active_window_only: bool = Field(default=False, alias="ACTIVE_WINDOW_ONLY")
    save_screenshots: bool = Field(default=False, alias="SAVE_SCREENSHOTS")
    captures_dir: Path = Field(default=Path("./captures"), alias="CAPTURES_DIR")
    ollama_enabled: bool = Field(default=False, alias="OLLAMA_ENABLED")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

