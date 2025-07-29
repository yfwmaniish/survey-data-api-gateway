from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://username:password@localhost/survey_db"
    database_url_async: Optional[str] = None
    
    # JWT
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_title: str = "Survey Data API Gateway"
    api_version: str = "1.0.0"
    debug: bool = True
    
    # Limits
    rate_limit: int = 100
    max_query_timeout: int = 30
    max_result_rows: int = 10000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
