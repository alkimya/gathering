"""
GatheRing Skills - Skills for managing GatheRing entities.

These skills allow agents to:
- Create and manage Goals
- Create and run Pipelines
- Start and monitor Background Tasks
- Schedule actions for later execution
- Create and participate in Circles
- Manage Projects and their context
"""

from gathering.skills.gathering.goals import GoalsSkill
from gathering.skills.gathering.pipelines import PipelinesSkill
from gathering.skills.gathering.tasks import BackgroundTasksSkill
from gathering.skills.gathering.schedules import SchedulesSkill
from gathering.skills.gathering.circles import CirclesSkill
from gathering.skills.gathering.projects import ProjectsSkill

__all__ = [
    "GoalsSkill",
    "PipelinesSkill",
    "BackgroundTasksSkill",
    "SchedulesSkill",
    "CirclesSkill",
    "ProjectsSkill",
]
