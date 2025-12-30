"""
Skill Registry for GatheRing.
Provides lazy-loading and dynamic registration of skills.
"""

from typing import Dict, Type, Optional, List, Any
import importlib
import logging

from gathering.skills.base import BaseSkill, SkillPermission

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registry for managing and accessing skills.

    Features:
    - Lazy loading: Skills only instantiated when first accessed
    - Dynamic registration: Add custom skills at runtime
    - Permission checking: Validate agent permissions before access
    """

    # Registered skill classes (not instances)
    _skill_classes: Dict[str, Type[BaseSkill]] = {}

    # Cached skill instances
    _instances: Dict[str, BaseSkill] = {}

    # Built-in skill mappings (module path -> class name)
    _builtin_skills: Dict[str, str] = {
        # Core skills
        "git": "gathering.skills.git:GitSkill",
        "test": "gathering.skills.test:TestSkill",
        "filesystem": "gathering.skills.filesystem:FileSystemSkill",
        # Web skills
        "web": "gathering.skills.web:WebSearchSkill",
        "scraper": "gathering.skills.web:WebScraperSkill",
        "http": "gathering.skills.http:HTTPSkill",
        # Code skills
        "code": "gathering.skills.code:CodeExecutionSkill",
        "analysis": "gathering.skills.analysis:CodeAnalysisSkill",
        # System skills
        "shell": "gathering.skills.shell:ShellSkill",
        "database": "gathering.skills.database:DatabaseSkill",
        "deploy": "gathering.skills.deploy:DeploySkill",
        # Documentation
        "docs": "gathering.skills.docs:DocsSkill",
        # Social skills
        "social": "gathering.skills.social:SocialMediaSkill",
        # AI & ML skills
        "ai": "gathering.skills.ai:AISkill",
        # Communication skills
        "email": "gathering.skills.email:EmailSkill",
        "notifications": "gathering.skills.notifications:NotificationsSkill",
        # Cloud & Infrastructure
        "cloud": "gathering.skills.cloud:CloudSkill",
        "monitoring": "gathering.skills.monitoring:MonitoringSkill",
        # Productivity skills
        "calendar": "gathering.skills.calendar:CalendarSkill",
        # Media processing skills
        "image": "gathering.skills.image:ImageSkill",
        "pdf": "gathering.skills.pdf:PDFSkill",
    }

    @classmethod
    def register(
        cls,
        name: str,
        skill_class: Type[BaseSkill],
        replace: bool = False,
    ) -> None:
        """
        Register a skill class.

        Args:
            name: Skill name for lookup
            skill_class: The skill class (not instance)
            replace: If True, replace existing registration
        """
        if name in cls._skill_classes and not replace:
            raise ValueError(f"Skill '{name}' already registered. Use replace=True to override.")

        cls._skill_classes[name] = skill_class

        # Clear cached instance if replacing
        if name in cls._instances:
            del cls._instances[name]

        logger.debug(f"Registered skill: {name} -> {skill_class.__name__}")

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a skill.

        Args:
            name: Skill name to remove
        """
        cls._skill_classes.pop(name, None)
        cls._instances.pop(name, None)

    @classmethod
    def get(
        cls,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        permissions: Optional[List[SkillPermission]] = None,
    ) -> BaseSkill:
        """
        Get a skill instance (lazy-loaded).

        Args:
            name: Skill name
            config: Optional configuration to pass to skill
            permissions: Optional permissions to validate

        Returns:
            Initialized skill instance

        Raises:
            ValueError: If skill not found
            PermissionError: If permissions insufficient
        """
        # Try to load from registered classes first
        if name not in cls._skill_classes:
            # Try to lazy-load builtin skill
            if name in cls._builtin_skills:
                cls._load_builtin_skill(name)
            else:
                raise ValueError(
                    f"Skill '{name}' not found. Available: {list(cls._skill_classes.keys())}"
                )

        skill_class = cls._skill_classes[name]

        # Check permissions if provided
        if permissions is not None:
            # Create temporary instance to check permissions
            temp_skill = skill_class(config)
            if not temp_skill.validate_permissions(permissions):
                missing = set(temp_skill.required_permissions) - set(permissions)
                raise PermissionError(
                    f"Insufficient permissions for skill '{name}'. "
                    f"Missing: {[p.value for p in missing]}"
                )

        # Return cached instance or create new one
        cache_key = f"{name}:{hash(str(config))}"
        if cache_key not in cls._instances:
            instance = skill_class(config)
            instance.ensure_initialized()
            cls._instances[cache_key] = instance

        return cls._instances[cache_key]

    @classmethod
    def _load_builtin_skill(cls, name: str) -> None:
        """
        Lazy-load a builtin skill from its module.

        Args:
            name: Skill name
        """
        if name not in cls._builtin_skills:
            raise ValueError(f"Unknown builtin skill: {name}")

        module_path = cls._builtin_skills[name]
        module_name, class_name = module_path.rsplit(":", 1)

        try:
            module = importlib.import_module(module_name)
            skill_class = getattr(module, class_name)
            cls.register(name, skill_class)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not load builtin skill '{name}': {e}")
            raise ValueError(f"Failed to load skill '{name}': {e}")

    @classmethod
    def list_skills(cls) -> List[str]:
        """
        List all available skill names.

        Returns:
            List of skill names (registered + builtins)
        """
        all_skills = set(cls._skill_classes.keys())
        all_skills.update(cls._builtin_skills.keys())
        return sorted(all_skills)

    @classmethod
    def list_registered(cls) -> List[str]:
        """List only registered (loaded) skill names."""
        return sorted(cls._skill_classes.keys())

    @classmethod
    def get_skill_info(cls, name: str) -> Dict[str, Any]:
        """
        Get information about a skill.

        Args:
            name: Skill name

        Returns:
            Dict with skill metadata
        """
        skill = cls.get(name)
        return {
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "required_permissions": [p.value for p in skill.required_permissions],
            "tools": skill.get_tool_names(),
            "tools_count": len(skill.get_tools_definition()),
        }

    @classmethod
    def get_all_tools(
        cls,
        skill_names: Optional[List[str]] = None,
        permissions: Optional[List[SkillPermission]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get tool definitions from multiple skills.

        Args:
            skill_names: List of skill names (None = all available)
            permissions: Filter skills by permissions

        Returns:
            Combined list of tool definitions
        """
        if skill_names is None:
            skill_names = cls.list_skills()

        tools = []
        for name in skill_names:
            try:
                skill = cls.get(name, permissions=permissions)
                for tool in skill.get_tools_definition():
                    # Add skill name to tool for routing
                    tool_with_skill = {**tool, "_skill": name}
                    tools.append(tool_with_skill)
            except (ValueError, PermissionError) as e:
                logger.debug(f"Skipping skill '{name}': {e}")
                continue

        return tools

    @classmethod
    def execute_tool(
        cls,
        tool_name: str,
        tool_input: Dict[str, Any],
        skill_name: Optional[str] = None,
        permissions: Optional[List[SkillPermission]] = None,
    ):
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            skill_name: Optional skill name (auto-detected if not provided)
            permissions: Optional permissions to validate

        Returns:
            SkillResponse from tool execution
        """
        # Find skill that provides this tool
        if skill_name is None:
            for name in cls.list_skills():
                try:
                    skill = cls.get(name)
                    if skill.has_tool(tool_name):
                        skill_name = name
                        break
                except ValueError:
                    continue

            if skill_name is None:
                from gathering.skills.base import SkillResponse
                return SkillResponse(
                    success=False,
                    message=f"No skill found providing tool '{tool_name}'",
                    error="tool_not_found",
                )

        skill = cls.get(skill_name, permissions=permissions)
        return skill.execute(tool_name, tool_input)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached skill instances."""
        cls._instances.clear()

    @classmethod
    def reset(cls) -> None:
        """Reset registry to initial state."""
        cls._skill_classes.clear()
        cls._instances.clear()
