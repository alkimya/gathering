"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================


class AgentStatus(str, Enum):
    """Agent status."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircleStatus(str, Enum):
    """Circle status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class ConversationStatus(str, Enum):
    """Conversation status."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# Agent Schemas
# =============================================================================


class AgentPersonaSchema(BaseModel):
    """Agent persona configuration."""
    name: str = Field(..., description="Agent name")
    role: str = Field(..., description="Agent role (e.g., 'Architect', 'Developer')")
    traits: List[str] = Field(default_factory=list, description="Personality traits")
    communication_style: str = Field(
        default="balanced",
        description="Communication style: formal, concise, detailed, technical, friendly, balanced"
    )
    specializations: List[str] = Field(default_factory=list, description="Areas of expertise")
    languages: List[str] = Field(default=["fr", "en"], description="Supported languages")


class AgentConfigSchema(BaseModel):
    """Agent configuration."""
    provider: str = Field(default="anthropic", description="LLM provider")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model name")
    max_tokens: int = Field(default=4096, description="Max tokens per response")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Temperature")
    competencies: List[str] = Field(default_factory=list, description="Agent competencies")
    can_review: List[str] = Field(default_factory=list, description="Review capabilities")


class AgentCreate(BaseModel):
    """Request to create an agent."""
    persona: AgentPersonaSchema
    config: AgentConfigSchema = Field(default_factory=AgentConfigSchema)


class AgentUpdate(BaseModel):
    """Request to update an agent."""
    persona: Optional[AgentPersonaSchema] = None
    config: Optional[AgentConfigSchema] = None


class AgentResponse(BaseModel):
    """Agent response."""
    id: int = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    role: str = Field(..., description="Agent role")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    status: AgentStatus = Field(..., description="Current status")
    competencies: List[str] = Field(default_factory=list)
    can_review: List[str] = Field(default_factory=list)
    current_task: Optional[str] = None
    created_at: datetime
    last_activity: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentDetailResponse(AgentResponse):
    """Detailed agent response."""
    persona: AgentPersonaSchema
    config: AgentConfigSchema
    session: Optional[Dict[str, Any]] = None
    skills: List[str] = Field(default_factory=list)
    tools_count: int = 0


class AgentListResponse(BaseModel):
    """List of agents."""
    agents: List[AgentResponse]
    total: int


# =============================================================================
# Chat Schemas
# =============================================================================


class ChatRequest(BaseModel):
    """Request to chat with an agent."""
    message: str = Field(..., min_length=1, description="User message")
    include_memories: bool = Field(default=True, description="Include RAG memories")
    allow_tools: bool = Field(default=True, description="Allow tool use")


class ChatResponse(BaseModel):
    """Response from agent chat."""
    content: str = Field(..., description="Agent response")
    agent_id: int
    agent_name: str
    model: str
    duration_ms: int = 0
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0


# =============================================================================
# Circle Schemas
# =============================================================================


class CircleCreate(BaseModel):
    """Request to create a circle."""
    name: str = Field(..., min_length=1, description="Circle name")
    require_review: bool = Field(default=True, description="Require peer review")
    auto_route: bool = Field(default=True, description="Auto-route tasks to agents")
    max_concurrent_tasks: int = Field(default=5, ge=1, description="Max concurrent tasks")


class CircleResponse(BaseModel):
    """Circle response."""
    id: str = Field(..., description="Circle ID")
    name: str
    status: CircleStatus
    agent_count: int
    task_count: int
    active_tasks: int
    require_review: bool
    auto_route: bool
    created_at: datetime
    started_at: Optional[datetime] = None


class CircleDetailResponse(CircleResponse):
    """Detailed circle response."""
    agents: List[AgentResponse]
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int
    conflicts: int


class CircleListResponse(BaseModel):
    """List of circles."""
    circles: List[CircleResponse]
    total: int


# =============================================================================
# Task Schemas
# =============================================================================


class TaskCreate(BaseModel):
    """Request to create a task."""
    title: str = Field(..., min_length=1, description="Task title")
    description: str = Field(default="", description="Task description")
    required_competencies: List[str] = Field(default_factory=list)
    priority: Union[int, str] = Field(default=5, description="Priority (1-10 or low/medium/high/critical)")
    assigned_agent_id: Optional[int] = Field(default=None, description="Assign to specific agent")

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v: Union[int, str]) -> int:
        """Convert string priority to int (1-10 scale)."""
        if isinstance(v, int):
            return max(1, min(10, v))
        if isinstance(v, str):
            priority_map = {
                'low': 8,
                'medium': 5,
                'high': 3,
                'critical': 1,
            }
            return priority_map.get(v.lower(), 5)
        return 5


class TaskResponse(BaseModel):
    """Task response."""
    id: int
    title: str
    description: str
    status: TaskStatus
    priority: int
    assigned_agent_id: Optional[int] = None
    assigned_agent_name: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None


class TaskListResponse(BaseModel):
    """List of tasks."""
    tasks: List[TaskResponse]
    total: int


class TaskResultSubmit(BaseModel):
    """Submit task result."""
    result: str = Field(..., description="Task result/output")
    files_modified: List[str] = Field(default_factory=list)


# =============================================================================
# Conversation Schemas
# =============================================================================


class ConversationCreate(BaseModel):
    """Request to start a conversation."""
    topic: str = Field(..., min_length=1, description="Conversation topic")
    agent_ids: List[int] = Field(..., min_length=1, description="Participating agents (1+ for user-agent chat, 2+ for multi-agent)")
    max_turns: int = Field(default=10, ge=1, le=50, description="Max conversation turns")
    initial_prompt: str = Field(default="", description="Initial prompt/instructions")
    turn_strategy: str = Field(
        default="round_robin",
        description="Turn strategy: round_robin, mention_based, free_form"
    )


class ConversationMessageSchema(BaseModel):
    """Message in a conversation."""
    agent_id: int
    agent_name: str
    content: str
    mentions: List[int] = Field(default_factory=list)
    timestamp: datetime


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    topic: str
    status: ConversationStatus
    participant_names: List[str]
    turns_taken: int
    max_turns: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation response."""
    messages: List[ConversationMessageSchema]
    transcript: str
    summary: Optional[str] = None
    duration_seconds: float = 0


class ConversationListResponse(BaseModel):
    """List of conversations."""
    conversations: List[ConversationResponse]
    total: int


# =============================================================================
# Event Schemas
# =============================================================================


class EventSchema(BaseModel):
    """Event schema for SSE/WebSocket."""
    id: str
    type: str
    source_agent_id: Optional[int] = None
    target_agent_id: Optional[int] = None
    data: Dict[str, Any]
    timestamp: datetime


# =============================================================================
# Memory Schemas
# =============================================================================


class MemoryCreate(BaseModel):
    """Request to create a memory."""
    content: str = Field(..., min_length=1, description="Memory content")
    memory_type: str = Field(default="learning", description="Type: learning, decision, error, etc.")


class MemoryResponse(BaseModel):
    """Memory response."""
    id: int
    content: str
    memory_type: str
    created_at: datetime


class MemoryListResponse(BaseModel):
    """List of memories."""
    memories: List[MemoryResponse]
    total: int


class RecallRequest(BaseModel):
    """Request to recall memories."""
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Max results")
    memory_types: Optional[List[str]] = None


class RecallResponse(BaseModel):
    """Recall response."""
    memories: List[str]
    query: str


# =============================================================================
# Health & Status
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    uptime_seconds: float
    agents_count: int
    circles_count: int
    active_tasks: int


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
