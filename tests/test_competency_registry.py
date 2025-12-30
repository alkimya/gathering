"""
Tests for Competency Registry.

Tests dynamic competency registration, discovery, validation,
and prerequisite management.
"""

import pytest
from gathering.core.competency_registry import (
    CompetencyRegistry,
    CompetencyDefinition,
    CompetencyCategory,
    CompetencyLevel,
    competency_registry,
    register_competency,
    get_competency,
    validate_competencies,
)


class TestCompetencyDefinition:
    """Test CompetencyDefinition dataclass."""

    def test_create_competency_definition(self):
        """Test creating a valid competency definition."""
        comp = CompetencyDefinition(
            id="python",
            name="Python Programming",
            description="Python development skills",
            category=CompetencyCategory.PROGRAMMING,
            level=CompetencyLevel.INTERMEDIATE,
            prerequisites=["programming_basics"],
            capabilities=["scripting", "automation"],
            tools_enabled=["execute_python"],
        )

        assert comp.id == "python"
        assert comp.name == "Python Programming"
        assert comp.category == CompetencyCategory.PROGRAMMING
        assert comp.level == CompetencyLevel.INTERMEDIATE
        assert "programming_basics" in comp.prerequisites
        assert "scripting" in comp.capabilities

    def test_competency_definition_validation(self):
        """Test competency definition validation."""
        # Empty ID
        with pytest.raises(ValueError, match="ID cannot be empty"):
            CompetencyDefinition(
                id="",
                name="Test",
                description="Test comp",
                category=CompetencyCategory.PROGRAMMING,
            )

        # Empty name
        with pytest.raises(ValueError, match="name cannot be empty"):
            CompetencyDefinition(
                id="test",
                name="",
                description="Test comp",
                category=CompetencyCategory.PROGRAMMING,
            )

        # Empty description
        with pytest.raises(ValueError, match="description cannot be empty"):
            CompetencyDefinition(
                id="test",
                name="Test",
                description="",
                category=CompetencyCategory.PROGRAMMING,
            )

    def test_competency_definition_defaults(self):
        """Test default values."""
        comp = CompetencyDefinition(
            id="test",
            name="Test Comp",
            description="Test competency",
            category=CompetencyCategory.UTILITY,
        )

        assert comp.level == CompetencyLevel.INTERMEDIATE
        assert comp.prerequisites == []
        assert comp.capabilities == []
        assert comp.tools_enabled == []
        assert comp.plugin_id is None
        assert comp.metadata == {}


