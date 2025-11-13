"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "sqlite:///./releaseguard.db"
    debug: bool = False

    # Scoring thresholds
    approve_threshold: float = 30.0  # 0-29 = APPROVE
    warn_threshold: float = 60.0  # 30-59 = WARN, 60+ = BLOCK

    model_config = {"env_prefix": "RELEASEGUARD_"}


settings = Settings()
