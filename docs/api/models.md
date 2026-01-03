# API Models

Pydantic models used in the GatheRing API.

## Agent Models

### AgentCreate

```python
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = Field(None, max_length=100)
    provider: str = Field(default="anthropic")  # openai, anthropic, ollama
    model: str = Field(default="claude-sonnet-4-20250514")
    personality: Optional[PersonalityConfig] = None
    background: Optional[BackgroundConfig] = None
    config: Optional[AgentConfig] = None
```

### AgentUpdate

```python
class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = None
    model: Optional[str] = None
    personality: Optional[PersonalityConfig] = None
    config: Optional[AgentConfig] = None
```

### AgentResponse

```python
class AgentResponse(BaseModel):
    id: int
    name: str
    role: Optional[str]
    model: str
    personality: Optional[PersonalityConfig]
    config: Optional[AgentConfig]
    status: AgentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### PersonalityConfig

```python
class PersonalityConfig(BaseModel):
    traits: list[str] = Field(default_factory=list)
    communication_style: Optional[str] = "professional"
    languages: list[str] = Field(default_factory=lambda: ["English"])
```

### AgentConfig

```python
class AgentConfig(BaseModel):
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)
    tools: list[str] = Field(default_factory=list)
```

### AgentStatus

```python
class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
```

## Circle Models

### CircleCreate

```python
class CircleCreate(BaseModel):
    name: str = Field(..., pattern="^[a-z0-9-]+$", max_length=50)
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    config: Optional[CircleConfig] = None
```

### CircleResponse

```python
class CircleResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    config: Optional[CircleConfig]
    status: CircleStatus
    agent_count: int
    created_at: datetime

    class Config:
        from_attributes = True
```

### CircleConfig

```python
class CircleConfig(BaseModel):
    max_agents: int = Field(default=10, ge=1, le=50)
    conversation_mode: str = Field(default="round_robin")
    turn_timeout: int = Field(default=30, ge=1)
    max_turns_per_conversation: int = Field(default=50, ge=1)
    memory_scope: str = Field(default="circle")
    allow_tools: bool = True
```

### CircleStatus

```python
class CircleStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
```

## Conversation Models

### ConversationCreate

```python
class ConversationCreate(BaseModel):
    circle_name: str
    topic: str = Field(..., min_length=1, max_length=500)
    agent_ids: list[int] = Field(..., min_items=1)
    initial_prompt: Optional[str] = None
    max_turns: int = Field(default=50, ge=1)
```

### ConversationResponse

```python
class ConversationResponse(BaseModel):
    id: int
    circle_id: int
    topic: str
    status: ConversationStatus
    turn_count: int
    created_at: datetime
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True
```

### ConversationAdvance

```python
class ConversationAdvance(BaseModel):
    prompt: Optional[str] = None
    agent_id: Optional[int] = None
```

### MessageResponse

```python
class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    agent_id: int
    agent_name: str
    content: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
```

## Workspace Models

### WorkspaceInfo

```python
class WorkspaceInfo(BaseModel):
    id: int
    path: str
    name: str
    git_enabled: bool
    current_branch: Optional[str]
```

### FileInfo

```python
class FileInfo(BaseModel):
    path: str
    name: str
    type: str  # "file" or "directory"
    size: Optional[int]
    modified_at: Optional[datetime]
```

### FileContent

```python
class FileContent(BaseModel):
    path: str
    content: str
    language: Optional[str]
    size: int
```

### FileWrite

```python
class FileWrite(BaseModel):
    content: str
```

### GitStatus

```python
class GitStatus(BaseModel):
    branch: str
    ahead: int
    behind: int
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    deleted: list[str]
```

### GitCommit

```python
class GitCommit(BaseModel):
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime
```

### GitStage

```python
class GitStage(BaseModel):
    files: list[str]
```

### GitCommitCreate

```python
class GitCommitCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
```

## Memory Models

### MemoryCreate

```python
class MemoryCreate(BaseModel):
    agent_id: Optional[int] = None
    scope: MemoryScope
    scope_id: Optional[int] = None
    memory_type: MemoryType = MemoryType.FACT
    key: str = Field(..., max_length=200)
    value: str
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0, le=1)
```

### MemoryResponse

```python
class MemoryResponse(BaseModel):
    id: int
    agent_id: Optional[int]
    scope: MemoryScope
    memory_type: MemoryType
    key: str
    value: str
    importance: float
    created_at: datetime

    class Config:
        from_attributes = True
```

### MemorySearchResult

```python
class MemorySearchResult(BaseModel):
    id: int
    key: str
    value: str
    similarity: float
    scope: MemoryScope
```

### MemoryScope

```python
class MemoryScope(str, Enum):
    GLOBAL = "global"
    CIRCLE = "circle"
    AGENT = "agent"
    CONVERSATION = "conversation"
```

### MemoryType

```python
class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EXPERIENCE = "experience"
    SKILL = "skill"
    RELATIONSHIP = "relationship"
```

## Dashboard Models

### DashboardStats

```python
class DashboardStats(BaseModel):
    total_agents: int
    active_agents: int
    total_circles: int
    active_circles: int
    conversations_today: int
    messages_today: int
```

### ActivityItem

```python
class ActivityItem(BaseModel):
    id: int
    type: str
    title: str
    description: Optional[str]
    agent_id: Optional[int]
    agent_name: Optional[str]
    circle_id: Optional[int]
    circle_name: Optional[str]
    timestamp: datetime
```

## Common Models

### PaginatedResponse

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

### ErrorResponse

```python
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
```

### ValidationErrorResponse

```python
class ValidationErrorResponse(BaseModel):
    detail: list[ValidationErrorItem]


class ValidationErrorItem(BaseModel):
    loc: list[str]
    msg: str
    type: str
```
