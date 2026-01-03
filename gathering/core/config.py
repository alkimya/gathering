"""
Configuration management for the GatheRing framework.
Loads settings from environment variables with validation.
"""

from pathlib import Path
from typing import Optional, Literal
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAIConfig(BaseModel):
    """OpenAI provider configuration."""

    api_key: Optional[SecretStr] = None
    org_id: Optional[str] = None
    default_model: str = "gpt-4"


class AnthropicConfig(BaseModel):
    """Anthropic provider configuration."""

    api_key: Optional[SecretStr] = None
    default_model: str = "claude-3-opus-20240229"


class OllamaConfig(BaseModel):
    """Ollama provider configuration."""

    base_url: str = "http://localhost:11434"
    default_model: str = "llama2"


class SecurityConfig(BaseModel):
    """Security-related configuration."""

    secret_key: SecretStr = Field(default_factory=lambda: SecretStr("dev-secret-key-change-me"))
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    max_tokens_per_request: int = Field(default=4000, ge=100, le=100000)


class FileStorageConfig(BaseModel):
    """File storage configuration."""

    base_path: Path = Field(default=Path("/tmp/gathering"))
    max_size_mb: int = Field(default=100, ge=1, le=10000)

    @field_validator("base_path", mode="before")
    @classmethod
    def validate_path(cls, v):
        """Ensure base_path is a Path object."""
        if isinstance(v, str):
            return Path(v)
        return v


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: Optional[str] = None
    redis_url: Optional[str] = None


class Settings(BaseSettings):
    """
    Main settings class that loads configuration from environment variables.

    Usage:
        from gathering.core.config import get_settings
        settings = get_settings()
        api_key = settings.openai.api_key.get_secret_value()
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Environment
    gathering_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # LLM Providers
    openai_api_key: Optional[SecretStr] = None
    openai_org_id: Optional[str] = None
    openai_default_model: str = "gpt-4"

    anthropic_api_key: Optional[SecretStr] = None
    anthropic_default_model: str = "claude-3-opus-20240229"

    deepseek_api_key: Optional[SecretStr] = None
    deepseek_default_model: str = "deepseek-chat"

    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama2"

    # Security
    secret_key: SecretStr = Field(default_factory=lambda: SecretStr("dev-secret-key-change-me"))
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    max_tokens_per_request: int = Field(default=4000, ge=100, le=100000)
    disable_auth: bool = Field(default=False, description="Disable authentication (dev only)")

    # File Storage
    file_storage_base_path: Path = Field(default=Path("/tmp/gathering"))
    file_storage_max_size_mb: int = Field(default=100, ge=1, le=10000)

    # Database
    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    # Web Server
    host: str = "0.0.0.0"
    port: int = 5000
    workers: int = 4
    cors_origins: str = "http://localhost:3000,http://localhost:5000"

    # Testing
    use_mock_providers: bool = True
    test_api_key: str = "test-key-for-testing-only"

    @property
    def openai(self) -> OpenAIConfig:
        """Get OpenAI configuration."""
        return OpenAIConfig(
            api_key=self.openai_api_key,
            org_id=self.openai_org_id,
            default_model=self.openai_default_model,
        )

    @property
    def anthropic(self) -> AnthropicConfig:
        """Get Anthropic configuration."""
        return AnthropicConfig(
            api_key=self.anthropic_api_key,
            default_model=self.anthropic_default_model,
        )

    @property
    def ollama(self) -> OllamaConfig:
        """Get Ollama configuration."""
        return OllamaConfig(
            base_url=self.ollama_base_url,
            default_model=self.ollama_default_model,
        )

    @property
    def security(self) -> SecurityConfig:
        """Get security configuration."""
        return SecurityConfig(
            secret_key=self.secret_key,
            rate_limit_per_minute=self.rate_limit_per_minute,
            max_tokens_per_request=self.max_tokens_per_request,
        )

    @property
    def file_storage(self) -> FileStorageConfig:
        """Get file storage configuration."""
        return FileStorageConfig(
            base_path=self.file_storage_base_path,
            max_size_mb=self.file_storage_max_size_mb,
        )

    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration."""
        return DatabaseConfig(
            url=self.database_url,
            redis_url=self.redis_url,
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.gathering_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.gathering_env == "development"

    def get_llm_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific LLM provider."""
        if provider == "openai" and self.openai_api_key:
            return self.openai_api_key.get_secret_value()
        elif provider == "anthropic" and self.anthropic_api_key:
            return self.anthropic_api_key.get_secret_value()
        elif provider == "deepseek" and self.deepseek_api_key:
            return self.deepseek_api_key.get_secret_value()
        return None

    def validate_for_production(self) -> list[str]:
        """Validate settings for production use. Returns list of issues."""
        issues = []

        if self.is_production:
            if self.debug:
                issues.append("DEBUG should be False in production")

            secret = self.secret_key.get_secret_value()
            if secret == "dev-secret-key-change-me":
                issues.append("SECRET_KEY must be changed from default in production")
            elif len(secret) < 32:
                issues.append("SECRET_KEY should be at least 32 characters")

            if self.disable_auth:
                issues.append("DISABLE_AUTH cannot be True in production")

            if not self.openai_api_key and not self.anthropic_api_key:
                issues.append("At least one LLM provider API key must be configured")

            # Warn about localhost CORS in production
            if "localhost" in self.cors_origins:
                issues.append("CORS_ORIGINS should not contain localhost in production")

        return issues

    def require_production_ready(self) -> None:
        """
        Validate and raise error if settings are not production-ready.
        Call this at application startup in production.
        """
        issues = self.validate_for_production()
        if issues:
            raise ValueError(
                "Configuration not production-ready:\n" +
                "\n".join(f"  - {issue}" for issue in issues)
            )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    Call get_settings.cache_clear() to reload settings.
    """
    return Settings()


def reload_settings() -> Settings:
    """Force reload of settings (clears cache)."""
    get_settings.cache_clear()
    return get_settings()
