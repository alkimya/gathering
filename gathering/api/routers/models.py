"""
Providers, Models, and Personas API endpoints.
Uses PostgreSQL database via DatabaseService.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from gathering.api.dependencies import get_database_service, DatabaseService
from gathering.api.async_db import AsyncDatabaseService, get_async_db


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ProviderBase(BaseModel):
    name: str = Field(..., description="Provider name (e.g., 'anthropic', 'openai')")
    api_base_url: Optional[str] = Field(None, description="API base URL")
    is_local: bool = Field(False, description="Is this a local provider (e.g., Ollama)")


class ProviderCreate(ProviderBase):
    pass


class Provider(ProviderBase):
    id: int
    created_at: Optional[str] = None
    model_count: int = 0

    class Config:
        from_attributes = True


class ModelBase(BaseModel):
    provider_id: int = Field(..., description="Provider foreign key")
    model_name: str = Field(..., description="Full API model name")
    model_alias: Optional[str] = Field(None, description="Display name")
    pricing_in: Optional[float] = Field(None, description="Input price per 1M tokens")
    pricing_out: Optional[float] = Field(None, description="Output price per 1M tokens")
    pricing_cache_read: Optional[float] = Field(None, description="Cache read price")
    pricing_cache_write: Optional[float] = Field(None, description="Cache write price")
    extended_thinking: bool = Field(False, description="Supports extended thinking")
    vision: bool = Field(False, description="Supports vision")
    function_calling: bool = Field(True, description="Supports function calling")
    streaming: bool = Field(True, description="Supports streaming")
    context_window: Optional[int] = Field(None, description="Max input tokens")
    max_output: Optional[int] = Field(None, description="Max output tokens")
    release_date: Optional[str] = Field(None, description="Model release date")
    is_deprecated: bool = Field(False, description="Is model deprecated")


class ModelCreate(ModelBase):
    pass


class ModelUpdate(BaseModel):
    model_alias: Optional[str] = None
    pricing_in: Optional[float] = None
    pricing_out: Optional[float] = None
    is_deprecated: Optional[bool] = None


class Model(ModelBase):
    id: int
    provider_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PersonaBase(BaseModel):
    display_name: str = Field(..., description="Persona display name")
    role: str = Field(..., description="Role/title")
    base_prompt: Optional[str] = Field(None, description="Short base prompt")
    full_prompt: Optional[str] = Field(None, description="Full system prompt (markdown)")
    traits: List[str] = Field(default_factory=list, description="Character traits")
    communication_style: str = Field("balanced", description="Communication style")
    specializations: List[str] = Field(default_factory=list, description="Areas of expertise")
    languages: List[str] = Field(default_factory=list, description="Languages spoken")
    motto: Optional[str] = Field(None, description="Personal motto")
    description: Optional[str] = Field(None, description="Short description")
    default_model_id: Optional[int] = Field(None, description="Default model FK")


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    base_prompt: Optional[str] = None
    full_prompt: Optional[str] = None
    traits: Optional[List[str]] = None
    communication_style: Optional[str] = None
    specializations: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    motto: Optional[str] = None
    description: Optional[str] = None
    default_model_id: Optional[int] = None


class Persona(PersonaBase):
    id: int
    work_ethic: List[str] = Field(default_factory=list)
    collaboration_notes: Optional[str] = None
    icon: Optional[str] = None
    is_builtin: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    default_model_alias: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Router
# =============================================================================

router = APIRouter(tags=["models"])


def _serialize_row(row: dict) -> dict:
    """Convert database row to JSON-serializable dict."""
    result = {}
    for key, value in row.items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        elif isinstance(value, (list, tuple)):
            result[key] = list(value) if value else []
        else:
            result[key] = value
    return result


# =============================================================================
# Providers Endpoints
# =============================================================================

@router.get("/providers", response_model=dict)
async def list_providers(db: AsyncDatabaseService = Depends(get_async_db)):
    """List all providers from database.

    Uses AsyncDatabaseService for non-blocking DB access.
    """
    providers = await db.fetch_all("""
        SELECT p.*,
               COUNT(m.id) as model_count
        FROM agent.providers p
        LEFT JOIN agent.models m ON m.provider_id = p.id
        GROUP BY p.id
        ORDER BY p.id
    """)
    providers = [_serialize_row(p) for p in providers]
    return {"providers": providers, "total": len(providers)}


@router.get("/providers/{provider_id}", response_model=dict)
async def get_provider(provider_id: int, db: AsyncDatabaseService = Depends(get_async_db)):
    """Get a specific provider.

    Uses AsyncDatabaseService for non-blocking DB access.
    """
    provider = await db.fetch_one(
        "SELECT * FROM agent.providers WHERE id = %(id)s",
        {'id': provider_id}
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _serialize_row(provider)


@router.post("/providers", response_model=dict, status_code=201)
async def create_provider(data: ProviderCreate, db: DatabaseService = Depends(get_database_service)):
    """Create a new provider."""
    # Check for duplicate name
    existing = db.execute_one(
        "SELECT id FROM agent.providers WHERE LOWER(name) = LOWER(%(name)s)",
        {'name': data.name}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Provider with this name already exists")

    # Insert new provider
    result = db.execute_one("""
        INSERT INTO agent.providers (name, api_base_url, is_local)
        VALUES (%(name)s, %(api_base_url)s, %(is_local)s)
        RETURNING *
    """, {
        'name': data.name.lower(),
        'api_base_url': data.api_base_url,
        'is_local': data.is_local,
    })
    return _serialize_row(result)


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: int, db: DatabaseService = Depends(get_database_service)):
    """Delete a provider."""
    db.execute(
        "DELETE FROM agent.providers WHERE id = %(id)s",
        {'id': provider_id}
    )


# =============================================================================
# Models Endpoints
# =============================================================================

@router.get("/models", response_model=dict)
async def list_models(
    provider_id: Optional[int] = None,
    include_deprecated: bool = False,
    db: DatabaseService = Depends(get_database_service),
):
    """List all models from database, optionally filtered by provider."""
    models = db.get_models(provider_id=provider_id, include_deprecated=include_deprecated)
    models = [_serialize_row(m) for m in models]
    return {"models": models, "total": len(models)}


@router.get("/models/{model_id}", response_model=dict)
async def get_model(model_id: int, db: DatabaseService = Depends(get_database_service)):
    """Get a specific model."""
    model = db.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return _serialize_row(model)


@router.post("/models", response_model=dict, status_code=201)
async def create_model(data: ModelCreate, db: DatabaseService = Depends(get_database_service)):
    """Create a new model."""
    # Check provider exists
    provider = db.get_provider(data.provider_id)
    if not provider:
        raise HTTPException(status_code=400, detail="Provider not found")

    # Insert new model
    result = db.execute_one("""
        INSERT INTO agent.models (
            provider_id, model_name, model_alias,
            pricing_in, pricing_out, pricing_cache_read, pricing_cache_write,
            extended_thinking, vision, function_calling, streaming,
            context_window, max_output, release_date, is_deprecated
        ) VALUES (
            %(provider_id)s, %(model_name)s, %(model_alias)s,
            %(pricing_in)s, %(pricing_out)s, %(pricing_cache_read)s, %(pricing_cache_write)s,
            %(extended_thinking)s, %(vision)s, %(function_calling)s, %(streaming)s,
            %(context_window)s, %(max_output)s, %(release_date)s, %(is_deprecated)s
        )
        RETURNING *, (SELECT name FROM agent.providers WHERE id = %(provider_id)s) as provider_name
    """, {
        'provider_id': data.provider_id,
        'model_name': data.model_name,
        'model_alias': data.model_alias,
        'pricing_in': data.pricing_in,
        'pricing_out': data.pricing_out,
        'pricing_cache_read': data.pricing_cache_read,
        'pricing_cache_write': data.pricing_cache_write,
        'extended_thinking': data.extended_thinking,
        'vision': data.vision,
        'function_calling': data.function_calling,
        'streaming': data.streaming,
        'context_window': data.context_window,
        'max_output': data.max_output,
        'release_date': data.release_date,
        'is_deprecated': data.is_deprecated,
    })
    return _serialize_row(result)


@router.patch("/models/{model_id}", response_model=dict)
async def update_model(model_id: int, data: ModelUpdate, db: DatabaseService = Depends(get_database_service)):
    """Update a model."""
    # Build SET clause dynamically
    updates = []
    params = {'id': model_id}

    if data.model_alias is not None:
        updates.append("model_alias = %(model_alias)s")
        params['model_alias'] = data.model_alias
    if data.pricing_in is not None:
        updates.append("pricing_in = %(pricing_in)s")
        params['pricing_in'] = data.pricing_in
    if data.pricing_out is not None:
        updates.append("pricing_out = %(pricing_out)s")
        params['pricing_out'] = data.pricing_out
    if data.is_deprecated is not None:
        updates.append("is_deprecated = %(is_deprecated)s")
        params['is_deprecated'] = data.is_deprecated

    if not updates:
        model = db.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return _serialize_row(model)

    updates.append("updated_at = NOW()")

    result = db.execute_one(f"""
        UPDATE agent.models
        SET {', '.join(updates)}
        WHERE id = %(id)s
        RETURNING *, (SELECT name FROM agent.providers WHERE id = provider_id) as provider_name
    """, params)

    if not result:
        raise HTTPException(status_code=404, detail="Model not found")
    return _serialize_row(result)


@router.delete("/models/{model_id}", status_code=204)
async def delete_model(model_id: int, db: DatabaseService = Depends(get_database_service)):
    """Delete a model."""
    db.execute(
        "DELETE FROM agent.models WHERE id = %(id)s",
        {'id': model_id}
    )


# =============================================================================
# Personas Endpoints
# =============================================================================

@router.get("/personas", response_model=dict)
async def list_personas(db: DatabaseService = Depends(get_database_service)):
    """List all personas from database."""
    personas = db.get_personas()
    personas = [_serialize_row(p) for p in personas]
    return {"personas": personas, "total": len(personas)}


@router.get("/personas/{persona_id}", response_model=dict)
async def get_persona(persona_id: int, db: DatabaseService = Depends(get_database_service)):
    """Get a specific persona."""
    persona = db.get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return _serialize_row(persona)


@router.post("/personas", response_model=dict, status_code=201)
async def create_persona(data: PersonaCreate, db: DatabaseService = Depends(get_database_service)):
    """Create a new persona."""
    result = db.execute_one("""
        INSERT INTO agent.personas (
            display_name, role, base_prompt, full_prompt,
            traits, communication_style, specializations, languages,
            motto, description, default_model_id
        ) VALUES (
            %(display_name)s, %(role)s, %(base_prompt)s, %(full_prompt)s,
            %(traits)s, %(communication_style)s, %(specializations)s, %(languages)s,
            %(motto)s, %(description)s, %(default_model_id)s
        )
        RETURNING *
    """, {
        'display_name': data.display_name,
        'role': data.role,
        'base_prompt': data.base_prompt,
        'full_prompt': data.full_prompt,
        'traits': data.traits,
        'communication_style': data.communication_style,
        'specializations': data.specializations,
        'languages': data.languages,
        'motto': data.motto,
        'description': data.description,
        'default_model_id': data.default_model_id,
    })
    return _serialize_row(result)


@router.patch("/personas/{persona_id}", response_model=dict)
async def update_persona(persona_id: int, data: PersonaUpdate, db: DatabaseService = Depends(get_database_service)):
    """Update a persona."""
    updates = []
    params = {'id': persona_id}

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            updates.append(f"{key} = %({key})s")
            params[key] = value

    if not updates:
        persona = db.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        return _serialize_row(persona)

    updates.append("updated_at = NOW()")

    result = db.execute_one(f"""
        UPDATE agent.personas
        SET {', '.join(updates)}
        WHERE id = %(id)s
        RETURNING *
    """, params)

    if not result:
        raise HTTPException(status_code=404, detail="Persona not found")
    return _serialize_row(result)


@router.delete("/personas/{persona_id}", status_code=204)
async def delete_persona(persona_id: int, db: DatabaseService = Depends(get_database_service)):
    """Delete a persona."""
    # Check if builtin
    persona = db.get_persona(persona_id)
    if persona and persona.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete builtin persona")

    db.execute(
        "DELETE FROM agent.personas WHERE id = %(id)s",
        {'id': persona_id}
    )


# =============================================================================
# Agents Endpoints (read from database)
# =============================================================================

@router.get("/agents-db", response_model=dict)
async def list_agents_from_db(db: DatabaseService = Depends(get_database_service)):
    """List all agents from database (via agent_dashboard view)."""
    agents = db.get_agents()
    agents = [_serialize_row(a) for a in agents]
    return {"agents": agents, "total": len(agents)}


@router.get("/agents-db/{agent_id}", response_model=dict)
async def get_agent_from_db(agent_id: int, db: DatabaseService = Depends(get_database_service)):
    """Get a specific agent from database."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _serialize_row(agent)


# Export router
models_router = router
