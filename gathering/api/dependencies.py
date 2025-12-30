"""
FastAPI dependencies for dependency injection.
"""

import os
import sys
from typing import Dict, Optional, List, Any
from functools import lru_cache

from gathering.orchestration import GatheringCircle
from gathering.agents import MemoryService, AgentWrapper

# Import picopg
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'picopg'))
from picopg import Database as PicoPGDatabase, Config as PicoPGConfig


# =============================================================================
# Database Connection
# =============================================================================


class DatabaseService:
    """Database service for API using picopg."""

    _instance: Optional['DatabaseService'] = None

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()

        self._config = PicoPGConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'gathering'),
            user=os.getenv('DB_USER', 'loc'),
            password=os.getenv('DB_PASSWORD', ''),
        )
        self._db = PicoPGDatabase(self._config)

    @property
    def db(self) -> PicoPGDatabase:
        return self._db

    def execute(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query and return list of dicts."""
        result = self._db.execute(sql, params or {})
        return list(result)

    def execute_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute query and return first row as dict."""
        rows = self.execute(sql, params)
        return rows[0] if rows else None

    def fetch_all(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Fetch all rows as list of dicts (alias for execute)."""
        return self.execute(sql, params)

    def fetch_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Fetch first row as dict (alias for execute_one)."""
        return self.execute_one(sql, params)

    # Agent queries
    def get_agents(self) -> List[Dict]:
        """Get all agents from database."""
        return self.execute("""
            SELECT * FROM public.agent_dashboard
            ORDER BY id
        """)

    def get_agent(self, agent_id: int) -> Optional[Dict]:
        """Get agent by ID."""
        return self.execute_one("""
            SELECT * FROM public.agent_dashboard
            WHERE id = %(id)s
        """, {'id': agent_id})

    # Provider queries
    def get_providers(self) -> List[Dict]:
        """Get all providers."""
        return self.execute("""
            SELECT p.*,
                   COUNT(m.id) as model_count
            FROM agent.providers p
            LEFT JOIN agent.models m ON m.provider_id = p.id
            GROUP BY p.id
            ORDER BY p.id
        """)

    def get_provider(self, provider_id: int) -> Optional[Dict]:
        """Get provider by ID."""
        return self.execute_one("""
            SELECT * FROM agent.providers WHERE id = %(id)s
        """, {'id': provider_id})

    # Model queries
    def get_models(self, provider_id: Optional[int] = None, include_deprecated: bool = False) -> List[Dict]:
        """Get all models, optionally filtered by provider."""
        sql = """
            SELECT m.*, p.name as provider_name
            FROM agent.models m
            JOIN agent.providers p ON p.id = m.provider_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}

        if provider_id:
            sql += " AND m.provider_id = %(provider_id)s"
            params['provider_id'] = provider_id

        if not include_deprecated:
            sql += " AND m.is_deprecated = false"

        sql += " ORDER BY p.name, m.model_alias"
        return self.execute(sql, params)

    def get_model(self, model_id: int) -> Optional[Dict]:
        """Get model by ID."""
        return self.execute_one("""
            SELECT m.*, p.name as provider_name
            FROM agent.models m
            JOIN agent.providers p ON p.id = m.provider_id
            WHERE m.id = %(id)s
        """, {'id': model_id})

    # Persona queries
    def get_personas(self) -> List[Dict]:
        """Get all personas."""
        return self.execute("""
            SELECT p.*, m.model_alias as default_model_alias
            FROM agent.personas p
            LEFT JOIN agent.models m ON m.id = p.default_model_id
            ORDER BY p.id
        """)

    def get_persona(self, persona_id: int) -> Optional[Dict]:
        """Get persona by ID."""
        return self.execute_one("""
            SELECT p.*, m.model_alias as default_model_alias
            FROM agent.personas p
            LEFT JOIN agent.models m ON m.id = p.default_model_id
            WHERE p.id = %(id)s
        """, {'id': persona_id})

    # Circle queries
    def get_circles(self, is_active: Optional[bool] = None) -> List[Dict]:
        """Get all circles, optionally filtered by active status."""
        sql = """
            SELECT c.*,
                   COUNT(DISTINCT m.agent_id) as member_count,
                   COUNT(DISTINCT t.id) as task_count
            FROM circle.circles c
            LEFT JOIN circle.members m ON m.circle_id = c.id AND m.is_active = true
            LEFT JOIN circle.tasks t ON t.circle_id = c.id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}

        if is_active is not None:
            sql += " AND c.is_active = %(is_active)s"
            params['is_active'] = is_active

        sql += " GROUP BY c.id ORDER BY c.created_at DESC"
        return self.execute(sql, params)

    def get_circle(self, circle_id: int) -> Optional[Dict]:
        """Get circle by ID with member and task counts."""
        return self.execute_one("""
            SELECT c.*,
                   COUNT(DISTINCT m.agent_id) as member_count,
                   COUNT(DISTINCT t.id) as task_count
            FROM circle.circles c
            LEFT JOIN circle.members m ON m.circle_id = c.id AND m.is_active = true
            LEFT JOIN circle.tasks t ON t.circle_id = c.id
            WHERE c.id = %(id)s
            GROUP BY c.id
        """, {'id': circle_id})

    def get_circle_members(self, circle_id: int) -> List[Dict]:
        """Get all active members of a circle."""
        return self.execute("""
            SELECT m.*, a.name as agent_name, a.role as agent_role
            FROM circle.members m
            JOIN agent.agents a ON a.id = m.agent_id
            WHERE m.circle_id = %(circle_id)s AND m.is_active = true
            ORDER BY m.joined_at
        """, {'circle_id': circle_id})

    def get_circle_tasks(self, circle_id: int, status: Optional[str] = None) -> List[Dict]:
        """Get tasks for a circle, optionally filtered by status."""
        sql = """
            SELECT t.*, a.name as assigned_agent_name
            FROM circle.tasks t
            LEFT JOIN agent.agents a ON a.id = t.assigned_agent_id
            WHERE t.circle_id = %(circle_id)s
        """
        params: Dict[str, Any] = {'circle_id': circle_id}

        if status:
            sql += " AND t.status = %(status)s::task_status"
            params['status'] = status

        sql += " ORDER BY t.priority DESC, t.created_at"
        return self.execute(sql, params)


_db_service: Optional[DatabaseService] = None


@lru_cache()
def get_database_service() -> DatabaseService:
    """Get or create the database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


class AgentRegistry:
    """Registry for managing agents across the API."""

    def __init__(self):
        self._agents: Dict[int, AgentWrapper] = {}
        self._next_id: int = 1

    def add(self, agent: AgentWrapper) -> int:
        """Add an agent to the registry."""
        agent_id = agent.agent_id
        self._agents[agent_id] = agent
        if agent_id >= self._next_id:
            self._next_id = agent_id + 1
        return agent_id

    def get(self, agent_id: int) -> Optional[AgentWrapper]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def remove(self, agent_id: int) -> bool:
        """Remove an agent from the registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def list_all(self) -> list:
        """List all agents."""
        return list(self._agents.values())

    def count(self) -> int:
        """Count agents."""
        return len(self._agents)

    def next_id(self) -> int:
        """Get next available ID."""
        next_id = self._next_id
        self._next_id += 1
        return next_id


class CircleRegistry:
    """Registry for managing circles across the API."""

    def __init__(self):
        self._circles: Dict[str, GatheringCircle] = {}

    def add(self, circle: GatheringCircle) -> str:
        """Add a circle to the registry."""
        self._circles[circle.name] = circle
        return circle.name

    def get(self, name: str) -> Optional[GatheringCircle]:
        """Get a circle by name."""
        return self._circles.get(name)

    def remove(self, name: str) -> bool:
        """Remove a circle from the registry."""
        if name in self._circles:
            del self._circles[name]
            return True
        return False

    def list_all(self) -> list:
        """List all circles."""
        return list(self._circles.values())

    def count(self) -> int:
        """Count circles."""
        return len(self._circles)


class ConversationRegistry:
    """Registry for managing conversations."""

    def __init__(self):
        self._conversations: Dict[str, dict] = {}
        self._counter: int = 0

    def add(self, conversation_data: dict) -> str:
        """Add a conversation."""
        self._counter += 1
        conv_id = f"conv-{self._counter}"
        conversation_data["id"] = conv_id
        self._conversations[conv_id] = conversation_data
        return conv_id

    def get(self, conv_id: str) -> Optional[dict]:
        """Get a conversation by ID."""
        return self._conversations.get(conv_id)

    def update(self, conv_id: str, data: dict) -> bool:
        """Update a conversation."""
        if conv_id in self._conversations:
            self._conversations[conv_id].update(data)
            return True
        return False

    def remove(self, conv_id: str) -> bool:
        """Remove a conversation."""
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            return True
        return False

    def list_all(self) -> list:
        """List all conversations."""
        return list(self._conversations.values())

    def count(self) -> int:
        """Count conversations."""
        return len(self._conversations)


# =============================================================================
# Data Source Toggle
# =============================================================================


def use_demo_data() -> bool:
    """Check if demo data should be used instead of database.

    Returns True if USE_DEMO_DATA=true in .env, False otherwise.
    When True, API returns hardcoded demo data for dashboard development.
    When False, API queries PostgreSQL for real data.
    """
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("USE_DEMO_DATA", "true").lower() in ("true", "1", "yes")


# Demo data for dashboard development
DEMO_AGENTS = [
    {
        "id": 1,
        "name": "Dr. Sophie Chen",
        "role": "Lead AI Researcher",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "status": "idle",
        "competencies": ["research", "analysis", "python", "machine-learning"],
        "can_review": ["code", "documentation"],
        "current_task": None,
        "tasks_completed": 47,
        "reviews_done": 23,
        "approval_rate": 0.94,
        "average_quality_score": 4.7,
        "is_active": True,
    },
    {
        "id": 2,
        "name": "Olivia Nakamoto",
        "role": "Full-Stack Developer",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "status": "busy",
        "competencies": ["typescript", "react", "nodejs", "postgresql"],
        "can_review": ["code", "architecture"],
        "current_task": "Implementing dashboard components",
        "tasks_completed": 89,
        "reviews_done": 45,
        "approval_rate": 0.91,
        "average_quality_score": 4.5,
        "is_active": True,
    },
    {
        "id": 3,
        "name": "Marcus Webb",
        "role": "DevOps Engineer",
        "provider": "openai",
        "model": "gpt-4",
        "status": "idle",
        "competencies": ["docker", "kubernetes", "ci-cd", "aws"],
        "can_review": ["infrastructure", "security"],
        "current_task": None,
        "tasks_completed": 34,
        "reviews_done": 18,
        "approval_rate": 0.88,
        "average_quality_score": 4.3,
        "is_active": True,
    },
]

DEMO_PROVIDERS = [
    {"id": 1, "name": "anthropic", "display_name": "Anthropic", "model_count": 3},
    {"id": 2, "name": "openai", "display_name": "OpenAI", "model_count": 4},
    {"id": 3, "name": "deepseek", "display_name": "DeepSeek", "model_count": 2},
    {"id": 4, "name": "ollama", "display_name": "Ollama (Local)", "model_count": 5},
]

DEMO_MODELS = [
    {"id": 1, "provider_id": 1, "provider_name": "anthropic", "model_alias": "claude-sonnet-4-20250514", "is_deprecated": False},
    {"id": 2, "provider_id": 1, "provider_name": "anthropic", "model_alias": "claude-opus-4-20250514", "is_deprecated": False},
    {"id": 3, "provider_id": 2, "provider_name": "openai", "model_alias": "gpt-4", "is_deprecated": False},
    {"id": 4, "provider_id": 2, "provider_name": "openai", "model_alias": "gpt-4-turbo", "is_deprecated": False},
    {"id": 5, "provider_id": 3, "provider_name": "deepseek", "model_alias": "deepseek-coder", "is_deprecated": False},
]

DEMO_CIRCLES = [
    {
        "id": 1,
        "name": "ai-research",
        "display_name": "AI Research Team",
        "description": "Research and experimentation with LLMs and multi-agent systems",
        "status": "running",
        "auto_route": True,
        "require_review": True,
        "member_count": 2,
        "task_count": 3,
        "is_active": True,
    },
    {
        "id": 2,
        "name": "backend-team",
        "display_name": "Backend Development",
        "description": "API development, database optimization, and backend infrastructure",
        "status": "running",
        "auto_route": True,
        "require_review": True,
        "member_count": 2,
        "task_count": 5,
        "is_active": True,
    },
    {
        "id": 3,
        "name": "devops",
        "display_name": "DevOps & Infrastructure",
        "description": "CI/CD, deployment, monitoring, and infrastructure management",
        "status": "stopped",
        "auto_route": False,
        "require_review": True,
        "member_count": 1,
        "task_count": 2,
        "is_active": True,
    },
]

DEMO_CIRCLE_MEMBERS = [
    # ai-research members
    {"id": 1, "circle_id": 1, "agent_id": 1, "agent_name": "Dr. Sophie Chen", "agent_role": "Lead AI Researcher", "role": "lead", "competencies": ["research", "analysis"], "is_active": True},
    {"id": 2, "circle_id": 1, "agent_id": 2, "agent_name": "Olivia Nakamoto", "agent_role": "Full-Stack Developer", "role": "member", "competencies": ["python", "typescript"], "is_active": True},
    # backend-team members
    {"id": 3, "circle_id": 2, "agent_id": 2, "agent_name": "Olivia Nakamoto", "agent_role": "Full-Stack Developer", "role": "lead", "competencies": ["nodejs", "postgresql"], "is_active": True},
    {"id": 4, "circle_id": 2, "agent_id": 1, "agent_name": "Dr. Sophie Chen", "agent_role": "Lead AI Researcher", "role": "member", "competencies": ["python"], "is_active": True},
    # devops members
    {"id": 5, "circle_id": 3, "agent_id": 3, "agent_name": "Marcus Webb", "agent_role": "DevOps Engineer", "role": "lead", "competencies": ["docker", "kubernetes"], "is_active": True},
]

DEMO_CIRCLE_TASKS = [
    # ai-research tasks
    {"id": 1, "circle_id": 1, "title": "Evaluate Claude Opus 4 for research tasks", "status": "in_progress", "priority": "high", "assigned_agent_id": 1, "assigned_agent_name": "Dr. Sophie Chen"},
    {"id": 2, "circle_id": 1, "title": "Design multi-agent collaboration protocol", "status": "pending", "priority": "high", "assigned_agent_id": None, "assigned_agent_name": None},
    {"id": 3, "circle_id": 1, "title": "Write paper on autonomous agent architectures", "status": "pending", "priority": "medium", "assigned_agent_id": None, "assigned_agent_name": None},
    # backend-team tasks
    {"id": 4, "circle_id": 2, "title": "Optimize PostgreSQL query performance", "status": "completed", "priority": "high", "assigned_agent_id": 2, "assigned_agent_name": "Olivia Nakamoto"},
    {"id": 5, "circle_id": 2, "title": "Implement circle endpoints for dashboard", "status": "in_progress", "priority": "high", "assigned_agent_id": 2, "assigned_agent_name": "Olivia Nakamoto"},
    {"id": 6, "circle_id": 2, "title": "Add WebSocket support for real-time updates", "status": "pending", "priority": "medium", "assigned_agent_id": None, "assigned_agent_name": None},
    {"id": 7, "circle_id": 2, "title": "Create API documentation", "status": "pending", "priority": "low", "assigned_agent_id": None, "assigned_agent_name": None},
    {"id": 8, "circle_id": 2, "title": "Implement rate limiting", "status": "completed", "priority": "medium", "assigned_agent_id": 1, "assigned_agent_name": "Dr. Sophie Chen"},
    # devops tasks
    {"id": 9, "circle_id": 3, "title": "Set up CI/CD pipeline", "status": "pending", "priority": "high", "assigned_agent_id": 3, "assigned_agent_name": "Marcus Webb"},
    {"id": 10, "circle_id": 3, "title": "Configure monitoring and alerts", "status": "pending", "priority": "medium", "assigned_agent_id": None, "assigned_agent_name": None},
]


class DataService:
    """Service that returns demo or DB data based on USE_DEMO_DATA setting."""

    def __init__(self, db_service: Optional[DatabaseService] = None):
        self._db = db_service

    @property
    def is_demo_mode(self) -> bool:
        return use_demo_data()

    def get_agents(self) -> List[Dict]:
        """Get agents from demo data or database."""
        if self.is_demo_mode:
            return DEMO_AGENTS
        if self._db:
            return self._db.get_agents()
        return DEMO_AGENTS  # Fallback to demo if no DB

    def get_agent(self, agent_id: int) -> Optional[Dict]:
        """Get agent by ID from demo data or database."""
        if self.is_demo_mode:
            return next((a for a in DEMO_AGENTS if a["id"] == agent_id), None)
        if self._db:
            return self._db.get_agent(agent_id)
        return next((a for a in DEMO_AGENTS if a["id"] == agent_id), None)

    def get_providers(self) -> List[Dict]:
        """Get providers from demo data or database."""
        if self.is_demo_mode:
            return DEMO_PROVIDERS
        if self._db:
            return self._db.get_providers()
        return DEMO_PROVIDERS

    def get_provider(self, provider_id: int) -> Optional[Dict]:
        """Get provider by ID from demo data or database."""
        if self.is_demo_mode:
            return next((p for p in DEMO_PROVIDERS if p["id"] == provider_id), None)
        if self._db:
            return self._db.get_provider(provider_id)
        return next((p for p in DEMO_PROVIDERS if p["id"] == provider_id), None)

    def get_models(self, provider_id: Optional[int] = None) -> List[Dict]:
        """Get models from demo data or database."""
        if self.is_demo_mode:
            models = DEMO_MODELS
            if provider_id:
                models = [m for m in models if m["provider_id"] == provider_id]
            return models
        if self._db:
            return self._db.get_models(provider_id)
        return DEMO_MODELS

    def get_model(self, model_id: int) -> Optional[Dict]:
        """Get model by ID from demo data or database."""
        if self.is_demo_mode:
            return next((m for m in DEMO_MODELS if m["id"] == model_id), None)
        if self._db:
            return self._db.get_model(model_id)
        return next((m for m in DEMO_MODELS if m["id"] == model_id), None)

    def get_circles(self, is_active: Optional[bool] = None) -> List[Dict]:
        """Get circles from demo data or database."""
        if self.is_demo_mode:
            circles = DEMO_CIRCLES
            if is_active is not None:
                circles = [c for c in circles if c["is_active"] == is_active]
            return circles
        if self._db:
            return self._db.get_circles(is_active)
        return DEMO_CIRCLES

    def get_circle(self, circle_id: int) -> Optional[Dict]:
        """Get circle by ID from demo data or database."""
        if self.is_demo_mode:
            return next((c for c in DEMO_CIRCLES if c["id"] == circle_id), None)
        if self._db:
            return self._db.get_circle(circle_id)
        return next((c for c in DEMO_CIRCLES if c["id"] == circle_id), None)

    def get_circle_members(self, circle_id: int) -> List[Dict]:
        """Get circle members from demo data or database."""
        if self.is_demo_mode:
            return [m for m in DEMO_CIRCLE_MEMBERS if m["circle_id"] == circle_id]
        if self._db:
            return self._db.get_circle_members(circle_id)
        return [m for m in DEMO_CIRCLE_MEMBERS if m["circle_id"] == circle_id]

    def get_circle_tasks(self, circle_id: int, status: Optional[str] = None) -> List[Dict]:
        """Get circle tasks from demo data or database."""
        if self.is_demo_mode:
            tasks = [t for t in DEMO_CIRCLE_TASKS if t["circle_id"] == circle_id]
            if status:
                tasks = [t for t in tasks if t["status"] == status]
            return tasks
        if self._db:
            return self._db.get_circle_tasks(circle_id, status)
        return [t for t in DEMO_CIRCLE_TASKS if t["circle_id"] == circle_id]


_data_service: Optional[DataService] = None


@lru_cache()
def get_data_service() -> DataService:
    """Get or create the data service singleton."""
    global _data_service
    if _data_service is None:
        try:
            db = get_database_service()
            _data_service = DataService(db)
        except Exception:
            _data_service = DataService(None)
    return _data_service


# =============================================================================
# Global instances (singleton pattern)
# =============================================================================

_memory_service: Optional[MemoryService] = None
_agent_registry: Optional[AgentRegistry] = None
_circle_registry: Optional[CircleRegistry] = None
_conversation_registry: Optional[ConversationRegistry] = None


@lru_cache()
def get_memory_service() -> MemoryService:
    """Get or create the global memory service.

    Uses PostgresMemoryStore if database and OpenAI API key are configured,
    otherwise falls back to InMemoryStore.
    """
    global _memory_service
    if _memory_service is None:
        # Try to use PostgreSQL-backed store if configured
        try:
            if os.getenv("OPENAI_API_KEY") and (os.getenv("DATABASE_URL") or os.getenv("DB_HOST")):
                from gathering.agents.postgres_store import PostgresMemoryStore
                store = PostgresMemoryStore.from_env()
                _memory_service = MemoryService(store=store)
                print("MemoryService: Using PostgreSQL + pgvector")
            else:
                _memory_service = MemoryService()
                print("MemoryService: Using InMemoryStore (no DB/OpenAI config)")
        except Exception as e:
            print(f"MemoryService: Falling back to InMemoryStore ({e})")
            _memory_service = MemoryService()
    return _memory_service


@lru_cache()
def get_agent_registry() -> AgentRegistry:
    """Get or create the global agent registry."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry


@lru_cache()
def get_circle_registry() -> CircleRegistry:
    """Get or create the global circle registry."""
    global _circle_registry
    if _circle_registry is None:
        _circle_registry = CircleRegistry()
    return _circle_registry


@lru_cache()
def get_conversation_registry() -> ConversationRegistry:
    """Get or create the global conversation registry."""
    global _conversation_registry
    if _conversation_registry is None:
        _conversation_registry = ConversationRegistry()
    return _conversation_registry


def get_circle(name: str = "default") -> Optional[GatheringCircle]:
    """Get a circle by name."""
    registry = get_circle_registry()
    return registry.get(name)


def reset_registries():
    """Reset all registries (for testing)."""
    global _memory_service, _agent_registry, _circle_registry, _conversation_registry, _data_service
    _memory_service = None
    _agent_registry = None
    _circle_registry = None
    _conversation_registry = None
    _data_service = None
    get_memory_service.cache_clear()
    get_agent_registry.cache_clear()
    get_circle_registry.cache_clear()
    get_conversation_registry.cache_clear()
    get_data_service.cache_clear()
