"""
Integration test: Multi-agents working on a project with shared memory.

This test demonstrates the complete workflow:
1. Create a project
2. Create a circle for the project
3. Add agents to the circle
4. Agents share knowledge via circle-scoped memory
5. Agents work on project files with auto-resolved paths
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from gathering.agents.project_context import ProjectContext
from gathering.agents.wrapper import AgentWrapper, AgentConfig
from gathering.agents.persona import AgentPersona
from gathering.orchestration.circle_store import CircleStore


class MockLLM:
    """Mock LLM for testing."""

    def complete(self, messages, tools=None, **kwargs):
        return {
            "content": "Test response",
            "role": "assistant",
        }


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test-project"
        project_path.mkdir()

        # Create sample files
        (project_path / "README.md").write_text("# Test Project\n")
        (project_path / "src").mkdir()
        (project_path / "src" / "main.py").write_text("def main():\n    pass\n")

        yield str(project_path)


@pytest.mark.skipif(
    not os.getenv("DB_HOST"),
    reason="Requires PostgreSQL connection"
)
class TestProjectIntegration:
    """Integration tests for project-based multi-agent workflows."""

    def test_circle_with_project_id(self):
        """Test creating a circle linked to a project."""
        store = CircleStore.from_env()

        # Create circle with project_id
        circle_id = store.create_circle(
            name="test-circle-project",
            display_name="Test Circle with Project",
            project_id=1,  # Assuming project 1 exists
        )

        # Verify
        circle = store.get_circle(circle_id)
        assert circle is not None
        assert circle["project_id"] == 1

        # Cleanup
        store.delete_circle(circle_id)
        store.close()

    def test_task_with_project_id(self):
        """Test creating a task linked to a project."""
        store = CircleStore.from_env()

        # Create circle and task
        circle_id = store.create_circle(name="test-circle-task")
        task_id = store.create_task(
            circle_id=circle_id,
            title="Test task with project",
            project_id=1,
        )

        # Verify
        task = store.get_task(task_id)
        assert task is not None
        assert task["project_id"] == 1

        # Cleanup
        store.delete_circle(circle_id)
        store.close()

    def test_list_circles_by_project(self):
        """Test listing circles filtered by project_id."""
        store = CircleStore.from_env()

        # Create circles
        circle1_id = store.create_circle(name="circle-proj-1", project_id=1)
        circle2_id = store.create_circle(name="circle-proj-2", project_id=2)
        circle3_id = store.create_circle(name="circle-proj-none")

        # List by project
        circles_proj1 = store.list_circles(project_id=1)
        assert any(c["id"] == circle1_id for c in circles_proj1)
        assert not any(c["id"] == circle2_id for c in circles_proj1)

        # Cleanup
        store.delete_circle(circle1_id)
        store.delete_circle(circle2_id)
        store.delete_circle(circle3_id)
        store.close()


class TestAgentProjectIntegration:
    """Tests for AgentWrapper project integration."""

    def test_load_project_context(self, temp_project):
        """Test loading project context in agent."""
        # Create agent
        persona = AgentPersona(
            name="Test Agent",
            role="Developer",
            traits=["efficient"],
        )
        agent = AgentWrapper(
            agent_id=999,
            persona=persona,
            llm=MockLLM(),
            config=AgentConfig(allow_tools=False),
        )

        # Load project
        project = agent.load_project_context(temp_project, project_id=1)

        # Verify
        assert project is not None
        assert agent.get_project() == project
        assert agent.get_project_id() == 1
        assert project.path == temp_project

    def test_project_aware_path_resolution(self, temp_project):
        """Test that relative paths are resolved against project root."""
        persona = AgentPersona(
            name="Test Agent",
            role="Developer",
            traits=["efficient"],
        )
        agent = AgentWrapper(
            agent_id=999,
            persona=persona,
            llm=MockLLM(),
            config=AgentConfig(allow_tools=False),
        )

        # Load project
        agent.load_project_context(temp_project)

        # Test path resolution in _execute_tool (indirectly)
        from pathlib import Path

        # Simulate skill execution with relative path
        params = {"path": "src/main.py"}
        skill_name = "filesystem"

        # Add mock skill
        class MockSkill:
            async def execute(self, tool_name, **params):
                return {"resolved_path": params.get("path")}

        agent._skills[skill_name] = MockSkill()
        agent._tool_map["fs_read"] = skill_name

        # Execute tool with relative path
        import asyncio
        result = asyncio.run(agent._execute_tool("fs_read", params.copy()))

        # Verify path was resolved
        expected_path = str(Path(temp_project) / "src" / "main.py")
        assert result["resolved_path"] == expected_path


class TestWorkflowIntegration:
    """Test complete workflow: Project → Circle → Agents → Shared Memory."""

    def test_agent_project_context_in_prompt(self, temp_project):
        """Test that project context is injected in prompts."""
        persona = AgentPersona(
            name="Sophie",
            role="Developer",
            traits=["efficient"],
        )

        # Create mock LLM that captures system prompt
        captured_messages = []

        class CapturingLLM:
            def complete(self, messages, tools=None, **kwargs):
                captured_messages.extend(messages)
                return {"content": "Response", "role": "assistant"}

        agent = AgentWrapper(
            agent_id=999,
            persona=persona,
            llm=CapturingLLM(),
            config=AgentConfig(allow_tools=False),
        )

        # Load project
        project = ProjectContext.from_path(temp_project)
        agent.set_project(project)

        # Chat
        import asyncio
        asyncio.run(agent.chat("Hello", include_memories=False))

        # Verify project info in system prompt
        system_message = next(
            (m for m in captured_messages if m.get("role") == "system"),
            None
        )
        assert system_message is not None
        assert temp_project in system_message["content"]
