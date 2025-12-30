# Phase 6: Plugin System - Design Document

Design détaillé du système de plugins pour rendre GatheRing extensible à n'importe quel domaine.

## Objectifs

**Problème actuel:**
- Compétences et tools hardcodées (Python, JavaScript, Git, etc.)
- Impossible d'ajouter de nouveaux domaines sans modifier le core
- Pas de support pour Art, Finance, Ingénierie, Science, etc.

**Solution:**
- **Tool Registry dynamique** - Enregistrer tools au runtime
- **Competency Registry dynamique** - Ajouter compétences sans modifier core
- **Plugin System** - Packages indépendants qu'on charge/décharge
- **File Handlers extensibles** - Support nouveaux formats (images, CAD, etc.)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        GatheRing Core                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Plugin Manager                             │  │
│  │  • Load plugins                                         │  │
│  │  • Register tools & competencies                        │  │
│  │  • Manage dependencies                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │  Tool Registry │  │ Competency Reg. │  │  File Handler │ │
│  │                │  │                 │  │    Registry   │ │
│  │  • get(name)   │  │  • get(id)      │  │  • get(ext)   │ │
│  │  • register()  │  │  • register()   │  │  • register() │ │
│  │  • list()      │  │  • list()       │  │  • list()     │ │
│  └────────────────┘  └─────────────────┘  └───────────────┘ │
└──────────────────────────────────────────────────────────────┘
                               ▲
                               │ Loads
                               │
┌──────────────────────────────┼────────────────────────────────┐
│                         Plugins                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  Core Plugin     │  │  Design Plugin   │  │Finance Plug.│ │
│  │                  │  │                  │  │             │ │
│  │  • Python        │  │  • Stable Diff.  │  │• yfinance   │ │
│  │  • JavaScript    │  │  • Image editing │  │• Portfolio  │ │
│  │  • Git           │  │  • Figma API     │  │• DCF model  │ │
│  └──────────────────┘  └──────────────────┘  └─────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Composants

### 1. Tool Registry

**Fichier:** `gathering/core/tool_registry.py`

Registre dynamique de tools disponibles.

```python
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

class ToolCategory(str, Enum):
    """Tool categories."""
    FILE_SYSTEM = "filesystem"
    VERSION_CONTROL = "version_control"
    LLM = "llm"
    IMAGE = "image"
    FINANCE = "finance"
    CAD = "cad"
    AUDIO = "audio"
    VIDEO = "video"
    DATA_ANALYSIS = "data_analysis"
    WEB = "web"
    CUSTOM = "custom"

@dataclass
class ToolDefinition:
    """Tool definition."""
    name: str
    description: str
    category: ToolCategory
    function: Callable
    required_competencies: List[str]
    parameters: Dict[str, Any]  # JSON schema
    returns: Dict[str, Any]     # Return type schema
    examples: List[str]
    plugin_id: Optional[str] = None  # Which plugin provided this tool

class ToolRegistry:
    """Dynamic tool registry."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._tools_by_category: Dict[ToolCategory, List[str]] = {}
        self._tools_by_competency: Dict[str, List[str]] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        # Validate
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")

        # Store
        self._tools[tool.name] = tool

        # Index by category
        if tool.category not in self._tools_by_category:
            self._tools_by_category[tool.category] = []
        self._tools_by_category[tool.category].append(tool.name)

        # Index by competencies
        for comp in tool.required_competencies:
            if comp not in self._tools_by_competency:
                self._tools_by_competency[comp] = []
            self._tools_by_competency[comp].append(tool.name)

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        if name not in self._tools:
            return

        tool = self._tools[name]

        # Remove from category index
        if tool.category in self._tools_by_category:
            self._tools_by_category[tool.category].remove(name)

        # Remove from competency index
        for comp in tool.required_competencies:
            if comp in self._tools_by_competency:
                self._tools_by_competency[comp].remove(name)

        # Remove tool
        del self._tools[name]

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name."""
        return self._tools.get(name)

    def list_all(self) -> List[ToolDefinition]:
        """List all tools."""
        return list(self._tools.values())

    def list_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """List tools in category."""
        tool_names = self._tools_by_category.get(category, [])
        return [self._tools[name] for name in tool_names]

    def list_by_competency(self, competency: str) -> List[ToolDefinition]:
        """List tools for competency."""
        tool_names = self._tools_by_competency.get(competency, [])
        return [self._tools[name] for name in tool_names]

    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool."""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        return tool.function(**kwargs)

# Global registry
tool_registry = ToolRegistry()
```

### 2. Competency Registry

**Fichier:** `gathering/core/competency_registry.py`

