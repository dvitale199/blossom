from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars like NEXT_PUBLIC_*
    )

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # App
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
