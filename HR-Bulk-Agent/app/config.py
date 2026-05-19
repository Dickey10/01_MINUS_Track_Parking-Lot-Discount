from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: str = "data/hr_agent.db"
    allow_live_connectors: bool = False
    secret_key: str = "local-dev-secret"

    gift24_base_url: str = "https://localhost:8888"
    gift24_client_id: str = ""
    gift24_client_secret: str = ""

    workd_base_url: str = ""
    workd_api_key: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-5.1"

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)


settings = Settings()