Registre dynamique de compétences.

```python
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class CompetencyDefinition:
    """Competency definition."""
    id: str
    name: str
    description: str
    category: str  # "programming", "design", "finance", "engineering", etc.
    related_tools: List[str] = field(default_factory=list)
    parent_competency: Optional[str] = None
    skill_level_required: str = "intermediate"  # "beginner", "intermediate", "advanced"
    plugin_id: Optional[str] = None

class CompetencyRegistry:
    """Dynamic competency registry."""

    def __init__(self):
        self._competencies: Dict[str, CompetencyDefinition] = {}
        self._by_category: Dict[str, List[str]] = {}

    def register(self, competency: CompetencyDefinition) -> None:
        """Register a competency."""
        if competency.id in self._competencies:
            raise ValueError(f"Competency '{competency.id}' already registered")

        self._competencies[competency.id] = competency

        # Index by category
        if competency.category not in self._by_category:
            self._by_category[competency.category] = []
        self._by_category[competency.category].append(competency.id)

    def unregister(self, id: str) -> None:
        """Unregister a competency."""
        if id not in self._competencies:
            return

        comp = self._competencies[id]

        # Remove from category index
        if comp.category in self._by_category:
            self._by_category[comp.category].remove(id)

        del self._competencies[id]

    def get(self, id: str) -> Optional[CompetencyDefinition]:
        """Get competency by ID."""
        return self._competencies.get(id)

    def list_all(self) -> List[CompetencyDefinition]:
        """List all competencies."""
        return list(self._competencies.values())

    def list_by_category(self, category: str) -> List[CompetencyDefinition]:
        """List competencies in category."""
        comp_ids = self._by_category.get(category, [])
        return [self._competencies[id] for id in comp_ids]

# Global registry
competency_registry = CompetencyRegistry()
```

### 3. Plugin Base Class

**Fichier:** `gathering/plugins/base.py`

Base class pour tous les plugins.

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    version: str
    description: str
    author: str
    requires: List[str] = field(default_factory=list)  # Python packages
    gathering_version: str = ">=0.4.0"

