from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Rate Limiter API"
    debug: bool = False

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = 20

    # Default rate limit (can be overridden per route)
    default_requests: int = 100
    default_window_seconds: int = 60
    default_algorithm: str = "token_bucket"

    # Whitelist — comma-separated IPs that bypass rate limiting
    whitelisted_ips: list[str] = Field(default=["127.0.0.1", "::1"])

    # Prometheus
    metrics_enabled: bool = True


settings = Settings()
