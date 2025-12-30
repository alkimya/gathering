"""
Tests for gathering/core/competencies.py - Competency implementations.
"""

import pytest

from gathering.core.competencies import (
    BasicCompetency,
    CompetencyRegistry,
    PREDEFINED_COMPETENCIES,
    find_best_competencies,
)
from gathering.core.exceptions import CompetencyError


class TestBasicCompetency:
    """Test BasicCompetency class."""

    def test_basic_creation(self):
        """Test creating a basic competency."""
        comp = BasicCompetency(name="python", level=0.8)
        assert comp.name == "python"
        assert comp.level == 0.8
        assert comp.keywords == []
        assert comp.description == "Competency in python"

    def test_creation_with_keywords(self):
        """Test creating competency with keywords."""
        comp = BasicCompetency(
            name="data_analysis",
            level=0.7,
            keywords=["Data", "Analysis", "STATISTICS"],
            description="Expert in data analysis",
        )
        assert comp.name == "data_analysis"
        assert comp.level == 0.7
        # Keywords are lowercased
        assert comp.keywords == ["data", "analysis", "statistics"]
        assert comp.description == "Expert in data analysis"

    def test_invalid_level_too_low(self):
        """Test that level below 0.0 raises error."""
        with pytest.raises(CompetencyError) as exc_info:
            BasicCompetency(name="test", level=-0.1)
        assert "Level must be between 0.0 and 1.0" in str(exc_info.value)
        assert exc_info.value.competency_name == "test"

    def test_invalid_level_too_high(self):
        """Test that level above 1.0 raises error."""
        with pytest.raises(CompetencyError) as exc_info:
            BasicCompetency(name="test", level=1.5)
        assert "Level must be between 0.0 and 1.0" in str(exc_info.value)

    def test_boundary_levels(self):
        """Test boundary level values."""
        comp_zero = BasicCompetency(name="novice", level=0.0)
        assert comp_zero.level == 0.0

        comp_one = BasicCompetency(name="expert", level=1.0)
        assert comp_one.level == 1.0

    def test_from_config(self):
        """Test creating competency from config dict."""
        config = {
            "name": "machine_learning",
            "level": 0.9,
            "keywords": ["ml", "model", "training"],
            "description": "ML expertise",
        }
        comp = BasicCompetency.from_config(config)
        assert comp.name == "machine_learning"
        assert comp.level == 0.9
        assert comp.keywords == ["ml", "model", "training"]

    def test_from_config_minimal(self):
        """Test creating competency from minimal config."""
        config = {"name": "minimal"}
        comp = BasicCompetency.from_config(config)
        assert comp.name == "minimal"
        assert comp.level == 0.5  # default
        assert comp.keywords == []

    def test_repr(self):
        """Test string representation."""
        comp = BasicCompetency(name="test", level=0.75)
        repr_str = repr(comp)
        assert "BasicCompetency" in repr_str
        assert "test" in repr_str
        assert "0.75" in repr_str


class TestGetPromptEnhancement:
    """Test get_prompt_enhancement method."""

    def test_novice_level(self):
        """Test prompt enhancement for novice level."""
        comp = BasicCompetency(name="python_coding", level=0.15)
        enhancement = comp.get_prompt_enhancement()
        assert "basic understanding of" in enhancement
        assert "python coding" in enhancement

    def test_working_knowledge_level(self):
        """Test prompt enhancement for working knowledge level."""
        comp = BasicCompetency(name="data_analysis", level=0.35)
        enhancement = comp.get_prompt_enhancement()
        assert "working knowledge of" in enhancement

    def test_solid_experience_level(self):
        """Test prompt enhancement for solid experience level."""
        comp = BasicCompetency(name="testing", level=0.55)
        enhancement = comp.get_prompt_enhancement()
        assert "solid experience with" in enhancement

    def test_advanced_expertise_level(self):
        """Test prompt enhancement for advanced expertise level."""
        comp = BasicCompetency(name="debugging", level=0.75)
        enhancement = comp.get_prompt_enhancement()
        assert "advanced expertise in" in enhancement

    def test_expert_level(self):
        """Test prompt enhancement for expert level."""
        comp = BasicCompetency(
            name="machine_learning",
            level=0.95,
            description="Building ML pipelines",
        )
        enhancement = comp.get_prompt_enhancement()
        assert "expert-level mastery of" in enhancement
        assert "Building ML pipelines" in enhancement

    def test_exact_boundary_1_0(self):
        """Test prompt enhancement at exactly 1.0."""
        comp = BasicCompetency(name="expertise", level=1.0)
        enhancement = comp.get_prompt_enhancement()
        assert "expert-level mastery" in enhancement