class Plugin(ABC):
    """Base plugin class."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        pass

    @abstractmethod
    def register_tools(self, tool_registry: 'ToolRegistry') -> None:
        """Register plugin tools."""
        pass

    @abstractmethod
    def register_competencies(self, competency_registry: 'CompetencyRegistry') -> None:
        """Register plugin competencies."""
        pass

    def register_file_handlers(self, handler_registry: 'FileHandlerRegistry') -> None:
        """Register file handlers (optional)."""
        pass

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass

    def validate_dependencies(self) -> List[str]:
        """Validate dependencies. Returns list of missing packages."""
        missing = []
        for package in self.metadata.requires:
            try:
                __import__(package.split(">=")[0].split("==")[0])
            except ImportError:
                missing.append(package)
        return missing
```

### 4. Plugin Manager

**Fichier:** `gathering/plugins/manager.py`

Gestionnaire de plugins.

```python
from typing import Dict, List, Optional
import importlib
import sys
from pathlib import Path

class PluginManager:
    """Plugin manager."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        competency_registry: CompetencyRegistry,
    ):
        self.tool_registry = tool_registry
        self.competency_registry = competency_registry
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_dirs: List[Path] = []

    def add_plugin_directory(self, path: Path) -> None:
        """Add directory to search for plugins."""
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)
            sys.path.insert(0, str(path))

    def load_plugin(self, plugin_id: str, plugin_class: type[Plugin]) -> None:
        """Load a plugin."""
        # Check if already loaded
        if plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' already loaded")

        # Instantiate plugin
        plugin = plugin_class()

        # Validate dependencies
        missing = plugin.validate_dependencies()
        if missing:
            raise ImportError(
                f"Plugin '{plugin_id}' missing dependencies: {', '.join(missing)}"
            )

        # Register tools
        plugin.register_tools(self.tool_registry)
        print(f"[Plugin] {plugin_id}: Registered tools")

        # Register competencies
        plugin.register_competencies(self.competency_registry)
        print(f"[Plugin] {plugin_id}: Registered competencies")

        # Call on_load
        plugin.on_load()

        # Store
        self._plugins[plugin_id] = plugin

        print(f"[Plugin] {plugin_id} loaded successfully")

    def unload_plugin(self, plugin_id: str) -> None:
        """Unload a plugin."""
        if plugin_id not in self._plugins:
            return

        plugin = self._plugins[plugin_id]

        # Call on_unload
        plugin.on_unload()

        # Unregister tools
        for tool in self.tool_registry.list_all():
            if tool.plugin_id == plugin_id:
                self.tool_registry.unregister(tool.name)

        # Unregister competencies
        for comp in self.competency_registry.list_all():
            if comp.plugin_id == plugin_id:
                self.competency_registry.unregister(comp.id)

        # Remove
        del self._plugins[plugin_id]

        print(f"[Plugin] {plugin_id} unloaded")

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get loaded plugin."""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[Plugin]:
        """List all loaded plugins."""
        return list(self._plugins.values())

# Global plugin manager
plugin_manager = None

def get_plugin_manager() -> PluginManager:
    """Get global plugin manager."""
    global plugin_manager
    if plugin_manager is None:
        from gathering.core.tool_registry import tool_registry
        from gathering.core.competency_registry import competency_registry
        plugin_manager = PluginManager(tool_registry, competency_registry)
    return plugin_manager
```

### 5. Core Plugin (Existing Tools)

**Fichier:** `gathering/plugins/core.py`

Plugin qui contient les tools existantes (Python, Git, etc.).

```python
from gathering.plugins.base import Plugin, PluginMetadata
from gathering.core.tool_registry import ToolDefinition, ToolCategory
from gathering.core.competency_registry import CompetencyDefinition

class CorePlugin(Plugin):
    """Core GatheRing plugin with existing tools."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="core",
            name="Core GatheRing Tools",
            version="1.0.0",
            description="Core tools for software development (Python, Git, etc.)",
            author="GatheRing Team",
            requires=[],
        )

    def register_tools(self, tool_registry):
        """Register core tools."""
        # File system tools
        tool_registry.register(ToolDefinition(
            name="fs_read",
            description="Read file contents",
            category=ToolCategory.FILE_SYSTEM,
            function=self._fs_read,
            required_competencies=["file_management"],
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            },
            returns={"type": "string", "description": "File contents"},
            examples=["fs_read(path='README.md')"],
            plugin_id="core",
        ))

        # Git tools
        tool_registry.register(ToolDefinition(
            name="git_status",
            description="Get git status",
            category=ToolCategory.VERSION_CONTROL,
            function=self._git_status,
            required_competencies=["git"],
            parameters={"type": "object", "properties": {}},
            returns={"type": "object", "description": "Git status"},
            examples=["git_status()"],
            plugin_id="core",
        ))

        # LLM tools
        tool_registry.register(ToolDefinition(
            name="llm_chat",
            description="Chat with LLM",
            category=ToolCategory.LLM,
            function=self._llm_chat,
            required_competencies=["language_models"],
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            },
            returns={"type": "string", "description": "LLM response"},
            examples=["llm_chat(message='Hello')"],
            plugin_id="core",
        ))

        # Add all existing tools...

    def register_competencies(self, competency_registry):
        """Register core competencies."""
        competency_registry.register(CompetencyDefinition(
            id="python",
            name="Python Programming",
            description="Python development, testing, packaging",
            category="programming",
            related_tools=["fs_read", "fs_write", "pytest"],
            plugin_id="core",
        ))

        competency_registry.register(CompetencyDefinition(
            id="git",
            name="Version Control (Git)",
            description="Git operations, branching, PRs",
            category="programming",
            related_tools=["git_status", "git_commit", "git_push"],
            plugin_id="core",
        ))

        # Add all existing competencies...

    def _fs_read(self, path: str) -> str:
        """Read file implementation."""
        with open(path, 'r') as f:
            return f.read()

    def _git_status(self) -> dict:
        """Git status implementation."""
        import subprocess
        result = subprocess.run(['git', 'status', '--short'], capture_output=True)
        return {"output": result.stdout.decode()}

    def _llm_chat(self, message: str) -> str:
        """LLM chat implementation."""
        # Existing LLM logic
        pass
```

## Exemple de Plugin

### Design Plugin

**Fichier:** `gathering/plugins/design.py`

Plugin pour design (Stable Diffusion, image editing).

```python
from gathering.plugins.base import Plugin, PluginMetadata
from gathering.core.tool_registry import ToolDefinition, ToolCategory
from gathering.core.competency_registry import CompetencyDefinition