class TestCompetencyRegistry:
    """Test CompetencyRegistry class."""

    def setup_method(self):
        """Setup test registry."""
        self.registry = CompetencyRegistry()

        # Register test competencies
        self.registry.register(
            CompetencyDefinition(
                id="programming_basics",
                name="Programming Basics",
                description="Basic programming concepts",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.NOVICE,
            )
        )

        self.registry.register(
            CompetencyDefinition(
                id="python_intermediate",
                name="Python Intermediate",
                description="Intermediate Python skills",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.INTERMEDIATE,
                prerequisites=["programming_basics"],
                capabilities=["oop", "functional"],
            )
        )

        self.registry.register(
            CompetencyDefinition(
                id="python_expert",
                name="Python Expert",
                description="Expert Python skills",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.EXPERT,
                prerequisites=["python_intermediate"],
                capabilities=["metaprogramming", "async"],
            )
        )

        self.registry.register(
            CompetencyDefinition(
                id="design",
                name="UI/UX Design",
                description="User interface design",
                category=CompetencyCategory.UI_UX_DESIGN,
                level=CompetencyLevel.ADVANCED,
            )
        )

    def test_register_competency(self):
        """Test registering a competency."""
        comp = CompetencyDefinition(
            id="new_comp",
            name="New Competency",
            description="A new competency",
            category=CompetencyCategory.CUSTOM,
        )

        self.registry.register(comp)
        assert self.registry.has("new_comp")

    def test_register_duplicate_competency(self):
        """Test registering duplicate competency raises error."""
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(
                CompetencyDefinition(
                    id="design",
                    name="Duplicate",
                    description="Duplicate",
                    category=CompetencyCategory.CUSTOM,
                )
            )

    def test_register_with_missing_prerequisite(self):
        """Test registering with missing prerequisite raises error."""
        with pytest.raises(ValueError, match="not registered"):
            self.registry.register(
                CompetencyDefinition(
                    id="advanced_skill",
                    name="Advanced",
                    description="Advanced skill",
                    category=CompetencyCategory.CUSTOM,
                    prerequisites=["nonexistent"],
                )
            )

    def test_unregister_competency(self):
        """Test unregistering a competency."""
        result = self.registry.unregister("design")
        assert result is True
        assert not self.registry.has("design")

    def test_unregister_nonexistent_competency(self):
        """Test unregistering nonexistent competency."""
        result = self.registry.unregister("nonexistent")
        assert result is False

    def test_unregister_with_dependents(self):
        """Test unregistering competency with dependents raises error."""
        with pytest.raises(ValueError, match="depend on it"):
            self.registry.unregister("programming_basics")

    def test_get_competency(self):
        """Test getting a competency."""
        comp = self.registry.get("python_expert")
        assert comp is not None
        assert comp.id == "python_expert"
        assert comp.level == CompetencyLevel.EXPERT

    def test_get_nonexistent_competency(self):
        """Test getting nonexistent competency."""
        comp = self.registry.get("nonexistent")
        assert comp is None

    def test_list_all_competencies(self):
        """Test listing all competencies."""
        comps = self.registry.list_all()
        assert len(comps) == 4
        assert any(c.id == "python_expert" for c in comps)

    def test_list_by_category(self):
        """Test listing by category."""
        programming = self.registry.list_by_category(CompetencyCategory.PROGRAMMING)
        assert len(programming) == 3

        design = self.registry.list_by_category(CompetencyCategory.UI_UX_DESIGN)
        assert len(design) == 1

        empty = self.registry.list_by_category(CompetencyCategory.FINANCIAL_ANALYSIS)
        assert len(empty) == 0

    def test_list_by_level(self):
        """Test listing by level."""
        experts = self.registry.list_by_level(CompetencyLevel.EXPERT)
        assert len(experts) == 1
        assert experts[0].id == "python_expert"

        novices = self.registry.list_by_level(CompetencyLevel.NOVICE)
        assert len(novices) == 1
        assert novices[0].id == "programming_basics"

    def test_list_by_plugin(self):
        """Test listing by plugin."""
        # Register competency with plugin_id
        self.registry.register(
            CompetencyDefinition(
                id="plugin_comp",
                name="Plugin Comp",
                description="From plugin",
                category=CompetencyCategory.CUSTOM,
                plugin_id="test_plugin",
            )
        )

        plugin_comps = self.registry.list_by_plugin("test_plugin")
        assert len(plugin_comps) == 1
        assert plugin_comps[0].id == "plugin_comp"

        empty = self.registry.list_by_plugin("nonexistent")
        assert len(empty) == 0

    def test_get_prerequisites(self):
        """Test getting direct prerequisites."""
        prereqs = self.registry.get_prerequisites("python_expert")
        assert prereqs == ["python_intermediate"]

        prereqs = self.registry.get_prerequisites("programming_basics")
        assert prereqs == []

        prereqs = self.registry.get_prerequisites("nonexistent")
        assert prereqs == []

    def test_get_all_prerequisites(self):
        """Test getting all prerequisites (transitive)."""
        all_prereqs = self.registry.get_all_prerequisites("python_expert")
        assert "python_intermediate" in all_prereqs
        assert "programming_basics" in all_prereqs
        assert "python_expert" not in all_prereqs  # Should not include itself

        all_prereqs = self.registry.get_all_prerequisites("programming_basics")
        assert len(all_prereqs) == 0

    def test_get_dependents(self):
        """Test getting competencies that depend on this one."""
        deps = self.registry.get_dependents("programming_basics")
        assert "python_intermediate" in deps

        deps = self.registry.get_dependents("python_intermediate")
        assert "python_expert" in deps

        deps = self.registry.get_dependents("python_expert")
        assert len(deps) == 0

    def test_validate_agent_competencies_direct_match(self):
        """Test validating with direct match."""
        result = self.registry.validate_agent_competencies(
            agent_competencies=["python_expert"],
            required=["python_expert"],
        )
        assert result is True

    def test_validate_agent_competencies_higher_level(self):
        """Test validating with higher-level competency."""
        # Agent has expert, needs intermediate - should pass
        result = self.registry.validate_agent_competencies(
            agent_competencies=["python_expert"],
            required=["python_intermediate"],
        )
        assert result is True

        # Agent has intermediate, needs basics - should pass
        result = self.registry.validate_agent_competencies(
            agent_competencies=["python_intermediate"],
            required=["programming_basics"],
        )
        assert result is True

    def test_validate_agent_competencies_missing(self):
        """Test validating with missing competency."""
        result = self.registry.validate_agent_competencies(
            agent_competencies=["design"],
            required=["python_expert"],
        )
        assert result is False

    def test_validate_agent_competencies_nonexistent(self):
        """Test validating with nonexistent required competency."""
        result = self.registry.validate_agent_competencies(
            agent_competencies=["python_expert"],
            required=["nonexistent"],
        )
        assert result is False

    def test_get_learning_path_linear(self):
        """Test getting learning path."""
        path = self.registry.get_learning_path("python_expert")
        assert path == [
            "programming_basics",
            "python_intermediate",
            "python_expert",
        ]

    def test_get_learning_path_no_prerequisites(self):
        """Test learning path for competency without prerequisites."""
        path = self.registry.get_learning_path("design")
        assert path == ["design"]

    def test_get_learning_path_nonexistent(self):
        """Test learning path for nonexistent competency."""
        path = self.registry.get_learning_path("nonexistent")
        assert path == []

    def test_get_learning_path_complex_graph(self):
        """Test learning path with complex prerequisite graph."""
        # Create a diamond dependency graph
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        registry = CompetencyRegistry()

        registry.register(
            CompetencyDefinition(
                id="a",
                name="A",
                description="Base",
                category=CompetencyCategory.PROGRAMMING,
            )
        )

        registry.register(
            CompetencyDefinition(
                id="b",
                name="B",
                description="Branch 1",
                category=CompetencyCategory.PROGRAMMING,
                prerequisites=["a"],
            )
        )

        registry.register(
            CompetencyDefinition(
                id="c",
                name="C",
                description="Branch 2",
                category=CompetencyCategory.PROGRAMMING,
                prerequisites=["a"],
            )
        )

        registry.register(
            CompetencyDefinition(
                id="d",
                name="D",
                description="Merge",
                category=CompetencyCategory.PROGRAMMING,
                prerequisites=["b", "c"],
            )
        )

        path = registry.get_learning_path("d")
        # A must come before B and C, which must come before D
        assert path[0] == "a"
        assert path[-1] == "d"
        assert "b" in path
        assert "c" in path

    def test_get_categories(self):
        """Test getting categories."""
        categories = self.registry.get_categories()
        assert CompetencyCategory.PROGRAMMING in categories
        assert CompetencyCategory.UI_UX_DESIGN in categories
        assert len(categories) == 2

    def test_get_levels(self):
        """Test getting levels."""
        levels = self.registry.get_levels()
        assert CompetencyLevel.NOVICE in levels
        assert CompetencyLevel.INTERMEDIATE in levels
        assert CompetencyLevel.ADVANCED in levels
        assert CompetencyLevel.EXPERT in levels

    def test_get_stats(self):
        """Test getting statistics."""
        stats = self.registry.get_stats()
        assert stats["total_competencies"] == 4
        assert stats["categories"] == 2
        assert stats["levels"] == 4
        assert stats["competencies_by_category"]["programming"] == 3
        assert stats["competencies_by_level"]["expert"] == 1

    def test_clear_registry(self):
        """Test clearing the registry."""
        self.registry.clear()
        assert len(self.registry.list_all()) == 0
        assert len(self.registry.get_categories()) == 0
        assert len(self.registry.get_levels()) == 0


