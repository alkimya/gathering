"""
Settings API endpoints.
Manages application configuration and API keys.
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# =============================================================================
# Pydantic Schemas
# =============================================================================

class ProviderSettings(BaseModel):
    api_key: Optional[str] = Field(None, description="API key (masked on read)")
    default_model: Optional[str] = None
    base_url: Optional[str] = None
    is_configured: bool = False


class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str = "gathering"
    user: str = ""
    is_connected: bool = False


class ApplicationSettings(BaseModel):
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"


class AllSettings(BaseModel):
    providers: Dict[str, ProviderSettings]
    database: DatabaseSettings
    application: ApplicationSettings


class ProviderUpdate(BaseModel):
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    base_url: Optional[str] = None


class ApplicationUpdate(BaseModel):
    debug: Optional[bool] = None
    log_level: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================

def mask_key(key: Optional[str]) -> Optional[str]:
    """Mask an API key for display."""
    if not key or len(key) < 8:
        return None
    return f"{key[:4]}...{key[-4:]}"


def get_env_file_path() -> Path:
    """Get path to .env file."""
    return Path(__file__).parent.parent.parent.parent / ".env"


def read_env_file() -> Dict[str, str]:
    """Read .env file and return as dict."""
    env_path = get_env_file_path()
    result = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    result[key.strip()] = value.strip()
    return result


def write_env_file(updates: Dict[str, str]):
    """Update .env file with new values."""
    env_path = get_env_file_path()
    lines = []

    # Read existing content
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()

    # Update or append values
    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=')[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add new keys that weren't in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)

    # Also update os.environ for current session
    for key, value in updates.items():
        os.environ[key] = value


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AllSettings)
async def get_settings():
    """Get all application settings."""
    env = read_env_file()

    providers = {
        "anthropic": ProviderSettings(
            api_key=mask_key(os.getenv("ANTHROPIC_API_KEY")),
            default_model=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-5"),
            is_configured=bool(os.getenv("ANTHROPIC_API_KEY")),
        ),
        "openai": ProviderSettings(
            api_key=mask_key(os.getenv("OPENAI_API_KEY")),
            default_model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4"),
            is_configured=bool(os.getenv("OPENAI_API_KEY")),
        ),
        "deepseek": ProviderSettings(
            api_key=mask_key(os.getenv("DEEPSEEK_API_KEY")),
            default_model=os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-coder"),
            is_configured=bool(os.getenv("DEEPSEEK_API_KEY")),
        ),
        "ollama": ProviderSettings(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            default_model=os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2"),
            is_configured=True,  # Ollama is local, always "configured"
        ),
    }

    database = DatabaseSettings(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "gathering"),
        user=os.getenv("DB_USER", ""),
        is_connected=True,  # If we got here, DB is connected
    )

    application = ApplicationSettings(
        environment=os.getenv("GATHERING_ENV", "development"),
        debug=os.getenv("DEBUG", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    return AllSettings(
        providers=providers,
        database=database,
        application=application,
    )


@router.patch("/providers/{provider}", response_model=ProviderSettings)
async def update_provider(provider: str, data: ProviderUpdate):
    """Update provider settings."""
    valid_providers = ["anthropic", "openai", "deepseek", "ollama"]
    if provider not in valid_providers:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    updates = {}
    provider_upper = provider.upper()

    if data.api_key is not None:
        updates[f"{provider_upper}_API_KEY"] = data.api_key

    if data.default_model is not None:
        updates[f"{provider_upper}_DEFAULT_MODEL"] = data.default_model

    if data.base_url is not None:
        if provider == "ollama":
            updates["OLLAMA_BASE_URL"] = data.base_url

    if updates:
        write_env_file(updates)

    # Return updated settings
    return ProviderSettings(
        api_key=mask_key(os.getenv(f"{provider_upper}_API_KEY")),
        default_model=os.getenv(f"{provider_upper}_DEFAULT_MODEL"),
        base_url=os.getenv(f"{provider_upper}_BASE_URL") if provider == "ollama" else None,
        is_configured=bool(os.getenv(f"{provider_upper}_API_KEY")) or provider == "ollama",
    )


@router.patch("/application", response_model=ApplicationSettings)
async def update_application(data: ApplicationUpdate):
    """Update application settings."""
    updates = {}

    if data.debug is not None:
        updates["DEBUG"] = "true" if data.debug else "false"

    if data.log_level is not None:
        if data.log_level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise HTTPException(status_code=400, detail="Invalid log level")
        updates["LOG_LEVEL"] = data.log_level.upper()

    if updates:
        write_env_file(updates)

    return ApplicationSettings(
        environment=os.getenv("GATHERING_ENV", "development"),
        debug=os.getenv("DEBUG", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


@router.post("/providers/{provider}/test")
async def test_provider(provider: str):
    """Test connection to a provider."""
    valid_providers = ["anthropic", "openai", "deepseek", "ollama"]
    if provider not in valid_providers:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    provider_upper = provider.upper()
    api_key = os.getenv(f"{provider_upper}_API_KEY")

    if provider == "ollama":
        # Test Ollama connection
        import httpx
        try:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {
                        "success": True,
                        "message": f"Connected to Ollama. {len(models)} models available.",
                        "models": [m.get("name") for m in models[:5]],
                    }
                else:
                    return {"success": False, "message": f"Ollama returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Could not connect to Ollama: {str(e)}"}

    if not api_key:
        return {"success": False, "message": f"No API key configured for {provider}"}

    # Test API key by making a minimal request
    try:
        if provider == "anthropic":
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return {"success": True, "message": "Anthropic API key is valid"}
                elif response.status_code == 401:
                    return {"success": False, "message": "Invalid API key"}
                else:
                    return {"success": False, "message": f"API returned status {response.status_code}"}

        elif provider == "openai":
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return {"success": True, "message": "OpenAI API key is valid"}
                elif response.status_code == 401:
                    return {"success": False, "message": "Invalid API key"}
                else:
                    return {"success": False, "message": f"API returned status {response.status_code}"}

        elif provider == "deepseek":
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.deepseek.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return {"success": True, "message": "DeepSeek API key is valid"}
                elif response.status_code == 401:
                    return {"success": False, "message": "Invalid API key"}
                else:
                    return {"success": False, "message": f"API returned status {response.status_code}"}

    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}

    return {"success": False, "message": "Provider not supported for testing"}


# Export router
settings_router = router
