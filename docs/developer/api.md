# API Development

Guide for developing and extending the GatheRing API.

## Architecture

The API is built with FastAPI and organized into routers:

```
gathering/api/
├── __init__.py
├── app.py              # Main FastAPI app
├── routers/
│   ├── agents.py       # /agents endpoints
│   ├── circles.py      # /circles endpoints
│   ├── conversations.py # /conversations endpoints
│   ├── workspace.py    # /workspace endpoints
│   └── memory.py       # /memory endpoints
├── schemas/            # Pydantic models
├── dependencies.py     # Dependency injection
└── middleware.py       # Custom middleware
```

## Creating a New Router

### 1. Create the Router File

```python
# gathering/api/routers/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from gathering.api.schemas.my_feature import (
    MyFeatureCreate,
    MyFeatureResponse,
)
from gathering.api.dependencies import get_db

router = APIRouter(
    prefix="/my-feature",
    tags=["my-feature"],
)


@router.get("/", response_model=List[MyFeatureResponse])
async def list_features(db=Depends(get_db)):
    """List all features."""
    features = await db.fetch_all("SELECT * FROM my_features")
    return features


@router.post("/", response_model=MyFeatureResponse, status_code=201)
async def create_feature(
    data: MyFeatureCreate,
    db=Depends(get_db),
):
    """Create a new feature."""
    result = await db.execute(
        "INSERT INTO my_features (name) VALUES ($1) RETURNING *",
        data.name,
    )
    return result


@router.get("/{feature_id}", response_model=MyFeatureResponse)
async def get_feature(feature_id: int, db=Depends(get_db)):
    """Get a feature by ID."""
    feature = await db.fetch_one(
        "SELECT * FROM my_features WHERE id = $1",
        feature_id,
    )
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature
```

### 2. Create Schemas

```python
# gathering/api/schemas/my_feature.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MyFeatureBase(BaseModel):
    name: str
    description: Optional[str] = None


class MyFeatureCreate(MyFeatureBase):
    pass


class MyFeatureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class MyFeatureResponse(MyFeatureBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### 3. Register the Router

```python
# gathering/api/app.py
from gathering.api.routers import my_feature

app.include_router(my_feature.router)
```

## Dependency Injection

### Database Connection

```python
from gathering.api.dependencies import get_db

@router.get("/")
async def my_endpoint(db=Depends(get_db)):
    result = await db.fetch_all("SELECT 1")
    return result
```

### Current User (Future)

```python
from gathering.api.dependencies import get_current_user

@router.get("/me")
async def my_profile(user=Depends(get_current_user)):
    return user
```

### Custom Dependencies

```python
# gathering/api/dependencies.py
from fastapi import Depends, HTTPException

async def get_agent_or_404(
    agent_id: int,
    db=Depends(get_db),
):
    agent = await db.fetch_one(
        "SELECT * FROM agent.agents WHERE id = $1",
        agent_id,
    )
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


# Usage
@router.get("/agents/{agent_id}/details")
async def agent_details(agent=Depends(get_agent_or_404)):
    return {"agent": agent}
```

## Error Handling

### HTTP Exceptions

```python
from fastapi import HTTPException

@router.get("/{id}")
async def get_item(id: int):
    item = await find_item(id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    return item
```

### Custom Exception Handlers

```python
# gathering/api/middleware.py
from fastapi import Request
from fastapi.responses import JSONResponse

class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": exc.message},
    )
```

## Request Validation

### Path Parameters

```python
@router.get("/agents/{agent_id}")
async def get_agent(agent_id: int):  # Automatically validated as int
    pass
```

### Query Parameters

```python
from typing import Optional

@router.get("/agents")
async def list_agents(
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
):
    pass
```

### Request Body

```python
from pydantic import BaseModel, Field

class CreateAgent(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = Field(None, max_length=100)
    provider: str = Field(default="anthropic")  # openai, anthropic, ollama
    model: str = Field(default="claude-sonnet-4-20250514")

@router.post("/agents")
async def create_agent(data: CreateAgent):
    pass
```

## Response Models

### Single Item

```python
@router.get("/{id}", response_model=AgentResponse)
async def get_agent(id: int):
    return await fetch_agent(id)
```

### List with Pagination

```python
from pydantic import BaseModel
from typing import List, Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=PaginatedResponse[AgentResponse])
async def list_agents(page: int = 1, page_size: int = 10):
    items = await fetch_agents(page, page_size)
    total = await count_agents()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
```

## WebSocket Endpoints

```python
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass
```

## Background Tasks

```python
from fastapi import BackgroundTasks

async def process_in_background(data: dict):
    # Long-running task
    await asyncio.sleep(10)
    print(f"Processed: {data}")


@router.post("/process")
async def start_processing(
    data: dict,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(process_in_background, data)
    return {"status": "processing"}
```

## Testing API Endpoints

```python
# tests/api/test_agents.py
import pytest
from httpx import AsyncClient
from gathering.api.app import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_agents(client):
    response = await client.get("/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_agent(client):
    response = await client.post(
        "/agents",
        json={
            "name": "Test Agent",
            "provider": "openai",
            "model": "gpt-4o"
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Agent"
```

## API Documentation

FastAPI automatically generates OpenAPI documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Adding Documentation

```python
@router.post(
    "/",
    response_model=AgentResponse,
    summary="Create a new agent",
    description="Creates a new AI agent with the specified configuration.",
    responses={
        201: {"description": "Agent created successfully"},
        422: {"description": "Validation error"},
    },
)
async def create_agent(data: AgentCreate):
    """
    Create a new agent with:

    - **name**: Agent's display name
    - **role**: Agent's role (optional)
    - **provider**: LLM provider (openai, anthropic, ollama)
    - **model**: Model identifier (provider-specific)
    """
    pass
```

## Related Topics

- [Architecture](architecture.md) - System architecture
- [Database](database.md) - Database layer
- [WebSocket](websocket.md) - Real-time communication
- [Testing](testing.md) - API testing
