"""
Competency implementations for the GatheRing framework.

Competencies represent skills and expertise areas that agents can have.
They influence how agents handle tasks and enhance their prompts.

Usage:
    from gathering.core.competencies import BasicCompetency, CompetencyRegistry

    # Create a competency
    coding = BasicCompetency(
        name="python_programming",
        level=0.9,
        keywords=["python", "code", "programming", "debug"],
        description="Expert-level Python programming skills"
    )

    # Check if competency can handle a task
    confidence = coding.can_handle_task("Write a Python function to sort a list")
"""

from typing import List, Dict, Any, Optional
import re

from gathering.core.interfaces import ICompetency
from gathering.core.exceptions import CompetencyError


class BasicCompetency(ICompetency):
    """
    Basic competency implementation with keyword matching.

    Attributes:
        name: Competency identifier
        level: Skill level from 0.0 (novice) to 1.0 (expert)
        keywords: Keywords associated with this competency
        description: Human-readable description
    """

    def __init__(
        self,
        name: str,
        level: float = 0.5,
        keywords: Optional[List[str]] = None,
        description: Optional[str] = None,
    ):
        super().__init__(name, level)

        if not 0.0 <= level <= 1.0:
            raise CompetencyError(
                f"Level must be between 0.0 and 1.0, got {level}",
                competency_name=name,
            )

        self.keywords = [kw.lower() for kw in (keywords or [])]
        self.description = description or f"Competency in {name}"

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BasicCompetency":
        """Create a competency from configuration."""
        return cls(
            name=config["name"],
            level=config.get("level", 0.5),
            keywords=config.get("keywords", []),
            description=config.get("description"),
        )

    def get_prompt_enhancement(self) -> str:
        """
        Get prompt enhancement based on competency level.

        Returns:
            String to enhance the agent's system prompt
        """
        level_descriptions = {
            (0.0, 0.2): "basic understanding of",
            (0.2, 0.4): "working knowledge of",
            (0.4, 0.6): "solid experience with",
            (0.6, 0.8): "advanced expertise in",
            (0.8, 1.0): "expert-level mastery of",
        }

        for (low, high), desc in level_descriptions.items():
            if low <= self.level < high:
                return f"You have {desc} {self.name.replace('_', ' ')}. {self.description}"

        return f"You have expert-level mastery of {self.name.replace('_', ' ')}. {self.description}"

    def can_handle_task(self, task_description: str) -> float:
        """
        Calculate confidence score for handling a task.

        Uses keyword matching and competency level to determine
        how well suited this competency is for a given task.

        Args:
            task_description: Description of the task

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not task_description:
            return 0.0

        task_lower = task_description.lower()

        # Count keyword matches
        matches = sum(1 for kw in self.keywords if kw in task_lower)

        if not self.keywords:
            # No keywords defined, use name matching
            if self.name.lower().replace("_", " ") in task_lower:
                return self.level * 0.8
            return 0.0

        # Calculate match ratio
        match_ratio = matches / len(self.keywords) if self.keywords else 0

        # Combine match ratio with competency level
        # Higher level = more confident even with partial matches
        confidence = match_ratio * (0.5 + 0.5 * self.level)

        return min(1.0, confidence)

    def __repr__(self) -> str:
        return f"BasicCompetency(name={self.name!r}, level={self.level})"


# Predefined competencies for common use cases
PREDEFINED_COMPETENCIES: Dict[str, Dict[str, Any]] = {
    "python_programming": {
        "level": 0.8,
        "keywords": ["python", "code", "programming", "script", "debug", "function", "class"],
        "description": "Writing, debugging, and reviewing Python code",
    },
    "javascript_programming": {
        "level": 0.8,
        "keywords": ["javascript", "js", "node", "react", "typescript", "frontend"],
        "description": "JavaScript and frontend development",
    },
    "data_analysis": {
        "level": 0.7,
        "keywords": ["data", "analysis", "statistics", "pandas", "numpy", "visualization", "chart"],
        "description": "Analyzing and visualizing data",
    },
    "machine_learning": {
        "level": 0.7,
        "keywords": ["ml", "machine learning", "model", "training", "neural", "ai", "deep learning"],
        "description": "Building and training ML models",
    },
    "technical_writing": {
        "level": 0.8,
        "keywords": ["documentation", "readme", "docs", "explain", "tutorial", "guide"],
        "description": "Writing clear technical documentation",
    },
    "research": {
        "level": 0.7,
        "keywords": ["research", "study", "analyze", "investigate", "explore", "find"],
        "description": "Conducting research and analysis",
    },
    "teaching": {
        "level": 0.8,
        "keywords": ["teach", "explain", "learn", "understand", "tutorial", "lesson"],
        "description": "Teaching and explaining concepts clearly",
    },
    "mathematics": {
        "level": 0.7,
        "keywords": ["math", "calculate", "equation", "formula", "algebra", "calculus"],
        "description": "Mathematical reasoning and calculations",
    },
    "problem_solving": {
        "level": 0.8,
        "keywords": ["solve", "fix", "issue", "problem", "debug", "troubleshoot"],
        "description": "Solving complex problems systematically",
    },
    "communication": {
        "level": 0.9,
        "keywords": ["communicate", "explain", "clarify", "discuss", "talk", "message"],
        "description": "Clear and effective communication",
    },
}


class CompetencyRegistry:
    """
    Registry for managing and creating competencies.

    Provides predefined competencies and allows custom registration.
    """

    _competencies: Dict[str, Dict[str, Any]] = PREDEFINED_COMPETENCIES.copy()

    @classmethod
    def register(cls, name: str, config: Dict[str, Any]) -> None:
        """Register a new competency template."""
        cls._competencies[name] = config

    @classmethod
    def create(cls, name: str, level: Optional[float] = None) -> BasicCompetency:
        """
        Create a competency instance from the registry.

        Args:
            name: Competency name
            level: Optional override for the default level

        Returns:
            BasicCompetency instance

        Raises:
            CompetencyError: If competency is not registered
        """
        if name not in cls._competencies:
            # Create a basic competency with the given name
            return BasicCompetency(name=name, level=level or 0.5)

        config = cls._competencies[name].copy()
        config["name"] = name

        if level is not None:
            config["level"] = level

        return BasicCompetency.from_config(config)

    @classmethod
    def list_competencies(cls) -> List[str]:
        """List all registered competency names."""
        return list(cls._competencies.keys())

    @classmethod
    def get_config(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for a competency."""
        return cls._competencies.get(name)


def find_best_competencies(
    competencies: List[ICompetency],
    task_description: str,
    min_confidence: float = 0.1,
) -> List[tuple[ICompetency, float]]:
    """
    Find the best competencies for a given task.

    Args:
        competencies: List of competencies to evaluate
        task_description: Description of the task
        min_confidence: Minimum confidence threshold

    Returns:
        List of (competency, confidence) tuples, sorted by confidence descending
    """
    results = []

    for comp in competencies:
        confidence = comp.can_handle_task(task_description)
        if confidence >= min_confidence:
            results.append((comp, confidence))

    return sorted(results, key=lambda x: x[1], reverse=True)