class TestCanHandleTask:
    """Test can_handle_task method."""

    def test_empty_task_description(self):
        """Test with empty task description."""
        comp = BasicCompetency(name="test", level=0.8, keywords=["python"])
        assert comp.can_handle_task("") == 0.0
        assert comp.can_handle_task(None) == 0.0

    def test_no_keywords_name_match(self):
        """Test matching by name when no keywords defined."""
        comp = BasicCompetency(name="python_programming", level=0.8)
        confidence = comp.can_handle_task("I need help with python programming")
        assert confidence > 0
        assert confidence == 0.8 * 0.8  # level * 0.8

    def test_no_keywords_no_match(self):
        """Test no match when no keywords and name doesn't match."""
        comp = BasicCompetency(name="python", level=0.8)
        confidence = comp.can_handle_task("I need help with JavaScript")
        assert confidence == 0.0

    def test_keyword_matching(self):
        """Test keyword-based matching."""
        comp = BasicCompetency(
            name="python",
            level=0.8,
            keywords=["python", "code", "programming"],
        )
        # All keywords match
        confidence = comp.can_handle_task("Write python code for programming")
        assert confidence > 0.5

    def test_partial_keyword_matching(self):
        """Test partial keyword matching."""
        comp = BasicCompetency(
            name="ml",
            level=0.7,
            keywords=["machine", "learning", "model", "training"],
        )
        # Only 2 of 4 keywords match
        confidence = comp.can_handle_task("Train a machine model")
        assert 0 < confidence < 1

    def test_no_keyword_match(self):
        """Test when no keywords match."""
        comp = BasicCompetency(
            name="python",
            level=0.9,
            keywords=["python", "django", "flask"],
        )
        confidence = comp.can_handle_task("Write JavaScript with React")
        assert confidence == 0.0

    def test_confidence_capped_at_1(self):
        """Test that confidence is capped at 1.0."""
        comp = BasicCompetency(
            name="test",
            level=1.0,
            keywords=["a"],  # Single keyword
        )
        # 100% match rate with level 1.0
        confidence = comp.can_handle_task("a a a a")
        assert confidence <= 1.0


class TestCompetencyRegistry:
    """Test CompetencyRegistry class."""

    def test_predefined_competencies_loaded(self):
        """Test that predefined competencies are available."""
        competencies = CompetencyRegistry.list_competencies()
        assert "python_programming" in competencies
        assert "data_analysis" in competencies
        assert "machine_learning" in competencies

    def test_create_predefined(self):
        """Test creating a predefined competency."""
        comp = CompetencyRegistry.create("python_programming")
        assert comp.name == "python_programming"
        assert comp.level == 0.8  # from PREDEFINED_COMPETENCIES

    def test_create_with_level_override(self):
        """Test creating with custom level."""
        comp = CompetencyRegistry.create("python_programming", level=0.5)
        assert comp.name == "python_programming"
        assert comp.level == 0.5  # overridden

    def test_create_unknown_competency(self):
        """Test creating an unknown competency creates basic one."""
        comp = CompetencyRegistry.create("unknown_skill")
        assert comp.name == "unknown_skill"
        assert comp.level == 0.5  # default

    def test_create_unknown_with_level(self):
        """Test creating unknown competency with level."""
        comp = CompetencyRegistry.create("custom_skill", level=0.9)
        assert comp.name == "custom_skill"
        assert comp.level == 0.9

    def test_register_new_competency(self):
        """Test registering a new competency."""
        CompetencyRegistry.register(
            "blockchain",
            {
                "level": 0.7,
                "keywords": ["blockchain", "crypto", "web3"],
                "description": "Blockchain development",
            },
        )
        comp = CompetencyRegistry.create("blockchain")
        assert comp.name == "blockchain"
        assert comp.level == 0.7
        assert "blockchain" in comp.keywords

    def test_get_config(self):
        """Test getting competency config."""
        config = CompetencyRegistry.get_config("python_programming")
        assert config is not None
        assert "keywords" in config
        assert "python" in config["keywords"]

    def test_get_config_not_found(self):
        """Test getting config for non-existent competency."""
        config = CompetencyRegistry.get_config("nonexistent")
        assert config is None


