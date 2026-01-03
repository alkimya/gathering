"""
Tests for Background Tasks API router.

Covers:
- List background tasks with filters
- Get single task details
- Create new background task
- Pause/Resume/Cancel operations
- Get task steps
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime


@pytest.fixture
def mock_db_service():
    """Create mock database service."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_agent_registry():
    """Create mock agent registry."""
    mock = Mock()
    mock.get.return_value = None
    return mock


@pytest.fixture
def client(mock_db_service, mock_agent_registry):
    """Create test client with mocked dependencies."""
    from fastapi import FastAPI
    from gathering.api.routers.background_tasks import router
    from gathering.api.dependencies import get_database_service, get_agent_registry

    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    app.dependency_overrides[get_database_service] = lambda: mock_db_service
    app.dependency_overrides[get_agent_registry] = lambda: mock_agent_registry

    yield TestClient(app)

    # Reset mocks after each test
    mock_db_service.reset_mock()
    mock_agent_registry.reset_mock()


class TestListBackgroundTasks:
    """Test listing background tasks."""

    def test_list_empty(self, client, mock_db_service):
        """Test listing when no tasks exist."""
        mock_db_service.execute.side_effect = [
            [],  # tasks query
            [],  # counts query
        ]

        response = client.get("/background-tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_list_with_tasks(self, client, mock_db_service):
        """Test listing tasks."""
        mock_db_service.execute.side_effect = [
            [
                {
                    "id": 1,
                    "agent_id": 1,
                    "goal": "Test goal",
                    "status": "running",
                    "current_step": 5,
                    "max_steps": 50,
                    "progress_percent": 10,
                    "created_at": datetime.now(),
                }
            ],
            [{"status": "running", "count": 1}],
        ]

        response = client.get("/background-tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["goal"] == "Test goal"

    def test_list_with_status_filter(self, client, mock_db_service):
        """Test listing with status filter."""
        mock_db_service.execute.side_effect = [[], []]

        response = client.get("/background-tasks?status=completed")

        assert response.status_code == 200
        # Verify execute was called
        assert mock_db_service.execute.called

    def test_list_with_agent_filter(self, client, mock_db_service):
        """Test listing with agent filter."""
        mock_db_service.execute.side_effect = [[], []]

        response = client.get("/background-tasks?agent_id=1")

        assert response.status_code == 200


class TestGetBackgroundTask:
    """Test getting single task details."""

    def test_get_existing_task(self, client, mock_db_service):
        """Test getting existing task."""
        mock_db_service.execute_one.return_value = {
            "id": 1,
            "agent_id": 1,
            "goal": "Test goal",
            "status": "running",
            "current_step": 5,
            "max_steps": 50,
            "progress_percent": 10,
            "created_at": datetime.now(),
        }

        response = client.get("/background-tasks/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["goal"] == "Test goal"

    def test_get_nonexistent_task(self, client, mock_db_service):
        """Test getting nonexistent task."""
        mock_db_service.execute_one.return_value = None

        response = client.get("/background-tasks/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCreateBackgroundTask:
    """Test creating background tasks."""

    def test_create_task_agent_not_found(self, client, mock_agent_registry):
        """Test creating task with nonexistent agent."""
        mock_agent_registry.get.return_value = None

        response = client.post(
            "/background-tasks",
            json={
                "agent_id": 999,
                "goal": "Test goal",
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("gathering.api.routers.background_tasks.get_background_executor")
    def test_create_task_success(self, mock_get_executor, client, mock_db_service, mock_agent_registry):
        """Test successful task creation."""
        # Setup mocks
        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent_registry.get.return_value = mock_agent

        mock_executor = Mock()
        mock_executor.start_task = AsyncMock(return_value=123)
        mock_get_executor.return_value = mock_executor

        mock_db_service.execute_one.return_value = {
            "id": 123,
            "agent_id": 1,
            "goal": "Test goal",
            "status": "pending",
            "current_step": 0,
            "max_steps": 50,
            "progress_percent": 0,
            "created_at": datetime.now(),
        }

        response = client.post(
            "/background-tasks",
            json={
                "agent_id": 1,
                "goal": "Test goal",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 123


class TestTaskOperations:
    """Test task control operations (pause, resume, cancel)."""

    @patch("gathering.api.routers.background_tasks.get_background_executor")
    def test_pause_task(self, mock_get_executor, client, mock_db_service):
        """Test pausing a task."""
        mock_executor = Mock()
        mock_executor.pause_task = AsyncMock(return_value=True)
        mock_get_executor.return_value = mock_executor

        mock_db_service.execute_one.return_value = {
            "id": 1,
            "status": "paused",
            "created_at": datetime.now(),
        }

        response = client.post("/background-tasks/1/pause")

        assert response.status_code == 200

    @patch("gathering.api.routers.background_tasks.get_background_executor")
    def test_resume_task(self, mock_get_executor, client, mock_db_service, mock_agent_registry):
        """Test resuming a task."""
        mock_executor = Mock()
        mock_executor.resume_task = AsyncMock(return_value=True)
        mock_get_executor.return_value = mock_executor

        mock_agent = Mock()
        mock_agent_registry.get.return_value = mock_agent

        mock_db_service.execute_one.side_effect = [
            {"id": 1, "agent_id": 1, "status": "paused", "created_at": datetime.now()},
            {"id": 1, "status": "running", "created_at": datetime.now()},
        ]

        response = client.post("/background-tasks/1/resume")

        assert response.status_code == 200

    @patch("gathering.api.routers.background_tasks.get_background_executor")
    def test_cancel_task(self, mock_get_executor, client, mock_db_service):
        """Test canceling a task."""
        mock_executor = Mock()
        mock_executor.cancel_task = AsyncMock(return_value=True)
        mock_get_executor.return_value = mock_executor

        mock_db_service.execute_one.return_value = {
            "id": 1,
            "status": "cancelled",
            "created_at": datetime.now(),
        }

        response = client.post("/background-tasks/1/cancel")

        assert response.status_code == 200


class TestTaskSteps:
    """Test task steps endpoints."""

    def test_get_task_steps(self, client, mock_db_service):
        """Test getting task steps."""
        # First execute_one: task existence check
        # Second execute_one: count query
        mock_db_service.execute_one.side_effect = [
            {"id": 1},  # Task exists
            {"count": 1},  # Total count
        ]
        # execute: steps query
        mock_db_service.execute.return_value = [
            {
                "id": 1,
                "task_id": 1,
                "step_number": 1,
                "action_type": "tool_call",
                "tool_name": "search",
                "success": True,
                "created_at": datetime.now(),
            }
        ]

        response = client.get("/background-tasks/1/steps")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["steps"]) == 1

    def test_get_task_steps_not_found(self, client, mock_db_service):
        """Test getting steps for nonexistent task."""
        mock_db_service.execute_one.return_value = None

        response = client.get("/background-tasks/999/steps")

        assert response.status_code == 404
