"""
Dynamic Competency Registry for GatheRing.

Allows registration and discovery of competencies (skills/capabilities) at runtime,
enabling dynamic agent skill management and plugin system extensibility.

Features:
- Type-safe competency definitions
- Category-based organization
- Level-based progression (novice → expert)
- Dynamic registration/unregistration
- Competency validation and requirements
- Dependency management between competencies

Usage:
    from gathering.core.competency_registry import (
        competency_registry,
        CompetencyDefinition,
        CompetencyCategory,
        CompetencyLevel,
    )

    # Register a competency
    competency_registry.register(CompetencyDefinition(
        id="python_advanced",
        name="Advanced Python Programming",
        description="Expert-level Python development",
        category=CompetencyCategory.PROGRAMMING,
        level=CompetencyLevel.EXPERT,
        prerequisites=["python_intermediate"],
        capabilities=["async_programming", "metaprogramming"],
    ))

    # Get competency
    comp = competency_registry.get("python_advanced")

    # List by category
    programming_comps = competency_registry.list_by_category(
        CompetencyCategory.PROGRAMMING
    )

    # Check if agent has competency
    has_skill = competency_registry.validate_agent_competencies(
        agent_competencies=["python_intermediate"],
        required=["python_advanced"],
    )
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum


class CompetencyLevel(str, Enum):
    """Competency proficiency levels."""

    NOVICE = "novice"  # Basic understanding
    INTERMEDIATE = "intermediate"  # Practical application
    ADVANCED = "advanced"  # Expert usage
    EXPERT = "expert"  # Mastery and innovation


class CompetencyCategory(str, Enum):
    """Competency categories for organization and discovery."""

    # Programming & Development
    PROGRAMMING = "programming"
    WEB_DEVELOPMENT = "web_development"
    MOBILE_DEVELOPMENT = "mobile_development"
    DATABASE = "database"
    DEVOPS = "devops"

    # AI & Machine Learning
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"

    # Creative & Design
    GRAPHIC_DESIGN = "graphic_design"
    UI_UX_DESIGN = "ui_ux_design"
    VIDEO_EDITING = "video_editing"
    AUDIO_PRODUCTION = "audio_production"
    THREE_D_MODELING = "three_d_modeling"

    # Business & Finance
    FINANCIAL_ANALYSIS = "financial_analysis"
    ACCOUNTING = "accounting"
    BUSINESS_STRATEGY = "business_strategy"
    MARKETING = "marketing"
    SALES = "sales"

    # Engineering
    MECHANICAL_ENGINEERING = "mechanical_engineering"
    ELECTRICAL_ENGINEERING = "electrical_engineering"
    CAD = "cad"
    SIMULATION = "simulation"
    IOT = "iot"

    # Science & Research
    DATA_SCIENCE = "data_science"
    STATISTICS = "statistics"
    SCIENTIFIC_COMPUTING = "scientific_computing"
    RESEARCH_METHODS = "research_methods"

    # Communication & Language
    WRITING = "writing"
    TRANSLATION = "translation"
    PUBLIC_SPEAKING = "public_speaking"

    # Domain Knowledge
    LEGAL = "legal"
    MEDICAL = "medical"
    EDUCATION = "education"

    # Soft Skills
    PROJECT_MANAGEMENT = "project_management"
    LEADERSHIP = "leadership"
    COLLABORATION = "collaboration"

    # Other
    CUSTOM = "custom"
    UTILITY = "utility"


@dataclass
class CompetencyDefinition:
    """
    Competency definition with metadata.

    A competency represents a skill or capability that agents can possess.
    """

    id: str
    """Unique competency identifier (e.g., 'python_advanced', 'design_ui_expert')"""

    name: str
    """Human-readable name (e.g., 'Advanced Python Programming')"""

    description: str
    """Detailed description of what this competency enables"""

    category: CompetencyCategory
    """Competency category for organization"""

    level: CompetencyLevel = CompetencyLevel.INTERMEDIATE
    """Proficiency level (default: intermediate)"""

    prerequisites: List[str] = field(default_factory=list)
    """List of prerequisite competency IDs"""

    capabilities: List[str] = field(default_factory=list)
    """Specific capabilities this competency provides"""

    tools_enabled: List[str] = field(default_factory=list)
    """Tool names that this competency enables"""

    plugin_id: Optional[str] = None
    """ID of plugin that provided this competency (None for core)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata (e.g., certifications, learning resources)"""

    def __post_init__(self):
        """Validate competency definition."""
        if not self.id:
            raise ValueError("Competency ID cannot be empty")
        if not self.name:
            raise ValueError("Competency name cannot be empty")
        if not self.description:
            raise ValueError("Competency description cannot be empty")


class CompetencyRegistry:
    """
    Dynamic competency registry.

    Manages registration, discovery, and validation of competencies.
    Thread-safe for concurrent access.
    """

    def __init__(self):
        self._competencies: Dict[str, CompetencyDefinition] = {}
        self._competencies_by_category: Dict[CompetencyCategory, List[str]] = {}
        self._competencies_by_level: Dict[CompetencyLevel, List[str]] = {}
        self._prerequisite_graph: Dict[str, Set[str]] = {}  # comp_id -> prerequisites

    def register(self, competency: CompetencyDefinition) -> None:
        """
        Register a competency.

        Args:
            competency: Competency definition to register.

        Raises:
            ValueError: If competency ID already exists or prerequisites are invalid.

        Example:
            >>> comp = CompetencyDefinition(
            ...     id="python",
            ...     name="Python Programming",
            ...     description="Python development skills",
            ...     category=CompetencyCategory.PROGRAMMING,
            ...     level=CompetencyLevel.INTERMEDIATE,
            ... )
            >>> competency_registry.register(comp)
        """
        # Validate
        if competency.id in self._competencies:
            raise ValueError(
                f"Competency '{competency.id}' already registered. "
                f"Use unregister() first to replace it."
            )

        # Validate prerequisites exist
        for prereq in competency.prerequisites:
            if prereq not in self._competencies and prereq != competency.id:
                raise ValueError(
                    f"Prerequisite '{prereq}' for competency '{competency.id}' "
                    f"is not registered. Register prerequisites first."
                )

        # Store competency
        self._competencies[competency.id] = competency

        # Index by category
        if competency.category not in self._competencies_by_category:
            self._competencies_by_category[competency.category] = []
        self._competencies_by_category[competency.category].append(competency.id)

        # Index by level
        if competency.level not in self._competencies_by_level:
            self._competencies_by_level[competency.level] = []
        self._competencies_by_level[competency.level].append(competency.id)

        # Build prerequisite graph
        if competency.prerequisites:
            self._prerequisite_graph[competency.id] = set(competency.prerequisites)

    def unregister(self, comp_id: str) -> bool:
        """
        Unregister a competency.

        Args:
            comp_id: Competency ID to unregister.

        Returns:
            True if competency was removed, False if it didn't exist.

        Raises:
            ValueError: If other competencies depend on this one.

        Example:
            >>> competency_registry.unregister("python")
            True
        """
        if comp_id not in self._competencies:
            return False

        # Check if other competencies depend on this one
        dependents = self.get_dependents(comp_id)
        if dependents:
            raise ValueError(
                f"Cannot unregister '{comp_id}': "
                f"competencies {dependents} depend on it"
            )

        competency = self._competencies[comp_id]

        # Remove from category index
        if competency.category in self._competencies_by_category:
            try:
                self._competencies_by_category[competency.category].remove(comp_id)
                if not self._competencies_by_category[competency.category]:
                    del self._competencies_by_category[competency.category]
            except ValueError:
                pass

        # Remove from level index
        if competency.level in self._competencies_by_level:
            try:
                self._competencies_by_level[competency.level].remove(comp_id)
                if not self._competencies_by_level[competency.level]:
                    del self._competencies_by_level[competency.level]
            except ValueError:
                pass

        # Remove from prerequisite graph
        if comp_id in self._prerequisite_graph:
            del self._prerequisite_graph[comp_id]

        # Remove competency
        del self._competencies[comp_id]
        return True

    def get(self, comp_id: str) -> Optional[CompetencyDefinition]:
        """
        Get competency by ID.

        Args:
            comp_id: Competency ID.

        Returns:
            Competency definition or None if not found.

        Example:
            >>> comp = competency_registry.get("python")
            >>> if comp:
            ...     print(comp.name)
        """
        return self._competencies.get(comp_id)

    def has(self, comp_id: str) -> bool:
        """
        Check if competency exists.

        Args:
            comp_id: Competency ID.

        Returns:
            True if competency is registered.

        Example:
            >>> if competency_registry.has("python"):
            ...     print("Competency exists")
        """
        return comp_id in self._competencies

    def list_all(self) -> List[CompetencyDefinition]:
        """
        List all registered competencies.

        Returns:
            List of all competency definitions.

        Example:
            >>> for comp in competency_registry.list_all():
            ...     print(f"{comp.id}: {comp.name}")
        """
        return list(self._competencies.values())

    def list_by_category(
        self, category: CompetencyCategory
    ) -> List[CompetencyDefinition]:
        """
        List competencies in a category.

        Args:
            category: Competency category.

        Returns:
            List of competencies in the category.

        Example:
            >>> programming = competency_registry.list_by_category(
            ...     CompetencyCategory.PROGRAMMING
            ... )
            >>> print(f"Found {len(programming)} programming competencies")
        """
        comp_ids = self._competencies_by_category.get(category, [])
        return [self._competencies[comp_id] for comp_id in comp_ids]

    def list_by_level(self, level: CompetencyLevel) -> List[CompetencyDefinition]:
        """
        List competencies at a proficiency level.

        Args:
            level: Competency level.

        Returns:
            List of competencies at that level.

        Example:
            >>> experts = competency_registry.list_by_level(CompetencyLevel.EXPERT)
            >>> for comp in experts:
            ...     print(comp.name)
        """
        comp_ids = self._competencies_by_level.get(level, [])
        return [self._competencies[comp_id] for comp_id in comp_ids]

    def list_by_plugin(self, plugin_id: str) -> List[CompetencyDefinition]:
        """
        List competencies provided by a plugin.

        Args:
            plugin_id: Plugin ID.

        Returns:
            List of competencies from that plugin.

        Example:
            >>> design_comps = competency_registry.list_by_plugin("design")
            >>> print(f"Design plugin provides {len(design_comps)} competencies")
        """
        return [
            comp for comp in self._competencies.values() if comp.plugin_id == plugin_id
        ]

    def get_prerequisites(self, comp_id: str) -> List[str]:
        """
        Get direct prerequisites for a competency.

        Args:
            comp_id: Competency ID.

        Returns:
            List of prerequisite competency IDs.

        Example:
            >>> prereqs = competency_registry.get_prerequisites("python_advanced")
            >>> print(f"Prerequisites: {prereqs}")
        """
        comp = self.get(comp_id)
        return comp.prerequisites if comp else []

    def get_all_prerequisites(self, comp_id: str) -> Set[str]:
        """
        Get all prerequisites (transitive closure) for a competency.

        Args:
            comp_id: Competency ID.

        Returns:
            Set of all prerequisite competency IDs (including indirect).

        Example:
            >>> all_prereqs = competency_registry.get_all_prerequisites("python_expert")
            >>> # Returns: {"python_advanced", "python_intermediate", "python_basic"}
        """
        if comp_id not in self._competencies:
            return set()

        visited = set()
        stack = [comp_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue

            visited.add(current)

            # Add direct prerequisites
            prereqs = self.get_prerequisites(current)
            for prereq in prereqs:
                if prereq not in visited:
                    stack.append(prereq)

        # Remove the competency itself
        visited.discard(comp_id)
        return visited

    def get_dependents(self, comp_id: str) -> List[str]:
        """
        Get competencies that depend on this one.

        Args:
            comp_id: Competency ID.

        Returns:
            List of competency IDs that have this as a prerequisite.

        Example:
            >>> deps = competency_registry.get_dependents("python_basic")
            >>> # Returns: ["python_intermediate", "python_advanced"]
        """
        dependents = []
        for other_id, prereqs in self._prerequisite_graph.items():
            if comp_id in prereqs:
                dependents.append(other_id)
        return dependents

    def validate_agent_competencies(
        self, agent_competencies: List[str], required: List[str]
    ) -> bool:
        """
        Validate if an agent has required competencies.

        Checks both direct competencies and prerequisites.

        Args:
            agent_competencies: List of competency IDs the agent has.
            required: List of required competency IDs.

        Returns:
            True if agent has all required competencies and their prerequisites.

        Example:
            >>> has_skills = competency_registry.validate_agent_competencies(
            ...     agent_competencies=["python_intermediate"],
            ...     required=["python_basic"],
            ... )
            >>> print(has_skills)  # True (intermediate includes basic)
        """
        agent_set = set(agent_competencies)

        for req in required:
            # Check if agent has the competency directly
            if req in agent_set:
                continue

            # Check if agent has a higher-level version
            # (e.g., has "python_expert" when "python_basic" is required)
            req_comp = self.get(req)
            if not req_comp:
                return False  # Required competency doesn't exist

            # Get all competencies that have this as a prerequisite
            # If agent has any of those, they implicitly have this
            dependents = self.get_dependents(req)
            if not any(dep in agent_set for dep in dependents):
                return False

        return True

    def get_learning_path(self, target_comp_id: str) -> List[str]:
        """
        Get learning path (ordered prerequisites) to acquire a competency.

        Args:
            target_comp_id: Target competency ID.

        Returns:
            Ordered list of competency IDs to learn (topological sort).

        Example:
            >>> path = competency_registry.get_learning_path("python_expert")
            >>> # Returns: ["python_basic", "python_intermediate", "python_advanced", "python_expert"]
        """
        if target_comp_id not in self._competencies:
            return []

        # Get all prerequisites
        all_prereqs = self.get_all_prerequisites(target_comp_id)
        all_prereqs.add(target_comp_id)

        # Topological sort
        visited = set()
        stack = []

        def dfs(comp_id: str):
            if comp_id in visited:
                return
            visited.add(comp_id)

            prereqs = self.get_prerequisites(comp_id)
            for prereq in prereqs:
                if prereq in all_prereqs:
                    dfs(prereq)

            stack.append(comp_id)

        dfs(target_comp_id)
        return stack

    def get_categories(self) -> List[CompetencyCategory]:
        """
        Get list of categories with registered competencies.

        Returns:
            List of categories that have at least one competency.

        Example:
            >>> categories = competency_registry.get_categories()
            >>> print(f"Competencies available in {len(categories)} categories")
        """
        return list(self._competencies_by_category.keys())

    def get_levels(self) -> List[CompetencyLevel]:
        """
        Get list of levels with registered competencies.

        Returns:
            List of levels that have at least one competency.

        Example:
            >>> levels = competency_registry.get_levels()
            >>> for level in levels:
            ...     comps = competency_registry.list_by_level(level)
            ...     print(f"{level.value}: {len(comps)} competencies")
        """
        return list(self._competencies_by_level.keys())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with statistics.

        Example:
            >>> stats = competency_registry.get_stats()
            >>> print(f"Total competencies: {stats['total_competencies']}")
        """
        return {
            "total_competencies": len(self._competencies),
            "categories": len(self._competencies_by_category),
            "levels": len(self._competencies_by_level),
            "competencies_by_category": {
                cat.value: len(comps)
                for cat, comps in self._competencies_by_category.items()
            },
            "competencies_by_level": {
                level.value: len(comps)
                for level, comps in self._competencies_by_level.items()
            },
            "plugins": len(
                set(
                    comp.plugin_id
                    for comp in self._competencies.values()
                    if comp.plugin_id
                )
            ),
        }

    def clear(self) -> None:
        """
        Clear all registered competencies.

        Use with caution! This removes all competencies from the registry.

        Example:
            >>> competency_registry.clear()
            >>> assert len(competency_registry.list_all()) == 0
        """
        self._competencies.clear()
        self._competencies_by_category.clear()
        self._competencies_by_level.clear()
        self._prerequisite_graph.clear()


# Global competency registry instance
competency_registry = CompetencyRegistry()


# Convenience functions for global registry
def register_competency(competency: CompetencyDefinition) -> None:
    """Register a competency in the global registry."""
    competency_registry.register(competency)


def get_competency(comp_id: str) -> Optional[CompetencyDefinition]:
    """Get competency from global registry."""
    return competency_registry.get(comp_id)


def validate_competencies(agent_competencies: List[str], required: List[str]) -> bool:
    """Validate agent competencies against requirements."""
    return competency_registry.validate_agent_competencies(agent_competencies, required)
