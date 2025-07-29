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
    
    # Caching
    redis_url: Optional[str] = None
    cache_ttl: int = 300  # 5 minutes default cache TTL
    enable_query_cache: bool = True
    
    def validate_secret_key(self):
        """Validate that secret key is changed from default"""
        if self.secret_key == "your-secret-key-change-this-in-production":
            import warnings
            warnings.warn(
                "⚠️  WARNING: Using default SECRET_KEY in production is insecure! "
                "Please set a secure SECRET_KEY environment variable.",
                UserWarning
            )
    
    def get_masked_secret(self) -> str:
        """Return masked secret key for logging"""
        if len(self.secret_key) > 8:
            return f"{self.secret_key[:4]}{'*' * (len(self.secret_key) - 8)}{self.secret_key[-4:]}"
        return "****"
    
    def get_masked_database_url(self) -> str:
        """Return masked database URL for logging"""
        import re
        # Mask password in database URL
        masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', self.database_url)
        return masked_url
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
# Validate security settings on startup
settings.validate_secret_key()
