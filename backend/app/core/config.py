from functools import lru_cache
from typing import Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "SMARTBUS Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # PostgreSQL Database Configuration
    POSTGRES_USER: str = "smartbus_user"
    POSTGRES_PASSWORD: str = "smartbus_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "smartbus_db"
    DATABASE_URL: str = (
        "postgresql+asyncpg://smartbus_user:smartbus_password@localhost:5432/smartbus_db"
    )

    # Database connection pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Firebase Authentication Configuration
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None

    # Geofencing Configuration
    DEFAULT_GEOFENCE_RADIUS_METERS: float = 100.0
    BUS_NEARBY_RADIUS_METERS: float = 500.0
    BUS_ARRIVAL_RADIUS_METERS: float = 100.0

    # Basic ETA Engine Configuration (baseline deterministic speed in m/s)
    DEFAULT_ETA_SPEED_MPS: float = 8.0

    # Push Notification & FCM Configuration
    FCM_ENABLED: bool = True
    NOTIFICATION_DEDUPE_TTL_SECONDS: int = 1800

    @field_validator("DEFAULT_ETA_SPEED_MPS")
    @classmethod
    def validate_eta_speed(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("DEFAULT_ETA_SPEED_MPS must be strictly greater than 0")
        return v

    @field_validator("BUS_NEARBY_RADIUS_METERS", "BUS_ARRIVAL_RADIUS_METERS")
    @classmethod
    def validate_positive_radius(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Geofence radii must be strictly greater than 0")
        return v

    @model_validator(mode="after")
    def validate_geofence_radii_relationship(self) -> "Settings":
        if self.BUS_NEARBY_RADIUS_METERS <= self.BUS_ARRIVAL_RADIUS_METERS:
            raise ValueError(
                f"BUS_NEARBY_RADIUS_METERS ({self.BUS_NEARBY_RADIUS_METERS}) must be strictly "
                f"greater than BUS_ARRIVAL_RADIUS_METERS ({self.BUS_ARRIVAL_RADIUS_METERS})"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached accessor for application settings instance."""
    return Settings()


settings = get_settings()
