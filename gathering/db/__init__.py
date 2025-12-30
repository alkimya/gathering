"""
Database module for GatheRing framework.
Provides PostgreSQL-based persistent storage with multi-schema architecture.

Schemas:
    - agent: Agents & Identity (agents, personas, sessions)
    - circle: Orchestration (circles, members, tasks, conflicts, events)
    - project: Projects (projects, files)
    - communication: Conversations (conversations, messages, chat_history)
    - memory: Memory & RAG (memories, knowledge_base) with pgvector
    - review: Reviews (reviews, comments, quality_metrics)
    - audit: Audit & Logs (logs, escalations)

Usage:
    from gathering.db import Database, init_db
    from gathering.db.models import Agent, Circle, Task, Memory

    # Initialize database
    db = Database.from_env()
    db.init_db()

    # Use with SQLAlchemy session
    with db.session() as session:
        agent = session.query(Agent).first()

    # Apply migrations
    from gathering.db.migrations import apply_migrations
    apply_migrations()

Note: Primary keys use BIGINT GENERATED ALWAYS AS IDENTITY (not UUID).
"""

from gathering.db.database import Database, init_db, get_db

# Import all models for easy access
from gathering.db.models import (
    # Base
    Base,

    # Enums
    AgentRole,
    MessageRole,
    TaskStatus,
    TaskPriority,
    ReviewStatus,
    ReviewType,
    MemoryScope,
    MemoryType,
    LogLevel,
    CircleStatus,
    ConversationStatus,

    # Agent schema
    Agent,
    Persona,
    Session,

    # Circle schema
    Circle,
    CircleMember,
    Task,
    TaskAssignment,
    Conflict,
    CircleEvent,

    # Project schema
    Project,
    ProjectFile,

    # Communication schema
    Conversation,
    Message,
    ChatHistory,

    # Memory schema
    Memory,
    KnowledgeBase,

    # Review schema
    Review,
    ReviewComment,
    QualityMetric,

    # Audit schema
    AuditLog,
    Escalation,
)

__all__ = [
    # Database
    "Database",
    "init_db",
    "get_db",
    "Base",

    # Enums
    "AgentRole",
    "MessageRole",
    "TaskStatus",
    "TaskPriority",
    "ReviewStatus",
    "ReviewType",
    "MemoryScope",
    "MemoryType",
    "LogLevel",
    "CircleStatus",
    "ConversationStatus",

    # Agent schema
    "Agent",
    "Persona",
    "Session",

    # Circle schema
    "Circle",
    "CircleMember",
    "Task",
    "TaskAssignment",
    "Conflict",
    "CircleEvent",

    # Project schema
    "Project",
    "ProjectFile",

    # Communication schema
    "Conversation",
    "Message",
    "ChatHistory",

    # Memory schema
    "Memory",
    "KnowledgeBase",

    # Review schema
    "Review",
    "ReviewComment",
    "QualityMetric",

    # Audit schema
    "AuditLog",
    "Escalation",
]
