from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 7
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env")

settings = Settings()