class TestGlobalCompetencyRegistry:
    """Test global competency registry."""

    def setup_method(self):
        """Clear global registry before each test."""
        competency_registry.clear()

    def teardown_method(self):
        """Clear global registry after each test."""
        competency_registry.clear()

    def test_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        from gathering.core.competency_registry import competency_registry as registry2

        assert competency_registry is registry2

    def test_register_to_global_registry(self):
        """Test registering to global registry."""
        comp = CompetencyDefinition(
            id="global_test",
            name="Global Test",
            description="Test competency",
            category=CompetencyCategory.UTILITY,
        )

        register_competency(comp)
        assert competency_registry.has("global_test")

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Register
        register_competency(
            CompetencyDefinition(
                id="python",
                name="Python",
                description="Python programming",
                category=CompetencyCategory.PROGRAMMING,
            )
        )

        # Get
        comp = get_competency("python")
        assert comp is not None
        assert comp.id == "python"

        # Validate
        result = validate_competencies(
            agent_competencies=["python"],
            required=["python"],
        )
        assert result is True


class TestCompetencyRegistryCleanup:
    """Test index cleanup on unregistration."""

    def setup_method(self):
        """Setup test registry."""
        self.registry = CompetencyRegistry()

    def test_unregister_cleans_category_index(self):
        """Test that unregistering removes from category index."""
        self.registry.register(
            CompetencyDefinition(
                id="test",
                name="Test",
                description="Test",
                category=CompetencyCategory.PROGRAMMING,
            )
        )

        assert CompetencyCategory.PROGRAMMING in self.registry.get_categories()

        self.registry.unregister("test")

        # Category should be removed if no competencies left
        assert CompetencyCategory.PROGRAMMING not in self.registry.get_categories()

    def test_unregister_cleans_level_index(self):
        """Test that unregistering removes from level index."""
        self.registry.register(
            CompetencyDefinition(
                id="test",
                name="Test",
                description="Test",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.EXPERT,
            )
        )

        assert CompetencyLevel.EXPERT in self.registry.get_levels()

        self.registry.unregister("test")

        # Level should be removed if no competencies left
        assert CompetencyLevel.EXPERT not in self.registry.get_levels()

    def test_unregister_cleans_prerequisite_graph(self):
        """Test that unregistering removes from prerequisite graph."""
        self.registry.register(
            CompetencyDefinition(
                id="base",
                name="Base",
                description="Base",
                category=CompetencyCategory.PROGRAMMING,
            )
        )

        self.registry.register(
            CompetencyDefinition(
                id="advanced",
                name="Advanced",
                description="Advanced",
                category=CompetencyCategory.PROGRAMMING,
                prerequisites=["base"],
            )
        )

        assert "advanced" in self.registry._prerequisite_graph

        self.registry.unregister("advanced")

        assert "advanced" not in self.registry._prerequisite_graph

    def test_partial_cleanup_with_shared_category(self):
        """Test that category is not removed if other competencies use it."""
        self.registry.register(
            CompetencyDefinition(
                id="test1",
                name="Test 1",
                description="Test 1",
                category=CompetencyCategory.PROGRAMMING,
            )
        )

        self.registry.register(
            CompetencyDefinition(
                id="test2",
                name="Test 2",
                description="Test 2",
                category=CompetencyCategory.PROGRAMMING,
            )
        )

        self.registry.unregister("test1")

        # Category should still exist
        assert CompetencyCategory.PROGRAMMING in self.registry.get_categories()

        # But only one competency
        assert len(self.registry.list_by_category(CompetencyCategory.PROGRAMMING)) == 1


