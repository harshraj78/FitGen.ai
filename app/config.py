from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitGen AI"
    app_env: str = "development"
    database_url: str = "sqlite:///./fitgen.db"
    auto_create_tables: bool | None = None
    allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8010,http://localhost:8010"
    session_ttl_hours: int = 168
    enable_demo_routes: bool | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    llm_provider: str = "groq"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"
    whatsapp_automation_enabled: bool = False
    payment_links_enabled: bool = False
    booking_base_url: str | None = None
    payment_link_base_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def demo_routes_enabled(self) -> bool:
        if self.enable_demo_routes is not None:
            return self.enable_demo_routes
        return self.app_env.lower() not in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
