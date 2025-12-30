"""
Skills module for GatheRing framework.
Provides modular, lazy-loaded skills for agents.

Available Skills:
- git: Git operations (clone, commit, push, PR, rebase, stash)
- test: Test execution and coverage analysis
- web: Web search (Google, Wikipedia, news)
- scraper: Web scraping and data extraction
- shell: Shell command execution
- http: HTTP client operations
- code: Code execution (Python, JavaScript)
- social: Social media integrations

Usage:
    from gathering.skills import SkillRegistry

    # Get a skill
    git = SkillRegistry.get("git")
    result = git.execute("git_status", {"path": "/my/repo"})

    # Register custom skill
    SkillRegistry.register("custom", MyCustomSkill)
"""

from gathering.skills.base import (
    BaseSkill,
    SkillResponse,
    SkillPermission,
)
from gathering.skills.registry import SkillRegistry

# Skills are lazy-loaded by registry on-demand

__all__ = [
    # Base classes
    "BaseSkill",
    "SkillResponse",
    "SkillPermission",
    # Registry
    "SkillRegistry",
]