class TestCompetencyLevels:
    """Test competency level progression."""

    def test_level_enum_values(self):
        """Test level enum has correct values."""
        assert CompetencyLevel.NOVICE.value == "novice"
        assert CompetencyLevel.INTERMEDIATE.value == "intermediate"
        assert CompetencyLevel.ADVANCED.value == "advanced"
        assert CompetencyLevel.EXPERT.value == "expert"

    def test_level_progression(self):
        """Test that levels represent progression."""
        registry = CompetencyRegistry()

        registry.register(
            CompetencyDefinition(
                id="novice",
                name="Novice",
                description="Novice level",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.NOVICE,
            )
        )

        registry.register(
            CompetencyDefinition(
                id="intermediate",
                name="Intermediate",
                description="Intermediate level",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.INTERMEDIATE,
                prerequisites=["novice"],
            )
        )

        registry.register(
            CompetencyDefinition(
                id="advanced",
                name="Advanced",
                description="Advanced level",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.ADVANCED,
                prerequisites=["intermediate"],
            )
        )

        registry.register(
            CompetencyDefinition(
                id="expert",
                name="Expert",
                description="Expert level",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.EXPERT,
                prerequisites=["advanced"],
            )
        )

        path = registry.get_learning_path("expert")
        assert path == ["novice", "intermediate", "advanced", "expert"]