class DesignPlugin(Plugin):
    """Design tools plugin (Stable Diffusion, image editing)."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="design",
            name="Design Tools",
            version="1.0.0",
            description="Tools for graphic design, image generation, and editing",
            author="GatheRing Community",
            requires=["Pillow>=10.0", "requests>=2.31"],
        )

    def register_tools(self, tool_registry):
        """Register design tools."""
        # Image generation
        tool_registry.register(ToolDefinition(
            name="generate_image",
            description="Generate image using Stable Diffusion",
            category=ToolCategory.IMAGE,
            function=self._generate_image,
            required_competencies=["ai_image_generation"],
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "width": {"type": "integer", "default": 512},
                    "height": {"type": "integer", "default": 512},
                },
                "required": ["prompt"]
            },
            returns={"type": "string", "description": "Path to generated image"},
            examples=["generate_image(prompt='A sunset over mountains')"],
            plugin_id="design",
        ))

        # Image editing
        tool_registry.register(ToolDefinition(
            name="edit_image",
            description="Edit image (resize, crop, filters)",
            category=ToolCategory.IMAGE,
            function=self._edit_image,
            required_competencies=["image_editing"],
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operations": {"type": "array"},
                },
                "required": ["path", "operations"]
            },
            returns={"type": "string", "description": "Path to edited image"},
            examples=["edit_image(path='image.png', operations=[{'type': 'resize', 'width': 800}])"],
            plugin_id="design",
        ))

    def register_competencies(self, competency_registry):
        """Register design competencies."""
        competency_registry.register(CompetencyDefinition(
            id="ai_image_generation",
            name="AI Image Generation",
            description="Generate images using AI (Stable Diffusion, DALL-E)",
            category="design",
            related_tools=["generate_image"],
            plugin_id="design",
        ))

        competency_registry.register(CompetencyDefinition(
            id="image_editing",
            name="Image Editing",
            description="Edit images (resize, crop, filters, compositing)",
            category="design",
            related_tools=["edit_image"],
            plugin_id="design",
        ))

    def _generate_image(self, prompt: str, width: int = 512, height: int = 512) -> str:
        """Generate image using Stable Diffusion API."""
        import requests
        from PIL import Image
        import io

        # Call Stable Diffusion API (example)
        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers={"Authorization": "Bearer YOUR_API_KEY"},
            json={
                "text_prompts": [{"text": prompt}],
                "width": width,
                "height": height,
            }
        )

        # Save image
        image_data = response.json()["artifacts"][0]["base64"]
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        output_path = f"generated_{uuid.uuid4()}.png"
        image.save(output_path)

        return output_path

    def _edit_image(self, path: str, operations: list) -> str:
        """Edit image."""
        from PIL import Image

        image = Image.open(path)

        for op in operations:
            if op["type"] == "resize":
                image = image.resize((op["width"], op.get("height", op["width"])))
            elif op["type"] == "crop":
                image = image.crop((op["x"], op["y"], op["x2"], op["y2"]))
            # Add more operations...

        output_path = f"edited_{uuid.uuid4()}.png"
        image.save(output_path)

        return output_path
```

## Usage

### Charger les plugins

```python
from gathering.plugins.manager import get_plugin_manager
from gathering.plugins.core import CorePlugin
from gathering.plugins.design import DesignPlugin

# Get manager
manager = get_plugin_manager()

# Load core plugin (existing tools)
manager.load_plugin("core", CorePlugin)

# Load design plugin
manager.load_plugin("design", DesignPlugin)

# List loaded plugins
for plugin in manager.list_plugins():
    print(f"Plugin: {plugin.metadata.name} v{plugin.metadata.version}")
```

### Utiliser les tools

```python
from gathering.core.tool_registry import tool_registry

# List all tools
for tool in tool_registry.list_all():
    print(f"- {tool.name}: {tool.description}")

# List design tools
design_tools = tool_registry.list_by_category(ToolCategory.IMAGE)
for tool in design_tools:
    print(f"- {tool.name}")

# Execute tool
result = tool_registry.execute(
    "generate_image",
    prompt="A sunset over mountains",
    width=1024,
    height=768
)
print(f"Generated: {result}")
```

### Créer un agent avec nouvelles compétences

```python
from gathering.core.competency_registry import competency_registry

# List design competencies
design_comps = competency_registry.list_by_category("design")

# Create agent with design skills
agent = await create_agent(
    name="DesignBot",
    competencies=["ai_image_generation", "image_editing", "graphic_design"],
)
```

## Prochaines Étapes

**Phase 6.1: Registries** (1 semaine)
- Implémenter ToolRegistry
- Implémenter CompetencyRegistry
- Tests unitaires

**Phase 6.2: Plugin System** (1 semaine)
- Plugin base class
- PluginManager
- CorePlugin (migrer tools existantes)

**Phase 6.3: Example Plugin** (3-4 jours)
- DesignPlugin complet
- Tests d'intégration
- Documentation

**Phase 6.4: Agent Integration** (3-4 jours)
- Modifier AgentWrapper pour utiliser registries
- Backward compatibility
- Tests

---

**Le Plugin System permettra à GatheRing de supporter n'importe quel domaine !** 🚀
