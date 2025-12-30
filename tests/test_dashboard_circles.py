"""
Tests for dashboard circle endpoints.
"""

import pytest
from unittest.mock import patch

from gathering.api.dependencies import (
    DataService,
    DEMO_CIRCLES,
    DEMO_CIRCLE_MEMBERS,
    DEMO_CIRCLE_TASKS,
)


class TestDataServiceCircles:
    """Test DataService circle methods in demo mode."""

    def test_get_circles_demo(self):
        """Should return demo circles."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            circles = data.get_circles()
            assert circles == DEMO_CIRCLES
            assert len(circles) == 3

    def test_get_circles_filtered_active(self):
        """Should filter circles by is_active."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            circles = data.get_circles(is_active=True)
            assert all(c["is_active"] is True for c in circles)

    def test_get_circle_demo(self):
        """Should return specific demo circle."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            circle = data.get_circle(1)
            assert circle is not None
            assert circle["name"] == "ai-research"
            assert circle["display_name"] == "AI Research Team"

    def test_get_circle_not_found(self):
        """Should return None for non-existent circle."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            circle = data.get_circle(999)
            assert circle is None

    def test_get_circle_members_demo(self):
        """Should return demo circle members."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            members = data.get_circle_members(1)
            assert len(members) == 2
            # Verify it's ai-research members
            agent_ids = {m["agent_id"] for m in members}
            assert agent_ids == {1, 2}  # Sophie and Olivia

    def test_get_circle_members_empty(self):
        """Should return empty list for circle with no members."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            members = data.get_circle_members(999)
            assert members == []

    def test_get_circle_tasks_demo(self):
        """Should return demo circle tasks."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            tasks = data.get_circle_tasks(1)
            assert len(tasks) == 3
            # Verify all tasks belong to circle 1
            assert all(t["circle_id"] == 1 for t in tasks)

    def test_get_circle_tasks_filtered_by_status(self):
        """Should filter tasks by status."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            tasks = data.get_circle_tasks(2, status="completed")
            assert len(tasks) == 2
            assert all(t["status"] == "completed" for t in tasks)

    def test_get_circle_tasks_empty(self):
        """Should return empty list for circle with no tasks."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            tasks = data.get_circle_tasks(999)
            assert tasks == []


class TestDemoCircleData:
    """Test demo circle data structure."""

    def test_demo_circles_structure(self):
        """Demo circles should have required fields."""
        for circle in DEMO_CIRCLES:
            assert "id" in circle
            assert "name" in circle
            assert "display_name" in circle
            assert "description" in circle
            assert "status" in circle
            assert "auto_route" in circle
            assert "require_review" in circle
            assert "member_count" in circle
            assert "task_count" in circle
            assert "is_active" in circle

    def test_demo_circle_members_structure(self):
        """Demo circle members should have required fields."""
        for member in DEMO_CIRCLE_MEMBERS:
            assert "id" in member
            assert "circle_id" in member
            assert "agent_id" in member
            assert "agent_name" in member
            assert "role" in member
            assert "is_active" in member

    def test_demo_circle_tasks_structure(self):
        """Demo circle tasks should have required fields."""
        for task in DEMO_CIRCLE_TASKS:
            assert "id" in task
            assert "circle_id" in task
            assert "title" in task
            assert "status" in task
            assert "priority" in task

    def test_demo_circle_member_counts_match(self):
        """Member counts in circles should match actual members."""
        for circle in DEMO_CIRCLES:
            circle_id = circle["id"]
            expected_count = circle["member_count"]
            actual_members = [m for m in DEMO_CIRCLE_MEMBERS if m["circle_id"] == circle_id]
            assert len(actual_members) == expected_count, \
                f"Circle {circle_id} reports {expected_count} members but has {len(actual_members)}"

    def test_demo_circle_task_counts_match(self):
        """Task counts in circles should match actual tasks."""
        for circle in DEMO_CIRCLES:
            circle_id = circle["id"]
            expected_count = circle["task_count"]
            actual_tasks = [t for t in DEMO_CIRCLE_TASKS if t["circle_id"] == circle_id]
            assert len(actual_tasks) == expected_count, \
                f"Circle {circle_id} reports {expected_count} tasks but has {len(actual_tasks)}"
