"""
Activity Tracker for workspace agent activities.

Tracks file edits, commits, test runs, and other agent actions
in a project workspace.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActivityType(str, Enum):
    """Types of activities."""

    FILE_CREATED = "file_created"
    FILE_EDITED = "file_edited"
    FILE_DELETED = "file_deleted"
    COMMIT = "commit"
    TEST_RUN = "test_run"
    BUILD = "build"
    DISCUSSION = "discussion"
    COMMAND_EXECUTED = "command_executed"


class ActivityTracker:
    """
    Tracks agent activities in a workspace.

    Stores activities in memory (can be extended to use database).
    """

    def __init__(self):
        self._activities: Dict[int, List[Dict[str, Any]]] = {}  # project_id -> activities

    def track_activity(
        self,
        project_id: int,
        agent_id: Optional[int],
        activity_type: ActivityType,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Track an activity.

        Args:
            project_id: Project ID.
            agent_id: Agent ID (None for user activities).
            activity_type: Type of activity.
            details: Activity details.

        Returns:
            Created activity.

        Example:
            >>> activity = tracker.track_activity(
            ...     project_id=1,
            ...     agent_id=5,
            ...     activity_type=ActivityType.FILE_EDITED,
            ...     details={"file": "src/main.py", "lines_added": 10}
            ... )
        """
        activity = {
            "id": self._generate_id(),
            "project_id": project_id,
            "agent_id": agent_id,
            "type": activity_type.value,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if project_id not in self._activities:
            self._activities[project_id] = []

        self._activities[project_id].append(activity)

        logger.info(
            f"Activity tracked: {activity_type.value} "
            f"by agent {agent_id} on project {project_id}"
        )

        return activity

    def get_activities(
        self,
        project_id: int,
        limit: int = 100,
        agent_id: Optional[int] = None,
        activity_type: Optional[ActivityType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get activities for a project.

        Args:
            project_id: Project ID.
            limit: Maximum number of activities.
            agent_id: Filter by agent (None = all agents).
            activity_type: Filter by type (None = all types).

        Returns:
            List of activities (most recent first).

        Example:
            >>> activities = tracker.get_activities(
            ...     project_id=1,
            ...     agent_id=5,
            ...     limit=20
            ... )
        """
        if project_id not in self._activities:
            return []

        activities = self._activities[project_id]

        # Filter
        if agent_id is not None:
            activities = [a for a in activities if a["agent_id"] == agent_id]

        if activity_type is not None:
            activities = [a for a in activities if a["type"] == activity_type.value]

        # Sort by timestamp (most recent first)
        activities = sorted(
            activities,
            key=lambda a: a["timestamp"],
            reverse=True,
        )

        return activities[:limit]

    def get_recent_file_edits(
        self,
        project_id: int,
        file_path: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get recent file edits.

        Args:
            project_id: Project ID.
            file_path: Filter by file (None = all files).
            limit: Maximum number of edits.

        Returns:
            List of file edit activities.
        """
        activities = self.get_activities(
            project_id,
            limit=limit * 3,  # Get more to filter
            activity_type=ActivityType.FILE_EDITED,
        )

        if file_path:
            activities = [
                a for a in activities
                if a["details"].get("file") == file_path
            ]

        return activities[:limit]

    def get_agent_summary(
        self,
        project_id: int,
        agent_id: int,
    ) -> Dict[str, Any]:
        """
        Get activity summary for an agent.

        Args:
            project_id: Project ID.
            agent_id: Agent ID.

        Returns:
            Summary with counts by activity type.
        """
        activities = self.get_activities(
            project_id,
            agent_id=agent_id,
            limit=1000,
        )

        # Count by type
        type_counts = {}
        for activity in activities:
            activity_type = activity["type"]
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1

        # Get most recent activity
        most_recent = activities[0] if activities else None

        return {
            "agent_id": agent_id,
            "total_activities": len(activities),
            "by_type": type_counts,
            "most_recent": most_recent,
        }

    def _generate_id(self) -> int:
        """Generate unique activity ID."""
        import time
        return int(time.time() * 1000000)

    def clear_project_activities(self, project_id: int) -> None:
        """Clear all activities for a project."""
        if project_id in self._activities:
            del self._activities[project_id]

    def get_stats(self, project_id: int) -> Dict[str, Any]:
        """Get activity statistics for a project."""
        if project_id not in self._activities:
            return {
                "total": 0,
                "by_type": {},
                "agents": [],
            }

        activities = self._activities[project_id]

        # Count by type
        type_counts = {}
        for activity in activities:
            activity_type = activity["type"]
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1

        # Get unique agents
        agents = set(a["agent_id"] for a in activities if a["agent_id"] is not None)

        return {
            "total": len(activities),
            "by_type": type_counts,
            "agents": list(agents),
        }


# Global activity tracker instance
activity_tracker = ActivityTracker()
