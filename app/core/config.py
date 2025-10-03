from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Saga Express"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://saga_user:saga_password@localhost:5432/saga_db"
    
    # Kafka/Redpanda
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:19092"
    
    # API
    API_PREFIX: str = "/api/v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
