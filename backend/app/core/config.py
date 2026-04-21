from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Podcast Prompt API"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./podcast.db"
    postgres_url: str | None = None
    cors_origins: str = "http://localhost:5173"
    tts_provider: str = "dashscope"
    tts_model: str = "cosyvoice-v2"
    dashscope_api_key: str | None = None
    dashscope_base_websocket_api_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    dashscope_default_male_voice: str = "loongdavid_v2"
    dashscope_default_female_voice: str = "longanwen"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def effective_database_url(self) -> str:
        if self.postgres_url:
            return self.postgres_url
        return self.database_url


settings = Settings()
