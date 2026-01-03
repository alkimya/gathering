"""
FastAPI dependencies for dependency injection.
"""

import os
from typing import Dict, Optional, List, Any
from functools import lru_cache

from gathering.orchestration import GatheringCircle
from gathering.agents import MemoryService, AgentWrapper

# Import pycopg (local PostgreSQL wrapper)
from pycopg import Database as PycopgDatabase, Config as PycopgConfig


# =============================================================================
# Database Connection
# =============================================================================


class DatabaseService:
    """Database service for API using pycopg."""

    _instance: Optional['DatabaseService'] = None

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()

        # Support DATABASE_URL (used in CI) or individual DB_* vars
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Parse postgresql://user:password@host:port/database
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            self._config = PycopgConfig(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/') or 'gathering',
                user=parsed.username or 'postgres',
                password=parsed.password or '',
            )
        else:
            self._config = PycopgConfig(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                database=os.getenv('DB_NAME', 'gathering'),
                user=os.getenv('DB_USER', 'loc'),
                password=os.getenv('DB_PASSWORD', ''),
            )
        self._db = PycopgDatabase(self._config)

    @property
    def db(self) -> PycopgDatabase:
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
        """Get agent by ID with full persona details."""
        return self.execute_one("""
            SELECT
                a.*,
                (SELECT COUNT(*) FROM memory.memories mem WHERE mem.agent_id = a.id AND mem.is_active = TRUE) AS memory_count,
                (SELECT COUNT(*) FROM communication.chat_history ch WHERE ch.agent_id = a.id) AS message_count,
                (SELECT COUNT(*) FROM circle.members cm WHERE cm.agent_id = a.id AND cm.is_active = TRUE) AS circle_count
            FROM agent.agents_full a
            WHERE a.id = %(id)s
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

    # Circle persistence methods
    def get_circle_by_name(self, name: str) -> Optional[Dict]:
        """Get circle by name."""
        return self.execute_one("""
            SELECT c.*,
                   COUNT(DISTINCT m.agent_id) as member_count,
                   COUNT(DISTINCT t.id) as task_count
            FROM circle.circles c
            LEFT JOIN circle.members m ON m.circle_id = c.id AND m.is_active = true
            LEFT JOIN circle.tasks t ON t.circle_id = c.id
            WHERE c.name = %(name)s AND c.is_active = true
            GROUP BY c.id
        """, {'name': name})

    def create_circle(self, name: str, require_review: bool = True, auto_route: bool = True) -> Optional[Dict]:
        """Create a new circle in the database."""
        return self.execute_one("""
            INSERT INTO circle.circles (name, display_name, require_review, auto_route, status)
            VALUES (%(name)s, %(name)s, %(require_review)s, %(auto_route)s, 'stopped')
            RETURNING *
        """, {'name': name, 'require_review': require_review, 'auto_route': auto_route})

    def update_circle_status(self, name: str, status: str) -> bool:
        """Update circle status."""
        result = self.execute("""
            UPDATE circle.circles
            SET status = %(status)s::circle_status,
                started_at = CASE WHEN %(status)s = 'running' THEN NOW() ELSE started_at END,
                stopped_at = CASE WHEN %(status)s = 'stopped' THEN NOW() ELSE stopped_at END
            WHERE name = %(name)s AND is_active = true
            RETURNING id
        """, {'name': name, 'status': status})
        return len(result) > 0

    def delete_circle(self, name: str) -> bool:
        """Soft delete a circle."""
        result = self.execute("""
            UPDATE circle.circles
            SET is_active = false, stopped_at = NOW()
            WHERE name = %(name)s AND is_active = true
            RETURNING id
        """, {'name': name})
        return len(result) > 0

    def add_circle_member(self, circle_name: str, agent_id: int, competencies: List[str] = None,
                          can_review: List[str] = None) -> Optional[Dict]:
        """Add an agent to a circle."""
        circle = self.get_circle_by_name(circle_name)
        if not circle:
            return None
        return self.execute_one("""
            INSERT INTO circle.members (circle_id, agent_id, competencies, can_review)
            VALUES (%(circle_id)s, %(agent_id)s, %(competencies)s, %(can_review)s)
            ON CONFLICT (circle_id, agent_id) DO UPDATE SET
                is_active = true,
                competencies = EXCLUDED.competencies,
                can_review = EXCLUDED.can_review
            RETURNING *
        """, {
            'circle_id': circle['id'],
            'agent_id': agent_id,
            'competencies': competencies or [],
            'can_review': can_review or []
        })

    def remove_circle_member(self, circle_name: str, agent_id: int) -> bool:
        """Remove an agent from a circle."""
        circle = self.get_circle_by_name(circle_name)
        if not circle:
            return False
        result = self.execute("""
            UPDATE circle.members
            SET is_active = false, left_at = NOW()
            WHERE circle_id = %(circle_id)s AND agent_id = %(agent_id)s
            RETURNING id
        """, {'circle_id': circle['id'], 'agent_id': agent_id})
        return len(result) > 0

    def get_active_circles(self) -> List[Dict]:
        """Get all active circles with their members."""
        return self.execute("""
            SELECT c.*
            FROM circle.circles c
            WHERE c.is_active = true
            ORDER BY c.created_at DESC
        """)

    def get_circle_members_with_info(self, circle_id: int) -> List[Dict]:
        """Get circle members with agent info."""
        return self.execute("""
            SELECT m.*, a.name as agent_name,
                   p.name as provider_name, mod.model_name, mod.model_alias
            FROM circle.members m
            JOIN agent.agents a ON a.id = m.agent_id
            LEFT JOIN agent.models mod ON a.model_id = mod.id
            LEFT JOIN agent.providers p ON mod.provider_id = p.id
            WHERE m.circle_id = %(circle_id)s AND m.is_active = true
        """, {'circle_id': circle_id})

    # Conversation persistence methods
    def create_conversation(self, conv_data: dict) -> Optional[Dict]:
        """Create a new conversation in the database."""
        # Get circle_id from circle name if provided
        circle_id = None
        circle_name = conv_data.get('circle_name')
        if circle_name:
            circle = self.get_circle_by_name(circle_name)
            if circle:
                circle_id = circle['id']

        return self.execute_one("""
            INSERT INTO communication.conversations (
                circle_id, topic, conversation_type, participant_agent_ids,
                participant_names, max_turns, turn_strategy, initial_prompt,
                status, turns_taken
            )
            VALUES (
                %(circle_id)s, %(topic)s, 'collaboration', %(agent_ids)s,
                %(participant_names)s, %(max_turns)s, %(turn_strategy)s,
                %(initial_prompt)s, %(status)s, %(turns_taken)s
            )
            RETURNING *
        """, {
            'circle_id': circle_id,
            'topic': conv_data.get('topic', ''),
            'agent_ids': conv_data.get('agent_ids', []),
            'participant_names': conv_data.get('participant_names', []),
            'max_turns': conv_data.get('max_turns', 20),
            'turn_strategy': conv_data.get('turn_strategy', 'round_robin'),
            'initial_prompt': conv_data.get('initial_prompt'),
            'status': conv_data.get('status', 'pending'),
            'turns_taken': conv_data.get('turns_taken', 0),
        })

    def get_conversation(self, conv_id: int) -> Optional[Dict]:
        """Get a conversation by ID with its messages."""
        conv = self.execute_one("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM communication.messages m WHERE m.conversation_id = c.id) as message_count
            FROM communication.conversations c
            WHERE c.id = %(id)s AND c.is_active = true
        """, {'id': conv_id})
        return conv

    def get_conversation_messages(self, conv_id: int) -> List[Dict]:
        """Get all messages for a conversation."""
        return self.execute("""
            SELECT m.*
            FROM communication.messages m
            WHERE m.conversation_id = %(conv_id)s
            ORDER BY m.created_at
        """, {'conv_id': conv_id})

    def add_conversation_message(self, conv_id: int, msg_data: dict) -> Optional[Dict]:
        """Add a message to a conversation."""
        agent_id = msg_data.get('agent_id')
        # agent_id 0 means user message
        role = 'user' if agent_id == 0 else 'assistant'

        return self.execute_one("""
            INSERT INTO communication.messages (
                conversation_id, role, agent_id, agent_name, content, mentions
            )
            VALUES (
                %(conv_id)s, %(role)s::message_role, %(agent_id)s,
                %(agent_name)s, %(content)s, %(mentions)s
            )
            RETURNING *
        """, {
            'conv_id': conv_id,
            'role': role,
            'agent_id': agent_id if agent_id and agent_id > 0 else None,
            'agent_name': msg_data.get('agent_name', 'Unknown'),
            'content': msg_data.get('content', ''),
            'mentions': msg_data.get('mentions', []),
        })

    def update_conversation(self, conv_id: int, data: dict) -> bool:
        """Update a conversation."""
        updates = []
        params = {'id': conv_id}

        if 'status' in data:
            updates.append("status = %(status)s::conversation_status")
            params['status'] = data['status']
        if 'turns_taken' in data:
            updates.append("turns_taken = %(turns_taken)s")
            params['turns_taken'] = data['turns_taken']
        if 'summary' in data:
            updates.append("summary = %(summary)s")
            params['summary'] = data['summary']
        if 'started_at' in data:
            updates.append("started_at = %(started_at)s")
            params['started_at'] = data['started_at']
        if 'completed_at' in data:
            updates.append("completed_at = %(completed_at)s")
            params['completed_at'] = data['completed_at']

        if not updates:
            return False

        sql = f"UPDATE communication.conversations SET {', '.join(updates)} WHERE id = %(id)s RETURNING id"
        result = self.execute(sql, params)
        return len(result) > 0

    def get_active_conversations(self) -> List[Dict]:
        """Get all active conversations."""
        return self.execute("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM communication.messages m WHERE m.conversation_id = c.id) as message_count,
                   ci.name as circle_name
            FROM communication.conversations c
            LEFT JOIN circle.circles ci ON ci.id = c.circle_id
            WHERE c.is_active = true
            ORDER BY c.created_at DESC
        """)

    def delete_conversation(self, conv_id: int) -> bool:
        """Soft delete a conversation."""
        result = self.execute("""
            UPDATE communication.conversations
            SET is_active = false
            WHERE id = %(id)s
            RETURNING id
        """, {'id': conv_id})
        return len(result) > 0

    # Agent memory methods - for conversation history and task tracking
    def get_agent_conversations(self, agent_id: int, limit: int = 10) -> List[Dict]:
        """Get recent conversations where an agent participated."""
        return self.execute("""
            SELECT DISTINCT
                c.id,
                c.topic,
                c.status::TEXT as status,
                c.turns_taken,
                c.started_at,
                c.completed_at,
                c.summary,
                (SELECT COUNT(*) FROM communication.messages m
                 WHERE m.conversation_id = c.id AND m.agent_id = %(agent_id)s) as my_message_count,
                (SELECT COUNT(*) FROM communication.messages m
                 WHERE m.conversation_id = c.id) as total_messages
            FROM communication.conversations c
            JOIN communication.messages m ON m.conversation_id = c.id
            WHERE m.agent_id = %(agent_id)s AND c.is_active = true
            ORDER BY c.started_at DESC NULLS LAST
            LIMIT %(limit)s
        """, {'agent_id': agent_id, 'limit': limit})

    def get_agent_conversation_messages(self, agent_id: int, limit: int = 50) -> List[Dict]:
        """Get recent messages sent by an agent across all conversations."""
        return self.execute("""
            SELECT
                m.id,
                m.conversation_id,
                m.content,
                m.created_at,
                c.topic as conversation_topic
            FROM communication.messages m
            JOIN communication.conversations c ON c.id = m.conversation_id
            WHERE m.agent_id = %(agent_id)s AND c.is_active = true
            ORDER BY m.created_at DESC
            LIMIT %(limit)s
        """, {'agent_id': agent_id, 'limit': limit})

    def get_agent_tasks(self, agent_id: int, limit: int = 20) -> List[Dict]:
        """Get tasks assigned to or completed by an agent."""
        return self.execute("""
            SELECT
                t.id,
                t.title,
                t.description,
                t.status::TEXT as status,
                t.priority::TEXT as priority,
                t.started_at,
                t.completed_at,
                t.result,
                c.name as circle_name,
                c.display_name as circle_display_name
            FROM circle.tasks t
            JOIN circle.circles c ON c.id = t.circle_id
            WHERE t.assigned_agent_id = %(agent_id)s
            ORDER BY t.created_at DESC
            LIMIT %(limit)s
        """, {'agent_id': agent_id, 'limit': limit})

    def get_agent_recent_activity(self, agent_id: int) -> Dict[str, Any]:
        """Get a summary of recent agent activity for context injection."""
        # Get counts
        stats = self.execute_one("""
            SELECT
                (SELECT COUNT(*) FROM communication.messages m
                 WHERE m.agent_id = %(agent_id)s) as total_messages,
                (SELECT COUNT(*) FROM circle.tasks t
                 WHERE t.assigned_agent_id = %(agent_id)s AND t.status = 'completed') as completed_tasks,
                (SELECT COUNT(*) FROM circle.tasks t
                 WHERE t.assigned_agent_id = %(agent_id)s AND t.status = 'in_progress') as active_tasks,
                (SELECT COUNT(DISTINCT c.id) FROM communication.conversations c
                 JOIN communication.messages m ON m.conversation_id = c.id
                 WHERE m.agent_id = %(agent_id)s) as conversations_participated
        """, {'agent_id': agent_id}) or {}

        # Get recent conversations (last 5)
        recent_convs = self.get_agent_conversations(agent_id, limit=5)

        # Get recent tasks (last 10)
        recent_tasks = self.get_agent_tasks(agent_id, limit=10)

        return {
            'stats': stats,
            'recent_conversations': recent_convs,
            'recent_tasks': recent_tasks,
        }


def build_agent_memory_context(activity: Dict[str, Any]) -> str:
    """Build a memory context string for injection into agent prompts.

    Args:
        activity: Dict from get_agent_recent_activity()

    Returns:
        Formatted string for inclusion in system prompt
    """
    lines = ["## Mémoire et Historique"]

    stats = activity.get('stats', {})
    if stats:
        lines.append("\n### Statistiques")
        if stats.get('total_messages'):
            lines.append(f"- Messages envoyés: {stats['total_messages']}")
        if stats.get('completed_tasks'):
            lines.append(f"- Tâches complétées: {stats['completed_tasks']}")
        if stats.get('active_tasks'):
            lines.append(f"- Tâches en cours: {stats['active_tasks']}")
        if stats.get('conversations_participated'):
            lines.append(f"- Conversations participées: {stats['conversations_participated']}")

    # Recent conversations
    recent_convs = activity.get('recent_conversations', [])
    if recent_convs:
        lines.append("\n### Conversations Récentes")
        for conv in recent_convs[:5]:
            topic = conv.get('topic') or 'Sans sujet'
            status = conv.get('status', 'unknown')
            my_msgs = conv.get('my_message_count', 0)
            summary = conv.get('summary')

            line = f"- [{status}] {topic}"
            if my_msgs:
                line += f" ({my_msgs} messages de ma part)"
            lines.append(line)

            if summary:
                lines.append(f"  Résumé: {summary[:200]}...")

    # Recent tasks
    recent_tasks = activity.get('recent_tasks', [])
    if recent_tasks:
        lines.append("\n### Tâches Récentes")
        for task in recent_tasks[:10]:
            title = task.get('title', 'Sans titre')
            status = task.get('status', 'unknown')
            circle = task.get('circle_display_name') or task.get('circle_name', '')
            result = task.get('result')

            line = f"- [{status}] {title}"
            if circle:
                line += f" (Circle: {circle})"
            lines.append(line)

            if result and status == 'completed':
                # Truncate long results
                result_preview = result[:150] + "..." if len(result) > 150 else result
                lines.append(f"  Résultat: {result_preview}")

    if len(lines) == 1:
        lines.append("\nAucun historique disponible pour le moment.")

    return "\n".join(lines)


_db_service: Optional[DatabaseService] = None


@lru_cache()
def get_database_service() -> DatabaseService:
    """Get or create the database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


class AgentRegistry:
    """Registry for managing agents across the API with database loading."""

    def __init__(self, db: Optional[DatabaseService] = None):
        self._agents: Dict[int, AgentWrapper] = {}
        self._next_id: int = 1
        self._db = db
        self._loaded = False

    def set_db(self, db: DatabaseService) -> None:
        """Set the database service (for lazy initialization)."""
        self._db = db

    def _ensure_loaded(self) -> None:
        """Ensure agents are loaded from database on first access."""
        if self._loaded or not self._db:
            return
        self._loaded = True
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load all agents from database."""
        if not self._db:
            return

        import logging
        logger = logging.getLogger(__name__)

        try:
            agents_data = self._db.get_agents()
            logger.info(f"Loading {len(agents_data)} agents from database")

            from gathering.agents import AgentPersona, AgentConfig, AgentWrapper
            from gathering.llm.providers import LLMProviderFactory
            from gathering.core.config import get_settings

            settings = get_settings()
            memory = get_memory_service()

            for agent_row in agents_data:
                try:
                    agent_id = agent_row['id']

                    # Get full agent details
                    full_agent = self._db.get_agent(agent_id)
                    if not full_agent:
                        continue

                    # Create persona
                    persona = AgentPersona(
                        name=full_agent.get('name', f'Agent-{agent_id}'),
                        role=full_agent.get('role', 'Assistant'),
                        traits=full_agent.get('traits') or [],
                        communication_style=full_agent.get('communication_style', 'professional'),
                        specializations=full_agent.get('specializations') or [],
                        languages=full_agent.get('languages') or ['English'],
                    )

                    # Get provider and model info
                    provider_name = full_agent.get('provider_name', 'anthropic') or 'anthropic'
                    model_name = full_agent.get('model_alias') or full_agent.get('model_name') or 'claude-sonnet-4'

                    # Create config
                    config = AgentConfig(
                        provider=provider_name,
                        model=model_name,
                        max_tokens=full_agent.get('max_tokens') or 4096,
                        temperature=full_agent.get('temperature') or 0.7,
                    )

                    # Create LLM provider
                    api_key = settings.get_llm_api_key(provider_name)
                    llm = None

                    if api_key:
                        try:
                            llm = LLMProviderFactory.create(provider_name, {
                                "api_key": api_key,
                                "model": model_name,
                                "max_tokens": config.max_tokens,
                                "temperature": config.temperature,
                            })
                        except Exception as e:
                            logger.warning(f"Failed to create LLM for agent {agent_id}: {e}")

                    if not llm:
                        # Mock LLM fallback
                        class MockLLM:
                            def complete(self, messages, **kwargs):
                                return {"content": f"LLM not configured for {provider_name}"}
                        llm = MockLLM()

                    # Create agent wrapper
                    agent = AgentWrapper(
                        agent_id=agent_id,
                        persona=persona,
                        llm=llm,
                        memory=memory,
                        config=config,
                    )

                    # Load skills from database for this agent
                    try:
                        from gathering.skills.registry import SkillRegistry
                        from gathering.agents.project_context import load_project_context

                        # Get skill_names from the agent row in DB
                        skill_row = self._db.execute_one(
                            "SELECT skill_names FROM agent.agents WHERE id = %(id)s",
                            {'id': agent_id}
                        )
                        skill_names = skill_row.get('skill_names') or [] if skill_row else []

                        # Fallback to core skills if none configured
                        if not skill_names:
                            skill_names = ["filesystem", "git", "code"]

                        project_path = "/home/loc/workspace/gathering"

                        for skill_name in skill_names:
                            try:
                                skill = SkillRegistry.get(
                                    skill_name,
                                    config={"working_dir": project_path, "allowed_paths": [project_path]},
                                )
                                agent.add_skill(skill)
                            except Exception as skill_err:
                                logger.warning(f"Failed to load skill {skill_name} for agent {agent_id}: {skill_err}")

                        # Set default project context
                        project = load_project_context(project_name="gathering")
                        if project:
                            agent.set_project(project)
                            logger.debug(f"Set project context for agent {agent_id}")

                    except Exception as skill_err:
                        logger.warning(f"Failed to load skills for agent {agent_id}: {skill_err}")

                    self._agents[agent_id] = agent
                    if agent_id >= self._next_id:
                        self._next_id = agent_id + 1

                    logger.debug(f"Loaded agent {agent_id}: {persona.name} with skills")

                except Exception as e:
                    logger.error(f"Failed to load agent {agent_row.get('id')}: {e}")

            logger.info(f"Loaded {len(self._agents)} agents into registry")

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load agents from database: {e}")

    def add(self, agent: AgentWrapper) -> int:
        """Add an agent to the registry."""
        self._ensure_loaded()
        agent_id = agent.agent_id
        self._agents[agent_id] = agent
        if agent_id >= self._next_id:
            self._next_id = agent_id + 1
        return agent_id

    def get(self, agent_id: int) -> Optional[AgentWrapper]:
        """Get an agent by ID."""
        self._ensure_loaded()
        return self._agents.get(agent_id)

    def remove(self, agent_id: int) -> bool:
        """Remove an agent from the registry."""
        self._ensure_loaded()
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def list_all(self) -> list:
        """List all agents."""
        self._ensure_loaded()
        return list(self._agents.values())

    def count(self) -> int:
        """Count agents."""
        self._ensure_loaded()
        return len(self._agents)

    def next_id(self) -> int:
        """Get next available ID."""
        self._ensure_loaded()
        next_id = self._next_id
        self._next_id += 1
        return next_id


class CircleRegistry:
    """Registry for managing circles across the API with database persistence."""

    def __init__(self, db: Optional[DatabaseService] = None):
        self._circles: Dict[str, GatheringCircle] = {}
        self._circle_metadata: Dict[str, Dict[str, Any]] = {}  # Store DB metadata (project_id, etc.)
        self._db = db
        self._loaded = False

    def set_db(self, db: DatabaseService) -> None:
        """Set the database service (for lazy initialization)."""
        self._db = db

    def _ensure_loaded(self) -> None:
        """Ensure circles are loaded from database on first access."""
        if self._loaded or not self._db:
            return
        self._loaded = True
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load all active circles from database."""
        if not self._db:
            return

        import logging
        logger = logging.getLogger(__name__)

        try:
            circles_data = self._db.get_active_circles()
            logger.info(f"Loading {len(circles_data)} circles from database")

            for circle_row in circles_data:
                try:
                    # Create GatheringCircle from DB data
                    circle = GatheringCircle(
                        name=circle_row['name'],
                        require_review=circle_row.get('require_review', True),
                        auto_route=circle_row.get('auto_route', True),
                    )

                    # Load members
                    members = self._db.get_circle_members_with_info(circle_row['id'])
                    for member in members:
                        from gathering.orchestration import AgentHandle
                        from gathering.llm.providers import LLMProviderFactory
                        from gathering.core.config import get_settings

                        settings = get_settings()
                        provider_name = member.get('provider_name', 'anthropic') or 'anthropic'
                        model_name = member.get('model_name') or member.get('model_alias') or 'claude-sonnet-4'
                        api_key = settings.get_llm_api_key(provider_name)

                        process_message_callback = None
                        if api_key:
                            try:
                                llm_provider = LLMProviderFactory.create(provider_name, {
                                    "api_key": api_key,
                                    "model": model_name,
                                    "max_tokens": 4096,
                                    "temperature": 0.7,
                                })

                                agent_name_local = member['agent_name']
                                agent_id_local = member['agent_id']

                                # Load agent system prompt and skills from DB
                                agent_data = self._db.get_agent(agent_id_local)
                                system_prompt = None
                                skill_names = []
                                if agent_data:
                                    system_prompt = agent_data.get('system_prompt') or agent_data.get('base_prompt')
                                    # skill_names is in the base table, not the view
                                    skill_row = self._db.execute_one(
                                        "SELECT skill_names FROM agent.agents WHERE id = %(id)s",
                                        {'id': agent_id_local}
                                    )
                                    if skill_row:
                                        skill_names = skill_row.get('skill_names') or []

                                # Build full system prompt with project context and memory
                                from gathering.agents.project_context import GATHERING_PROJECT
                                project_context = GATHERING_PROJECT.to_prompt()

                                # Get agent's memory/activity context
                                agent_activity = self._db.get_agent_recent_activity(agent_id_local)
                                memory_context = build_agent_memory_context(agent_activity)

                                # Build skills info for system prompt
                                skills_info = ""
                                if skill_names:
                                    skills_info = f"\n\n## Skills Disponibles\nTu as accès aux skills suivants: {', '.join(skill_names)}"

                                if system_prompt:
                                    full_system_prompt = f"{system_prompt}\n\n## Contexte Projet\n{project_context}\n\n{memory_context}{skills_info}"
                                else:
                                    full_system_prompt = f"""Tu es {agent_name_local}, un assistant IA expert.

## Contexte Projet
{project_context}

{memory_context}{skills_info}

Réponds de manière concise et constructive. Tu as accès au contexte du projet ci-dessus.
Tu peux référencer les fichiers, la structure, et les conventions du projet.
Tu peux aussi te référer à tes conversations et tâches passées dans ta mémoire.
Si tu as des skills disponibles, utilise les outils appropriés pour accomplir les tâches."""

                                # Create callback with skills support
                                process_message_callback = self._create_agent_callback_with_skills(
                                    llm=llm_provider,
                                    agent_name=agent_name_local,
                                    system_prompt=full_system_prompt,
                                    skill_names=skill_names,
                                    logger=logger,
                                    agent_id=member['agent_id'],
                                )
                            except Exception as e:
                                logger.warning(f"Failed to create LLM for agent {member['agent_id']}: {e}")

                        handle = AgentHandle(
                            id=member['agent_id'],
                            name=member['agent_name'],
                            provider=provider_name,
                            model=model_name,
                            competencies=member.get('competencies') or [],
                            can_review=member.get('can_review') or [],
                            process_message=process_message_callback,
                        )
                        circle.add_agent(handle)

                    self._circles[circle.name] = circle
                    # Store metadata from DB (project_id, etc.)
                    self._circle_metadata[circle.name] = {
                        'id': circle_row.get('id'),
                        'project_id': circle_row.get('project_id'),
                    }
                    logger.info(f"Loaded circle '{circle.name}' with {len(circle.agents)} agents")

                except Exception as e:
                    logger.error(f"Failed to load circle {circle_row['name']}: {e}")

        except Exception as e:
            logger.error(f"Failed to load circles from database: {e}")

    def _create_agent_callback_with_skills(
        self,
        llm,
        agent_name: str,
        system_prompt: str,
        skill_names: List[str],
        logger,
        agent_id: int = None,
    ):
        """Create a callback function with skills support for an agent.

        This enables agents to use tools during conversations.
        """
        from gathering.skills.registry import SkillRegistry

        # Agent context for skill traceability (e.g., git trailers)
        agent_context = {
            "agent_name": agent_name,
            "agent_id": agent_id,
        }

        # Load tools from skills
        tools = []
        skill_tool_map = {}  # tool_name -> skill_name

        if skill_names:
            try:
                for skill_name in skill_names:
                    try:
                        skill = SkillRegistry.get(skill_name, config={
                            "working_dir": "/home/loc/workspace/gathering"
                        })
                        skill_tools = skill.get_tools_definition()
                        for tool in skill_tools:
                            tool_name = tool.get("name")
                            if tool_name:
                                skill_tool_map[tool_name] = skill_name
                        tools.extend(skill_tools)
                        logger.info(f"Loaded {len(skill_tools)} tools from skill '{skill_name}' for {agent_name}")
                    except Exception as e:
                        logger.warning(f"Could not load skill '{skill_name}' for {agent_name}: {e}")
            except Exception as e:
                logger.warning(f"Error loading skills for {agent_name}: {e}")

        async def process_message(prompt: str) -> str:
            """Process a message with optional tool use."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            # If no tools, simple completion
            if not tools:
                response = llm.complete(messages)
                return response.get("content", "No response generated")

            # With tools, do an agentic loop
            max_iterations = 10
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Call LLM with tools
                response = llm.complete(messages, tools=tools)

                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])

                # If no tool calls, we're done
                if not tool_calls:
                    return content if content else "No response generated"

                # Log tool usage for debugging
                logger.debug(f"[{agent_name}] Iteration {iteration}: {len(tool_calls)} tool call(s)")

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": tool_calls,
                })

                # Execute each tool
                for tool_call in tool_calls:
                    tool_id = tool_call.get("id", "")
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})

                    # Find skill and execute tool
                    skill_name = skill_tool_map.get(tool_name)
                    result_str = ""

                    if skill_name:
                        try:
                            skill = SkillRegistry.get(skill_name, config={
                                "working_dir": "/home/loc/workspace/gathering"
                            })
                            # Pass agent context for traceability
                            skill.context = agent_context
                            result = skill.execute(tool_name, tool_args)

                            # Format result
                            if result.success:
                                if result.data:
                                    import json
                                    result_str = json.dumps(result.data, ensure_ascii=False, indent=2)
                                else:
                                    result_str = result.message
                            else:
                                result_str = f"Error: {result.error or result.message}"
                        except Exception as e:
                            result_str = f"Tool execution error: {str(e)}"
                    else:
                        result_str = f"Unknown tool: {tool_name}"

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_use_id": tool_id,
                        "name": tool_name,
                        "content": result_str,
                    })

            # If we hit max iterations, return last content with warning
            logger.warning(f"[{agent_name}] Hit max tool iterations ({max_iterations})")
            if content:
                return content + f"\n\n[Limite de {max_iterations} itérations d'outils atteinte]"
            return f"[Erreur: Limite de {max_iterations} itérations d'outils atteinte sans réponse finale]"

        return process_message

    def add(self, circle: GatheringCircle, persist: bool = True) -> str:
        """Add a circle to the registry and optionally persist to DB."""
        self._ensure_loaded()
        self._circles[circle.name] = circle

        if persist and self._db:
            # Persist to database
            self._db.create_circle(
                name=circle.name,
                require_review=circle.require_review,
                auto_route=circle.auto_route,
            )

        return circle.name

    def get(self, name: str) -> Optional[GatheringCircle]:
        """Get a circle by name."""
        self._ensure_loaded()
        return self._circles.get(name)

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Get circle metadata (project_id, etc.) by name."""
        self._ensure_loaded()
        return self._circle_metadata.get(name, {})

    def get_project_name(self, name: str) -> Optional[str]:
        """Get the project name associated with a circle."""
        metadata = self.get_metadata(name)
        project_id = metadata.get('project_id')
        if project_id and self._db:
            project = self._db.get_project(project_id)
            if project:
                return project.get('name')
        return None

    def remove(self, name: str, persist: bool = True) -> bool:
        """Remove a circle from the registry and optionally from DB."""
        self._ensure_loaded()
        if name in self._circles:
            del self._circles[name]
            if persist and self._db:
                self._db.delete_circle(name)
            return True
        return False

    def update_status(self, name: str, status: str) -> bool:
        """Update circle status in database."""
        if self._db:
            return self._db.update_circle_status(name, status)
        return False

    def add_member(self, circle_name: str, agent_id: int, competencies: List[str] = None,
                   can_review: List[str] = None) -> bool:
        """Add a member to circle in database.

        Note: If the agent doesn't exist in DB (e.g., in-memory only during tests),
        the persistence is skipped silently. The in-memory circle still has the agent.
        """
        if self._db:
            try:
                result = self._db.add_circle_member(circle_name, agent_id, competencies, can_review)
                return result is not None
            except Exception as e:
                # Ignore FK violations - agent may exist in memory only (tests, dynamic agents)
                import logging
                logging.getLogger(__name__).debug(f"Could not persist circle member: {e}")
                return False
        return False

    def remove_member(self, circle_name: str, agent_id: int) -> bool:
        """Remove a member from circle in database."""
        if self._db:
            return self._db.remove_circle_member(circle_name, agent_id)
        return False

    def list_all(self) -> list:
        """List all circles."""
        self._ensure_loaded()
        return list(self._circles.values())

    def count(self) -> int:
        """Count circles."""
        self._ensure_loaded()
        return len(self._circles)


class ConversationRegistry:
    """Registry for managing conversations with database persistence."""

    def __init__(self, db: Optional[DatabaseService] = None):
        self._conversations: Dict[str, dict] = {}
        self._db = db
        self._loaded = False

    def set_db(self, db: DatabaseService) -> None:
        """Set the database service (for lazy initialization)."""
        self._db = db

    def _ensure_loaded(self) -> None:
        """Ensure conversations are loaded from database on first access."""
        if self._loaded or not self._db:
            return
        self._loaded = True
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load all active conversations from database."""
        if not self._db:
            return

        import logging
        logger = logging.getLogger(__name__)

        try:
            convs_data = self._db.get_active_conversations()
            logger.info(f"Loading {len(convs_data)} conversations from database")

            for conv_row in convs_data:
                try:
                    conv_id = str(conv_row['id'])

                    # Load messages for this conversation
                    messages_data = self._db.get_conversation_messages(conv_row['id'])
                    messages = []
                    for msg in messages_data:
                        messages.append({
                            "agent_id": msg.get('agent_id') or 0,
                            "agent_name": msg.get('agent_name', 'User'),
                            "content": msg.get('content', ''),
                            "mentions": msg.get('mentions', []),
                            "timestamp": msg.get('created_at'),
                        })

                    # Convert DB row to conversation dict
                    conv_dict = {
                        "id": conv_id,
                        "db_id": conv_row['id'],
                        "topic": conv_row.get('topic', ''),
                        "agent_ids": conv_row.get('participant_agent_ids', []),
                        "participant_names": conv_row.get('participant_names', []),
                        "max_turns": conv_row.get('max_turns', 20),
                        "turn_strategy": conv_row.get('turn_strategy', 'round_robin'),
                        "initial_prompt": conv_row.get('initial_prompt'),
                        "circle_name": conv_row.get('circle_name'),  # Loaded from JOIN
                        "status": conv_row.get('status', 'pending'),
                        "turns_taken": conv_row.get('turns_taken', 0),
                        "messages": messages,
                        "transcript": "",
                        "started_at": conv_row.get('started_at'),
                        "completed_at": conv_row.get('completed_at'),
                        "duration_seconds": 0,
                    }

                    self._conversations[conv_id] = conv_dict
                    logger.info(f"Loaded conversation {conv_id} with {len(messages)} messages")

                except Exception as e:
                    logger.error(f"Failed to load conversation {conv_row.get('id')}: {e}")

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load conversations from database: {e}")

    def add(self, conversation_data: dict) -> str:
        """Add a conversation and persist to DB."""
        self._ensure_loaded()

        # Create in database first
        if self._db:
            db_conv = self._db.create_conversation(conversation_data)
            if db_conv:
                conv_id = str(db_conv['id'])
                conversation_data["id"] = conv_id
                conversation_data["db_id"] = db_conv['id']
            else:
                # Fallback to memory-only
                conv_id = f"conv-{len(self._conversations) + 1}"
                conversation_data["id"] = conv_id
        else:
            conv_id = f"conv-{len(self._conversations) + 1}"
            conversation_data["id"] = conv_id

        self._conversations[conv_id] = conversation_data
        return conv_id

    def get(self, conv_id: str) -> Optional[dict]:
        """Get a conversation by ID."""
        self._ensure_loaded()
        return self._conversations.get(conv_id)

    def update(self, conv_id: str, data: dict) -> bool:
        """Update a conversation and persist to DB."""
        self._ensure_loaded()
        if conv_id not in self._conversations:
            return False

        conv = self._conversations[conv_id]
        conv.update(data)

        # Persist to DB
        if self._db and 'db_id' in conv:
            db_id = conv['db_id']

            # Update conversation metadata
            db_updates = {}
            if 'status' in data:
                status_val = data['status']
                if hasattr(status_val, 'value'):
                    status_val = status_val.value
                db_updates['status'] = status_val
            if 'turns_taken' in data:
                db_updates['turns_taken'] = data['turns_taken']
            if 'started_at' in data:
                db_updates['started_at'] = data['started_at']
            if 'completed_at' in data:
                db_updates['completed_at'] = data['completed_at']

            if db_updates:
                self._db.update_conversation(db_id, db_updates)

            # If messages were updated, persist new ones
            if 'messages' in data:
                # Get existing message count
                existing_msgs = self._db.get_conversation_messages(db_id)
                existing_count = len(existing_msgs)
                new_messages = data['messages'][existing_count:]

                for msg in new_messages:
                    self._db.add_conversation_message(db_id, msg)

        return True

    def remove(self, conv_id: str) -> bool:
        """Remove a conversation."""
        self._ensure_loaded()
        if conv_id not in self._conversations:
            return False

        conv = self._conversations[conv_id]
        if self._db and 'db_id' in conv:
            self._db.delete_conversation(conv['db_id'])

        del self._conversations[conv_id]
        return True

    def list_all(self) -> list:
        """List all conversations."""
        self._ensure_loaded()
        return list(self._conversations.values())

    def count(self) -> int:
        """Count conversations."""
        self._ensure_loaded()
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
    """Get or create the global agent registry with database loading."""
    global _agent_registry
    if _agent_registry is None:
        db = get_database_service()
        _agent_registry = AgentRegistry(db=db)
    return _agent_registry


@lru_cache()
def get_circle_registry() -> CircleRegistry:
    """Get or create the global circle registry with database persistence."""
    global _circle_registry
    if _circle_registry is None:
        db = get_database_service()
        _circle_registry = CircleRegistry(db=db)
    return _circle_registry


@lru_cache()
def get_conversation_registry() -> ConversationRegistry:
    """Get or create the global conversation registry with database persistence."""
    global _conversation_registry
    if _conversation_registry is None:
        db = get_database_service()
        _conversation_registry = ConversationRegistry(db=db)
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
