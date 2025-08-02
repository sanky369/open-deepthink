"""
Application configuration management.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
import structlog

logger = structlog.get_logger()


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Keys
    gemini_api_key: str
    
    # Application Configuration
    app_name: str = "open-deep-think"
    debug: bool = False
    
    # Pipeline Defaults
    default_n_paths: int = 8
    default_max_iterations: int = 1
    default_top_k: int = 3
    
    # Rate Limiting
    max_requests_per_minute: int = 60
    
    # Caching
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 900  # 15 minutes
    
    # Timeouts (in seconds)
    gemini_timeout: int = 180
    pipeline_timeout: int = 300
    
    # Logging
    log_level: str = "INFO"
    
    # Model Configuration
    gemini_model_name: str = "gemini-2.5-pro"
    
    # Performance Settings
    max_concurrent_requests: int = 10
    request_queue_size: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def validate_configuration(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If critical configuration is invalid
        """
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        if self.default_n_paths < 1 or self.default_n_paths > 32:
            raise ValueError("default_n_paths must be between 1 and 32")
        
        if self.default_top_k < 1 or self.default_top_k > self.default_n_paths:
            raise ValueError("default_top_k must be between 1 and default_n_paths")
        
        if self.pipeline_timeout < 30:
            raise ValueError("pipeline_timeout must be at least 30 seconds")
        
        logger.info(
            "configuration_validated",
            app_name=self.app_name,
            debug=self.debug,
            default_n_paths=self.default_n_paths,
            pipeline_timeout=self.pipeline_timeout
        )
        
        return True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Application settings instance
    """
    settings = Settings()
    settings.validate_configuration()
    return settings