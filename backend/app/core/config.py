import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SMARTBUS Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database Configuration (PostgreSQL + PostGIS)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "smartbus_db"
    DATABASE_URL: Optional[str] = None

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    REDIS_MOCK_MODE: bool = False

    # Firebase Configuration
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = "firebase-service-account.json"
    FIREBASE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    FIREBASE_MOCK_MODE: bool = False

    # Domain Restriction
    STUDENT_REQUIRED_DOMAIN: str = "sode-edu.in"

    # Timezone
    TIMEZONE: str = "Asia/Kolkata"

    # Predefined Admins
    ADMIN1_EMAIL: str = "admin1@sode-edu.in"
    ADMIN1_PASSWORD: str = "Admin1_Password123!"
    ADMIN2_EMAIL: str = "admin2@sode-edu.in"
    ADMIN2_PASSWORD: str = "Admin2_Password123!"
    ADMIN3_EMAIL: str = "admin3@sode-edu.in"
    ADMIN3_PASSWORD: str = "Admin3_Password123!"

    # Predefined Drivers
    DRIVER1_EMAIL: str = "driver1@sode-edu.in"
    DRIVER1_PASSWORD: str = "Driver1_Password123!"
    DRIVER2_EMAIL: str = "driver2@sode-edu.in"
    DRIVER2_PASSWORD: str = "Driver2_Password123!"
    DRIVER3_EMAIL: str = "driver3@sode-edu.in"
    DRIVER3_PASSWORD: str = "Driver3_Password123!"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def get_redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

settings = Settings()