class TestFindBestCompetencies:
    """Test find_best_competencies function."""

    def test_find_matching_competencies(self):
        """Test finding competencies that match a task."""
        competencies = [
            BasicCompetency("python", 0.9, ["python", "code"]),
            BasicCompetency("javascript", 0.8, ["js", "javascript"]),
            BasicCompetency("writing", 0.7, ["docs", "readme"]),
        ]
        results = find_best_competencies(
            competencies,
            "Write python code",
            min_confidence=0.1,
        )
        assert len(results) > 0
        # Python should be the best match
        assert results[0][0].name == "python"
        assert results[0][1] > 0

    def test_filter_by_min_confidence(self):
        """Test that min_confidence filters results."""
        competencies = [
            BasicCompetency("python", 0.5, ["python"]),
            BasicCompetency("java", 0.3, ["java"]),
        ]
        # High threshold should filter out weak matches
        results = find_best_competencies(
            competencies,
            "Write python code",
            min_confidence=0.8,
        )
        # May be empty or have few results
        assert all(conf >= 0.8 for _, conf in results)

    def test_empty_competencies(self):
        """Test with empty competencies list."""
        results = find_best_competencies([], "Any task", min_confidence=0.1)
        assert results == []

    def test_no_matches(self):
        """Test when no competencies match."""
        competencies = [
            BasicCompetency("blockchain", 0.8, ["blockchain", "crypto"]),
        ]
        results = find_best_competencies(
            competencies,
            "Write python code",
            min_confidence=0.1,
        )
        assert results == []

    def test_sorted_by_confidence(self):
        """Test that results are sorted by confidence descending."""
        competencies = [
            BasicCompetency("low", 0.3, ["test"]),
            BasicCompetency("high", 0.9, ["test"]),
            BasicCompetency("medium", 0.6, ["test"]),
        ]
        results = find_best_competencies(
            competencies,
            "test task",
            min_confidence=0.0,
        )
        # Should be sorted by confidence
        confidences = [conf for _, conf in results]
        assert confidences == sorted(confidences, reverse=True)


class TestPredefinedCompetencies:
    """Test the predefined competencies dictionary."""

    def test_all_predefined_have_required_fields(self):
        """Test all predefined competencies have required fields."""
        for name, config in PREDEFINED_COMPETENCIES.items():
            assert "level" in config, f"{name} missing level"
            assert "keywords" in config, f"{name} missing keywords"
            assert "description" in config, f"{name} missing description"

    def test_all_predefined_levels_valid(self):
        """Test all predefined levels are valid."""
        for name, config in PREDEFINED_COMPETENCIES.items():
            level = config["level"]
            assert 0.0 <= level <= 1.0, f"{name} has invalid level {level}"

    def test_can_create_all_predefined(self):
        """Test that all predefined competencies can be created."""
        for name in PREDEFINED_COMPETENCIES:
            comp = CompetencyRegistry.create(name)
            assert comp.name == name
            assert comp.level > 0
