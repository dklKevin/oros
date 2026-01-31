"""
Configuration management for Biomedical Knowledge Platform.

Uses pydantic-settings for environment variable loading with validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Environment
    # =========================================================================
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = Field(
        default="postgresql://biomedical:changeme@localhost:5432/knowledge_platform",
        description="PostgreSQL connection URL. MUST be configured via environment variable in production.",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure production doesn't use default credentials."""
        import os
        env = os.environ.get("ENVIRONMENT", "development")
        if env == "production" and "changeme" in v:
            raise ValueError(
                "Default database credentials detected in production. "
                "Set DATABASE_URL environment variable with secure credentials."
            )
        return v
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5, le=300)
    database_echo: bool = Field(default=False, description="Echo SQL statements")

    # =========================================================================
    # AWS Configuration
    # =========================================================================
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_endpoint_url: str | None = Field(
        default=None,
        description="LocalStack endpoint for local development",
    )
    use_localstack: bool = False

    # =========================================================================
    # S3 Configuration
    # =========================================================================
    s3_bucket_raw_documents: str = "biomedical-raw-documents"
    s3_bucket_processed_chunks: str = "biomedical-processed-chunks"

    # =========================================================================
    # SQS Configuration
    # =========================================================================
    sqs_ingestion_queue_url: str | None = None
    sqs_dlq_url: str | None = None
    sqs_embedding_queue_url: str | None = None

    # =========================================================================
    # Bedrock Configuration
    # =========================================================================
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v1"
    bedrock_llm_model_id_simple: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_llm_model_id_complex: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    # =========================================================================
    # Logging
    # =========================================================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # =========================================================================
    # API Configuration
    # =========================================================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_title: str = "Biomedical Knowledge Platform"
    api_version: str = "1.0.0"

    # =========================================================================
    # Ingestion Configuration
    # =========================================================================
    ingestion_batch_size: int = Field(default=10, ge=1, le=100)
    ingestion_max_retries: int = Field(default=3, ge=1, le=10)
    ingestion_visibility_timeout: int = Field(default=300, ge=30, le=43200)

    # =========================================================================
    # Chunking Configuration
    # =========================================================================
    chunk_max_tokens: int = Field(default=512, ge=100, le=2000)
    chunk_overlap_tokens: int = Field(default=200, ge=0, le=500)

    # =========================================================================
    # Retrieval Configuration
    # =========================================================================
    retrieval_default_limit: int = Field(default=10, ge=1, le=100)
    retrieval_max_limit: int = Field(default=100, ge=10, le=1000)
    retrieval_cache_ttl: int = Field(default=3600, ge=0, le=86400)

    # =========================================================================
    # Search Configuration
    # =========================================================================
    search_vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    search_keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    rate_limit_search_per_minute: int = Field(default=100, ge=1)
    rate_limit_chat_per_minute: int = Field(default=20, ge=1)

    # =========================================================================
    # Observability
    # =========================================================================
    enable_xray_tracing: bool = False
    metrics_enabled: bool = True

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("search_vector_weight", "search_keyword_weight")
    @classmethod
    def validate_weights(cls, v: float) -> float:
        """Ensure weights are between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Weight must be between 0 and 1")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def async_database_url(self) -> str:
        """Get async-compatible database URL."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
