"""
Tests for agent persistence components.
Tests AgentPersona, ProjectContext, AgentSession, MemoryService, AgentWrapper, and Resume.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from gathering.agents import (
    # Persona
    AgentPersona,
    ARCHITECT_PERSONA,
    SENIOR_DEV_PERSONA,
    CODE_SPECIALIST_PERSONA,
    # Project Context
    ProjectContext,
    GATHERING_PROJECT,
    # Session
    AgentSession,
    InjectedContext,
    # Memory
    MemoryService,
    MemoryEntry,
    InMemoryStore,
    build_agent_context,
    # Wrapper
    AgentWrapper,
    AgentConfig,
    AgentResponse,
    # Resume
    ResumeContext,
    ResumeStrategy,
    SessionResumeManager,
    InMemorySessionPersistence,
    create_resume_prompt,
)


class TestAgentPersona:
    """Tests for AgentPersona."""

    def test_persona_creation(self):
        """Test basic persona creation."""
        persona = AgentPersona(
            name="TestAgent",
            role="Tester",
            traits=["rigoureux", "précis"],
            communication_style="technical",
        )

        assert persona.name == "TestAgent"
        assert persona.role == "Tester"
        assert len(persona.traits) == 2
        assert persona.communication_style == "technical"

    def test_build_system_prompt(self):
        """Test system prompt building."""
        persona = AgentPersona(
            name="Claude",
            role="Architecte",
            base_prompt="Tu es un expert.",
            traits=["analytique"],
            communication_style="detailed",
            specializations=["python", "architecture"],
        )

        prompt = persona.build_system_prompt()

        assert "Tu es un expert" in prompt
        assert "Claude" in prompt
        assert "Architecte" in prompt
        assert "python" in prompt

    def test_build_prompt_with_project(self):
        """Test prompt with project context."""
        persona = AgentPersona(name="Agent", role="Dev")
        project = ProjectContext(
            name="TestProject",
            path="/test",
            venv_path="/test/venv",
        )

        prompt = persona.build_system_prompt(project)

        assert "TestProject" in prompt
        assert "/test" in prompt

    def test_predefined_personas(self):
        """Test predefined personas exist and are valid."""
        assert ARCHITECT_PERSONA.name == "Architecte"
        assert "architecture" in ARCHITECT_PERSONA.specializations

        assert SENIOR_DEV_PERSONA.name == "Dev Senior"
        assert "python" in SENIOR_DEV_PERSONA.specializations

        assert CODE_SPECIALIST_PERSONA.name == "Spécialiste Code"
        assert "optimization" in CODE_SPECIALIST_PERSONA.specializations

    def test_persona_serialization(self):
        """Test to_dict and from_dict."""
        persona = AgentPersona(
            id=1,
            name="Agent",
            role="Tester",
            traits=["a", "b"],
            specializations=["python"],
        )

        data = persona.to_dict()
        restored = AgentPersona.from_dict(data)

        assert restored.id == persona.id
        assert restored.name == persona.name
        assert restored.traits == persona.traits


class TestProjectContext:
    """Tests for ProjectContext."""

    def test_project_context_creation(self):
        """Test basic project context creation."""
        project = ProjectContext(
            name="MyProject",
            path="/home/user/project",
            venv_path="/home/user/project/venv",
            python_version="3.11",
        )

        assert project.name == "MyProject"
        assert project.venv_path is not None

    def test_to_prompt(self):
        """Test prompt generation."""
        project = ProjectContext(
            name="TestProject",
            path="/test",
            tools={"testing": "pytest", "database": "picopg"},
            conventions={"primary_keys": "IDENTITY"},
            notes=["Important note"],
        )

        prompt = project.to_prompt()

        assert "TestProject" in prompt
        assert "pytest" in prompt
        assert "picopg" in prompt
        assert "IDENTITY" in prompt
        assert "Important note" in prompt

    def test_add_methods(self):
        """Test helper methods for adding data."""
        project = ProjectContext(name="Test", path="/test")

        project.add_note("Note 1")
        project.add_tool("orm", "sqlalchemy")
        project.add_convention("style", "pep8")
        project.add_key_file("config", "src/config.py")
        project.add_command("test", "pytest")

        assert "Note 1" in project.notes
        assert project.tools["orm"] == "sqlalchemy"
        assert project.conventions["style"] == "pep8"
        assert project.key_files["config"] == "src/config.py"
        assert project.commands["test"] == "pytest"

    def test_gathering_project_constant(self):
        """Test pre-configured GATHERING_PROJECT."""
        assert GATHERING_PROJECT.name.lower() == "gathering"
        assert "pycopg" in GATHERING_PROJECT.tools["database"] or "picopg" in GATHERING_PROJECT.tools["database"]
        assert "pytest" in GATHERING_PROJECT.tools["testing"]

    def test_project_serialization(self):
        """Test to_dict and from_dict."""
        project = ProjectContext(
            id=1,
            name="Test",
            path="/test",
            tools={"a": "b"},
        )

        data = project.to_dict()
        restored = ProjectContext.from_dict(data)

        assert restored.id == project.id
        assert restored.name == project.name
        assert restored.tools == project.tools


class TestAgentSession:
    """Tests for AgentSession."""

    def test_session_creation(self):
        """Test basic session creation."""
        session = AgentSession(agent_id=1, project_id=10)

        assert session.agent_id == 1
        assert session.project_id == 10
        assert session.status == "active"
        assert len(session.recent_messages) == 0

    def test_add_message(self):
        """Test adding messages to session."""
        session = AgentSession(agent_id=1)

        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there")

        assert len(session.recent_messages) == 2
        assert session.last_message == "Hello"
        assert session.last_response == "Hi there"

    def test_message_limit(self):
        """Test message sliding window."""
        session = AgentSession(agent_id=1, max_messages=5)

        for i in range(10):
            session.add_message("user", f"Message {i}")

        assert len(session.recent_messages) == 5

    def test_working_files(self):
        """Test file tracking."""
        session = AgentSession(agent_id=1)

        session.add_working_file("src/main.py")
        session.add_working_file("src/utils.py")
        assert len(session.working_files) == 2

        session.remove_working_file("src/main.py")
        assert len(session.working_files) == 1

    def test_pending_actions(self):
        """Test action tracking."""
        session = AgentSession(agent_id=1)

        session.add_pending_action("Write tests")
        session.add_pending_action("Review code")
        assert len(session.pending_actions) == 2

        session.complete_action("Write tests")
        assert len(session.pending_actions) == 1
        assert "Write tests" in session.completed_actions

    def test_current_task(self):
        """Test current task tracking."""
        session = AgentSession(agent_id=1)

        session.set_current_task(100, "Implement feature", "50%")
        assert session.current_task_id == 100
        assert session.current_task_title == "Implement feature"

        session.clear_current_task()
        assert session.current_task_id is None

    def test_needs_resume(self):
        """Test resume detection."""
        session = AgentSession(agent_id=1)

        # Recent activity - no resume needed
        assert session.needs_resume is False

        # Old activity - resume needed
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        assert session.needs_resume is True

    def test_generate_resume_summary(self):
        """Test resume summary generation."""
        session = AgentSession(agent_id=1)
        session.set_current_task(1, "Fix bug")
        session.add_pending_action("Write test")
        session.add_working_file("src/bug.py")
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)

        summary = session.generate_resume_summary()

        assert "Fix bug" in summary
        assert "Write test" in summary
        assert "src/bug.py" in summary

    def test_session_serialization(self):
        """Test to_dict and from_dict."""
        session = AgentSession(
            agent_id=1,
            project_id=10,
            status="active",
        )
        session.add_message("user", "Test")
        session.add_working_file("file.py")

        data = session.to_dict()
        restored = AgentSession.from_dict(data)

        assert restored.agent_id == session.agent_id
        assert restored.project_id == session.project_id
        assert len(restored.recent_messages) == 1


class TestInjectedContext:
    """Tests for InjectedContext."""

    def test_to_messages(self):
        """Test message building."""
        context = InjectedContext(
            system_prompt="You are helpful.",
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
        )

        messages = context.to_messages("New message")

        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[-1]["content"] == "New message"


class TestMemoryService:
    """Tests for MemoryService."""

    @pytest.fixture
    def memory_service(self):
        return MemoryService()

    def test_persona_caching(self, memory_service):
        """Test persona caching."""
        persona = AgentPersona(name="Test")
        memory_service.set_persona(1, persona)

        retrieved = memory_service.get_persona(1)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_project_caching(self, memory_service):
        """Test project caching."""
        project = ProjectContext(name="Test", path="/test")
        memory_service.set_project(1, project)

        retrieved = memory_service.get_project(1)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_session_management(self, memory_service):
        """Test session creation and retrieval."""
        session = memory_service.get_or_create_session(1, 10)
        assert session.agent_id == 1
        assert session.project_id == 10

        # Same session returned
        session2 = memory_service.get_or_create_session(1)
        assert session2 is session

    @pytest.mark.asyncio
    async def test_build_context(self, memory_service):
        """Test context building."""
        persona = AgentPersona(name="Agent", role="Dev")
        project = ProjectContext(name="Project", path="/test")

        memory_service.set_persona(1, persona)
        memory_service.set_project(10, project)

        context = await memory_service.build_context(
            agent_id=1,
            user_message="Hello",
            project_id=10,
        )

        assert context.system_prompt != ""
        assert "Agent" in context.system_prompt

    @pytest.mark.asyncio
    async def test_record_exchange(self, memory_service):
        """Test recording conversation exchanges."""
        await memory_service.record_exchange(
            agent_id=1,
            user_message="Hello",
            assistant_response="Hi",
        )

        session = memory_service.get_session(1)
        assert session is not None
        assert len(session.recent_messages) == 2

    @pytest.mark.asyncio
    async def test_remember_and_recall(self, memory_service):
        """Test memory storage and retrieval."""
        await memory_service.remember(1, "Important fact", "learning")
        await memory_service.remember(1, "Another fact", "learning")

        memories = await memory_service.recall(1, "important")
        assert len(memories) >= 1
        assert "Important fact" in memories[0]

    def test_file_tracking(self, memory_service):
        """Test file tracking through service."""
        memory_service.track_file(1, "src/main.py")
        session = memory_service.get_session(1)
        assert "src/main.py" in session.working_files

        memory_service.untrack_file(1, "src/main.py")
        assert "src/main.py" not in session.working_files

    def test_action_tracking(self, memory_service):
        """Test action tracking through service."""
        memory_service.add_pending_action(1, "Write tests")
        session = memory_service.get_session(1)
        assert "Write tests" in session.pending_actions

        memory_service.complete_action(1, "Write tests")
        assert "Write tests" not in session.pending_actions
        assert "Write tests" in session.completed_actions

    def test_task_tracking(self, memory_service):
        """Test task tracking through service."""
        memory_service.set_current_task(1, 100, "Task Title", "In progress")
        session = memory_service.get_session(1)
        assert session.current_task_id == 100

        memory_service.clear_current_task(1)
        assert session.current_task_id is None

    def test_export_import_session(self, memory_service):
        """Test session export and import."""
        memory_service.get_or_create_session(1)
        memory_service.track_file(1, "test.py")

        data = memory_service.export_session(1)
        assert data is not None

        # Create new service and import
        new_service = MemoryService()
        session = new_service.import_session(1, data)
        assert "test.py" in session.working_files


class TestInMemoryStore:
    """Tests for InMemoryStore."""

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.mark.asyncio
    async def test_store_memory(self, store):
        """Test storing memories."""
        memory_id = await store.store_memory(
            agent_id=1,
            content="Test memory",
            memory_type="learning",
            metadata={"importance": 0.8},
        )

        assert memory_id == 1

    @pytest.mark.asyncio
    async def test_search_memories(self, store):
        """Test searching memories."""
        await store.store_memory(1, "Python is great", "learning", {})
        await store.store_memory(1, "JavaScript is cool", "learning", {})

        results = await store.search_memories(1, "Python")
        assert len(results) == 1
        assert "Python" in results[0]["content"]

    @pytest.mark.asyncio
    async def test_get_recent_memories(self, store):
        """Test getting recent memories."""
        await store.store_memory(1, "Memory 1", "learning", {})
        await store.store_memory(1, "Memory 2", "decision", {})
        await store.store_memory(1, "Memory 3", "learning", {})

        recent = await store.get_recent_memories(1, limit=2)
        assert len(recent) == 2

        learning_only = await store.get_recent_memories(1, memory_types=["learning"])
        assert len(learning_only) == 2


class TestResumeContext:
    """Tests for ResumeContext."""

    def test_resume_context_creation(self):
        """Test basic resume context creation."""
        context = ResumeContext(
            summary="Summary here",
            working_files=["file1.py"],
            pending_actions=["Action 1"],
        )

        assert context.summary == "Summary here"
        assert len(context.working_files) == 1

    def test_to_prompt_full(self):
        """Test full resume prompt."""
        context = ResumeContext(
            time_away=timedelta(hours=2),
            current_task={"title": "Fix bug", "progress": "50%"},
            pending_actions=["Test", "Review"],
            working_files=["main.py"],
        )

        prompt = context.to_prompt(ResumeStrategy.FULL)

        assert "Fix bug" in prompt
        assert "Test" in prompt
        assert "main.py" in prompt

    def test_to_prompt_minimal(self):
        """Test minimal resume prompt."""
        context = ResumeContext(
            time_away=timedelta(hours=2),
            current_task={"title": "Fix bug"},
        )

        prompt = context.to_prompt(ResumeStrategy.MINIMAL)

        assert "Fix bug" in prompt
        assert len(prompt) < 200  # Should be short


class TestSessionResumeManager:
    """Tests for SessionResumeManager."""

    @pytest.fixture
    def manager(self):
        return SessionResumeManager()

    def test_needs_resume(self, manager):
        """Test resume detection."""
        session = AgentSession(agent_id=1)

        # Recent - no resume
        assert manager.needs_resume(session) is False

        # Old - needs resume
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        assert manager.needs_resume(session) is True

    def test_get_strategy(self, manager):
        """Test strategy selection."""
        session = AgentSession(agent_id=1)

        # With current task
        session.set_current_task(1, "Task")
        strategy = manager.get_strategy(session)
        assert strategy == ResumeStrategy.TASK_FOCUSED

        # Long absence
        session.clear_current_task()
        session.last_activity = datetime.now(timezone.utc) - timedelta(days=2)
        strategy = manager.get_strategy(session)
        assert strategy == ResumeStrategy.SUMMARY

    def test_build_resume_context(self, manager):
        """Test building resume context."""
        session = AgentSession(agent_id=1)
        session.set_current_task(100, "Test task")
        session.add_working_file("test.py")

        project = ProjectContext(name="Project", path="/test", notes=["Note 1"])

        context = manager.build_resume_context(session, project)

        assert context.current_task is not None
        assert context.current_task["id"] == 100
        assert "test.py" in context.working_files
        assert "Note 1" in context.project_notes

    def test_generate_resume_prompt(self, manager):
        """Test prompt generation."""
        session = AgentSession(agent_id=1)
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        session.set_current_task(1, "Important task")

        prompt = manager.generate_resume_prompt(session)

        assert "Important task" in prompt
        assert "Reprise" in prompt


class TestInMemorySessionPersistence:
    """Tests for InMemorySessionPersistence."""

    @pytest.fixture
    def persistence(self):
        return InMemorySessionPersistence()

    @pytest.mark.asyncio
    async def test_save_and_load(self, persistence):
        """Test saving and loading sessions."""
        session = AgentSession(agent_id=1, status="active")
        await persistence.save_session(session)

        loaded = await persistence.load_session(1)
        assert loaded is not None
        assert loaded.agent_id == 1

    @pytest.mark.asyncio
    async def test_list_sessions(self, persistence):
        """Test listing sessions."""
        await persistence.save_session(AgentSession(agent_id=1, status="active"))
        await persistence.save_session(AgentSession(agent_id=2, status="paused"))

        all_sessions = await persistence.list_sessions()
        assert len(all_sessions) == 2

        active_only = await persistence.list_sessions(status="active")
        assert len(active_only) == 1


class TestAgentWrapper:
    """Tests for AgentWrapper."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        llm = MagicMock()
        # complete() is sync and returns Dict[str, Any] per ILLMProvider interface
        llm.complete = MagicMock(return_value={
            "role": "assistant",
            "content": "Hello! I'm ready to help.",
        })
        return llm

    @pytest.fixture
    def agent(self, mock_llm):
        """Create an agent wrapper."""
        persona = AgentPersona(name="TestAgent", role="Tester")
        return AgentWrapper(
            agent_id=1,
            persona=persona,
            llm=mock_llm,
        )

    def test_agent_creation(self, agent):
        """Test agent creation."""
        assert agent.agent_id == 1
        assert agent.name == "TestAgent"
        assert agent.role == "Tester"

    def test_add_skill(self, agent):
        """Test adding skills."""
        skill = MagicMock()
        skill.name = "git"
        skill.tools = [{"name": "git_status"}]

        agent.add_skill(skill)

        assert "git" in agent._skills
        assert "git_status" in agent._tool_map

    def test_remove_skill(self, agent):
        """Test removing skills."""
        skill = MagicMock()
        skill.name = "git"
        skill.tools = [{"name": "git_status"}]

        agent.add_skill(skill)
        agent.remove_skill("git")

        assert "git" not in agent._skills

    def test_set_project(self, agent):
        """Test setting project context."""
        project = ProjectContext(name="TestProject", path="/test")
        agent.set_project(project, project_id=10)

        assert agent._project is not None
        assert agent._project.name == "TestProject"

    @pytest.mark.asyncio
    async def test_chat(self, agent, mock_llm):
        """Test chat method."""
        response = await agent.chat("Hello!")

        assert response.content == "Hello! I'm ready to help."
        assert response.model == agent.config.model
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_remember_and_recall(self, agent):
        """Test remember and recall."""
        await agent.remember("Important info", "learning")
        memories = await agent.recall("important")

        assert len(memories) >= 1

    def test_file_tracking(self, agent):
        """Test file tracking."""
        agent.track_file("test.py")
        assert "test.py" in agent.session.working_files

        agent.untrack_file("test.py")
        assert "test.py" not in agent.session.working_files

    def test_task_tracking(self, agent):
        """Test task tracking."""
        agent.set_current_task(100, "Test task", "In progress")
        assert agent.session.current_task_id == 100

        agent.clear_current_task()
        assert agent.session.current_task_id is None

    def test_get_status(self, agent):
        """Test getting agent status."""
        status = agent.get_status()

        assert status["agent_id"] == 1
        assert status["name"] == "TestAgent"
        assert "session" in status

    def test_export_state(self, agent):
        """Test exporting agent state."""
        state = agent.export_state()

        assert state["agent_id"] == 1
        assert "persona" in state
        assert "config" in state

    def test_from_state(self, mock_llm):
        """Test restoring agent from state."""
        persona = AgentPersona(name="OriginalAgent", role="Tester")
        original = AgentWrapper(agent_id=1, persona=persona, llm=mock_llm)
        original.track_file("important.py")

        state = original.export_state()

        restored = AgentWrapper.from_state(state, mock_llm)

        assert restored.agent_id == 1
        assert restored.name == "OriginalAgent"


@pytest.mark.asyncio
async def test_build_agent_context_helper():
    """Test the build_agent_context helper function."""
    persona = AgentPersona(name="Agent", role="Dev")
    project = ProjectContext(name="Project", path="/test")
    session = AgentSession(agent_id=1)
    session.add_message("user", "Previous message")

    context = await build_agent_context(
        agent_id=1,
        user_message="Current message",
        persona=persona,
        project=project,
        session=session,
    )

    assert context.system_prompt != ""
    assert len(context.history) == 1


def test_create_resume_prompt_helper():
    """Test the create_resume_prompt helper function."""
    session = AgentSession(agent_id=1)
    session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
    session.set_current_task(1, "Test task")

    prompt = create_resume_prompt(session)

    assert "Test task" in prompt
    assert "Reprise" in prompt
