from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    internal_auth_secret: str
    access_token_expire_minutes: int = 60 * 24 * 7

    debug: bool = False

    deepseek_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-v4-pro"

    anime_api_base_url: str = "https://api.tenrai.org/v1"
    anime_api_fallback_url: str = "https://api.jikan.moe/v4"

    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
