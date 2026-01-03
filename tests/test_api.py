"""
Tests for the GatheRing REST API.
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from gathering.api.main import create_app
from gathering.api.dependencies import (
    reset_registries,
    get_agent_registry,
    get_circle_registry,
    get_conversation_registry,
    get_memory_service,
)
from gathering.orchestration import GatheringCircle, AgentHandle


@pytest.fixture(autouse=True)
def clean_registries():
    """Reset all registries before each test."""
    reset_registries()
    yield
    reset_registries()


@pytest.fixture
def app():
    """Create a test app with auth disabled for business logic tests."""
    return create_app(
        enable_websocket=False,
        enable_auth=False,  # Disable auth for business logic tests
        enable_rate_limit=False,  # Disable rate limiting for tests
        enable_logging=False,  # Disable logging noise in tests
    )


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# =============================================================================
# Health Endpoints
# =============================================================================


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data
        # Counts can be 0 or more depending on database state
        assert "agents_count" in data
        assert "circles_count" in data
        assert isinstance(data["agents_count"], int)
        assert isinstance(data["circles_count"], int)

    def test_readiness_check(self, client):
        """Test readiness probe."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True

    def test_liveness_check(self, client):
        """Test liveness probe."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["alive"] is True

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["docs"] == "/docs"


# =============================================================================
# Agent Endpoints
# =============================================================================


class TestAgentEndpoints:
    """Tests for agent management endpoints."""

    def test_list_agents_empty(self, client):
        """Test listing agents when none exist."""
        response = client.get("/agents")
        assert response.status_code == 200

        data = response.json()
        assert data["agents"] == []
        assert data["total"] == 0

    def test_create_agent(self, client):
        """Test creating an agent."""
        response = client.post("/agents", json={
            "persona": {
                "name": "Claude",
                "role": "Architect",
                "traits": ["rigoureux", "pédagogue"],
                "communication_style": "detailed",
                "specializations": ["python", "architecture"],
                "languages": ["fr", "en"],
            },
            "config": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "temperature": 0.7,
            },
        })

        assert response.status_code == 201
        data = response.json()

        assert data["id"] == 1
        assert data["name"] == "Claude"
        assert data["role"] == "Architect"
        assert data["provider"] == "anthropic"
        assert "persona" in data
        assert "config" in data

    def test_get_agent(self, client):
        """Test getting an agent by ID."""
        # Create first
        client.post("/agents", json={
            "persona": {"name": "Test", "role": "Tester"},
        })

        response = client.get("/agents/1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test"

    def test_get_agent_not_found(self, client):
        """Test getting non-existent agent."""
        response = client.get("/agents/999")
        assert response.status_code == 404

    def test_update_agent(self, client):
        """Test updating an agent."""
        # Create first
        client.post("/agents", json={
            "persona": {"name": "Original", "role": "Tester"},
        })

        response = client.patch("/agents/1", json={
            "persona": {
                "name": "Updated",
                "role": "Developer",
                "traits": [],
                "communication_style": "concise",
                "specializations": [],
                "languages": ["en"],
            },
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["role"] == "Developer"

    def test_delete_agent(self, client):
        """Test deleting an agent."""
        # Create first
        client.post("/agents", json={
            "persona": {"name": "ToDelete", "role": "Tester"},
        })

        response = client.delete("/agents/1")
        assert response.status_code == 204

        # Verify deleted
        response = client.get("/agents/1")
        assert response.status_code == 404

    def test_list_agents(self, client):
        """Test listing multiple agents."""
        client.post("/agents", json={"persona": {"name": "Agent1", "role": "A"}})
        client.post("/agents", json={"persona": {"name": "Agent2", "role": "B"}})

        response = client.get("/agents")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert len(data["agents"]) == 2

    def test_get_agent_status(self, client):
        """Test getting agent status."""
        client.post("/agents", json={
            "persona": {"name": "StatusAgent", "role": "Tester"},
        })

        response = client.get("/agents/1/status")
        assert response.status_code == 200

        data = response.json()
        assert data["agent_id"] == 1
        assert data["name"] == "StatusAgent"
        assert "session" in data
        assert "is_processing" in data


# =============================================================================
# Circle Endpoints
# =============================================================================


class TestCircleEndpoints:
    """Tests for circle orchestration endpoints."""

    def test_list_circles(self, client):
        """Test listing circles returns valid structure."""
        response = client.get("/circles")
        assert response.status_code == 200

        data = response.json()
        assert "circles" in data
        assert "total" in data
        assert isinstance(data["circles"], list)
        assert isinstance(data["total"], int)
        assert data["total"] == len(data["circles"])

    def test_create_circle(self, client):
        """Test creating a circle."""
        circle_name = f"test-circle-{uuid.uuid4().hex[:8]}"
        response = client.post("/circles", json={
            "name": circle_name,
            "require_review": True,
            "auto_route": True,
            "max_concurrent_tasks": 5,
        })

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == circle_name
        assert data["require_review"] is True
        assert data["auto_route"] is True
        assert data["status"] == "stopped"

    def test_create_duplicate_circle(self, client):
        """Test creating duplicate circle fails."""
        circle_name = f"dup-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})

        response = client.post("/circles", json={"name": circle_name})
        assert response.status_code == 409

    def test_get_circle(self, client):
        """Test getting a circle by name."""
        circle_name = f"my-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})

        response = client.get(f"/circles/{circle_name}")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == circle_name
        assert "agents" in data

    def test_get_circle_not_found(self, client):
        """Test getting non-existent circle."""
        response = client.get("/circles/nonexistent")
        assert response.status_code == 404

    def test_start_circle(self, client):
        """Test starting a circle."""
        circle_name = f"start-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})

        response = client.post(f"/circles/{circle_name}/start")
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    def test_stop_circle(self, client):
        """Test stopping a circle."""
        circle_name = f"stop-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})
        client.post(f"/circles/{circle_name}/start")

        response = client.post(f"/circles/{circle_name}/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

    def test_add_agent_to_circle(self, client):
        """Test adding an agent to a circle."""
        circle_name = f"agent-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})

        response = client.post(
            f"/circles/{circle_name}/agents",
            params={
                "agent_id": 1,
                "agent_name": "Claude",
                "provider": "anthropic",
                "model": "claude-sonnet",
                "competencies": "python,architecture",
                "can_review": "code",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "added"

    def test_remove_agent_from_circle(self, client):
        """Test removing an agent from a circle."""
        circle_name = f"remove-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})
        client.post(
            f"/circles/{circle_name}/agents",
            params={"agent_id": 1, "agent_name": "Test"},
        )

        response = client.delete(f"/circles/{circle_name}/agents/1")
        assert response.status_code == 200
        assert response.json()["status"] == "removed"

    def test_delete_circle(self, client):
        """Test deleting a circle."""
        circle_name = f"delete-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})

        response = client.delete(f"/circles/{circle_name}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/circles/{circle_name}")
        assert response.status_code == 404


# =============================================================================
# Task Endpoints
# =============================================================================


class TestTaskEndpoints:
    """Tests for task management endpoints."""

    @pytest.fixture
    def running_circle(self, client):
        """Create and start a circle with agents."""
        circle_name = f"task-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})
        client.post(
            f"/circles/{circle_name}/agents",
            params={
                "agent_id": 1,
                "agent_name": "Worker",
                "competencies": "python",
            },
        )
        client.post(f"/circles/{circle_name}/start")
        return circle_name

    def test_create_task(self, client, running_circle):
        """Test creating a task."""
        response = client.post(f"/circles/{running_circle}/tasks", json={
            "title": "Test Task",
            "description": "A test task",
            "required_competencies": ["python"],
            "priority": 7,
        })

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Test Task"
        assert data["priority"] == 7

    def test_create_task_circle_not_running(self, client):
        """Test creating task in stopped circle fails."""
        circle_name = f"stopped-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})

        response = client.post(f"/circles/{circle_name}/tasks", json={
            "title": "Test",
        })

        assert response.status_code == 400

    def test_list_tasks(self, client, running_circle):
        """Test listing tasks."""
        client.post(f"/circles/{running_circle}/tasks", json={"title": "Task 1"})
        client.post(f"/circles/{running_circle}/tasks", json={"title": "Task 2"})

        response = client.get(f"/circles/{running_circle}/tasks")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2

    def test_get_task(self, client, running_circle):
        """Test getting a task by ID."""
        create_resp = client.post(
            f"/circles/{running_circle}/tasks",
            json={"title": "Get Task"},
        )
        task_id = create_resp.json()["id"]

        response = client.get(f"/circles/{running_circle}/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Get Task"

    def test_get_circle_metrics(self, client, running_circle):
        """Test getting circle metrics."""
        response = client.get(f"/circles/{running_circle}/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "agents" in data
        assert "total_tasks" in data


# =============================================================================
# Conversation Endpoints
# =============================================================================


class TestConversationEndpoints:
    """Tests for conversation endpoints."""

    @pytest.fixture
    def circle_with_agents(self, client):
        """Create a circle with multiple agents."""
        circle_name = f"conv-circle-{uuid.uuid4().hex[:8]}"
        client.post("/circles", json={"name": circle_name})
        client.post(
            f"/circles/{circle_name}/agents",
            params={"agent_id": 1, "agent_name": "Agent1"},
        )
        client.post(
            f"/circles/{circle_name}/agents",
            params={"agent_id": 2, "agent_name": "Agent2"},
        )
        client.post(f"/circles/{circle_name}/start")
        return circle_name

    def test_list_conversations(self, client):
        """Test listing conversations returns valid structure."""
        response = client.get("/conversations")
        assert response.status_code == 200

        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert isinstance(data["conversations"], list)
        assert isinstance(data["total"], int)

    def test_create_conversation(self, client, circle_with_agents):
        """Test creating a conversation."""
        response = client.post(
            "/conversations",
            params={"circle_name": circle_with_agents},
            json={
                "topic": "Test conversation",
                "agent_ids": [1, 2],
                "max_turns": 5,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["topic"] == "Test conversation"
        assert data["status"] == "pending"
        assert "Agent1" in data["participant_names"]
        assert "Agent2" in data["participant_names"]

    def test_create_conversation_circle_not_found(self, client):
        """Test creating conversation with non-existent circle."""
        response = client.post(
            "/conversations",
            params={"circle_name": "nonexistent"},
            json={
                "topic": "Test",
                "agent_ids": [1, 2],
            },
        )

        assert response.status_code == 404

    def test_get_conversation(self, client, circle_with_agents):
        """Test getting a conversation."""
        create_resp = client.post(
            "/conversations",
            params={"circle_name": circle_with_agents},
            json={
                "topic": "Get test",
                "agent_ids": [1, 2],
            },
        )
        conv_id = create_resp.json()["id"]

        response = client.get(f"/conversations/{conv_id}")
        assert response.status_code == 200
        assert response.json()["topic"] == "Get test"

    def test_cancel_conversation(self, client, circle_with_agents):
        """Test cancelling a conversation."""
        create_resp = client.post(
            "/conversations",
            params={"circle_name": circle_with_agents},
            json={
                "topic": "Cancel test",
                "agent_ids": [1, 2],
            },
        )
        conv_id = create_resp.json()["id"]

        response = client.post(f"/conversations/{conv_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_delete_conversation(self, client, circle_with_agents):
        """Test deleting a conversation."""
        create_resp = client.post(
            "/conversations",
            params={"circle_name": circle_with_agents},
            json={
                "topic": "Delete test",
                "agent_ids": [1, 2],
            },
        )
        conv_id = create_resp.json()["id"]

        response = client.delete(f"/conversations/{conv_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/conversations/{conv_id}")
        assert response.status_code == 404

    def test_get_transcript(self, client, circle_with_agents):
        """Test getting conversation transcript."""
        create_resp = client.post(
            "/conversations",
            params={"circle_name": circle_with_agents},
            json={
                "topic": "Transcript test",
                "agent_ids": [1, 2],
            },
        )
        conv_id = create_resp.json()["id"]

        response = client.get(f"/conversations/{conv_id}/transcript")
        assert response.status_code == 200

        data = response.json()
        assert data["conversation_id"] == conv_id
        assert data["topic"] == "Transcript test"


# =============================================================================
# WebSocket Tests
# =============================================================================


class TestWebSocketManager:
    """Tests for WebSocket manager."""

    def test_ws_manager_import(self):
        """Test WebSocket manager can be imported."""
        from gathering.api.websocket import ws_manager, WebSocketManager
        assert isinstance(ws_manager, WebSocketManager)

    @pytest.mark.asyncio
    async def test_ws_manager_connection_count(self):
        """Test connection count starts at zero."""
        from gathering.api.websocket import WebSocketManager
        manager = WebSocketManager()
        assert manager.connection_count == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestAPIIntegration:
    """Integration tests for API workflows."""

    def test_full_workflow(self, client):
        """Test a complete workflow: create circle, add agents, create task."""
        circle_name = f"workflow-circle-{uuid.uuid4().hex[:8]}"

        # Create circle
        response = client.post("/circles", json={"name": circle_name})
        assert response.status_code == 201

        # Add agents
        client.post(
            f"/circles/{circle_name}/agents",
            params={
                "agent_id": 1,
                "agent_name": "Architect",
                "competencies": "architecture,python",
                "can_review": "code",
            },
        )
        client.post(
            f"/circles/{circle_name}/agents",
            params={
                "agent_id": 2,
                "agent_name": "Developer",
                "competencies": "python,testing",
                "can_review": "code",
            },
        )

        # Start circle
        response = client.post(f"/circles/{circle_name}/start")
        assert response.status_code == 200

        # Create task
        response = client.post(f"/circles/{circle_name}/tasks", json={
            "title": "Implement feature",
            "required_competencies": ["python"],
        })
        assert response.status_code == 201

        # Check metrics
        response = client.get(f"/circles/{circle_name}/metrics")
        assert response.status_code == 200
        assert response.json()["total_tasks"] >= 1

        # Get circle details
        response = client.get(f"/circles/{circle_name}")
        assert response.status_code == 200
        assert response.json()["agent_count"] == 2
