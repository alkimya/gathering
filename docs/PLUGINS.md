# GatheRing Plugin System

The plugin system allows extending GatheRing with custom tools, competencies, and capabilities without modifying core code.

## Overview

Plugins provide:
- **Tools**: Functions that agents can call (e.g., read files, generate images, run calculations)
- **Competencies**: Skills that agents can have (e.g., Python programming, design, finance)
- **Dynamic loading**: Load/unload plugins at runtime
- **Discovery**: Automatically find plugins in directories
- **Agent creation**: Agents can create plugins dynamically

## Quick Start

### Using the Plugin Manager

```python
from gathering.plugins import plugin_manager
from gathering.plugins.core import CorePlugin

# Register plugin class
plugin_manager.register_plugin_class("core", CorePlugin)

# Load with configuration
plugin_manager.load_plugin("core", config={"base_path": "."})

# Enable the plugin
plugin_manager.enable_plugin("core")

# Use tools
from gathering.core.tool_registry import tool_registry
result = tool_registry.execute("calculate", expression="2 + 2")
```

### Discovering Plugins

```python
from pathlib import Path
from gathering.plugins import plugin_manager

# Add plugin directory
plugin_manager.add_plugin_directory(Path("./my_plugins"))

# Discover plugins (registers but doesn't load)
discovered = plugin_manager.discover_plugins()
print(f"Found plugins: {list(discovered.keys())}")

# Load a discovered plugin
plugin_manager.load_plugin("my_plugin")
```

## Creating a Plugin

### Basic Plugin Structure

```python
from gathering.plugins.base import Plugin, PluginMetadata
from gathering.core.tool_registry import ToolDefinition, ToolCategory
from gathering.core.competency_registry import (
    CompetencyDefinition,
    CompetencyCategory,
    CompetencyLevel,
)


class MyPlugin(Plugin):
    """My custom plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my_plugin",
            name="My Plugin",
            version="1.0.0",
            description="A custom plugin for GatheRing",
            author="Your Name",
            python_dependencies=["requests>=2.28.0"],  # Optional
        )

    def register_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="my_tool",
                description="Does something useful",
                category=ToolCategory.CUSTOM,
                function=self.my_tool_function,
                required_competencies=["my_skill"],
                parameters={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                    },
                    "required": ["input"],
                },
                returns={"type": "string"},
                plugin_id="my_plugin",
            )
        ]

    def register_competencies(self) -> list[CompetencyDefinition]:
        return [
            CompetencyDefinition(
                id="my_skill",
                name="My Skill",
                description="Ability to use my plugin",
                category=CompetencyCategory.CUSTOM,
                level=CompetencyLevel.INTERMEDIATE,
                tools_enabled=["my_tool"],
                plugin_id="my_plugin",
            )
        ]

    def my_tool_function(self, input: str) -> str:
        """Tool implementation."""
        return f"Processed: {input}"


# Export for discovery
plugin_class = MyPlugin
```

### Plugin Metadata

```python
@dataclass
class PluginMetadata:
    id: str                      # Unique identifier (e.g., "design")
    name: str                    # Human-readable name
    version: str                 # Semantic version
    description: str             # What the plugin does
    author: str = ""             # Author name
    author_email: str = ""       # Contact email
    license: str = "MIT"         # License
    homepage: str = ""           # Repository URL
    tags: list[str] = []         # For discovery
    dependencies: list[str] = [] # Other plugins required
    python_dependencies: list[str] = []  # pip packages
    min_gathering_version: str = "0.1.0"
    config_schema: dict = {}     # JSON Schema for config
```

### Plugin Lifecycle

```
1. register_plugin_class() - Register the plugin class
2. load_plugin()           - Instantiate and validate
   ├── __init__()          - Create instance with config
   ├── validate_dependencies() - Check Python packages
   └── load()              - Initialize plugin
3. register_tools()        - Get tools to register
4. register_competencies() - Get competencies to register
5. enable_plugin()         - Activate the plugin
   └── on_enable()         - Plugin becomes active
6. disable_plugin()        - Deactivate (reversible)
   └── on_disable()        - Plugin becomes inactive
7. unload_plugin()         - Remove completely
   └── unload()            - Cleanup resources
```

## Dynamic Plugin Creation

Agents can create plugins at runtime without writing files:

```python
from gathering.plugins import plugin_manager
from gathering.core.tool_registry import ToolCategory

def my_function(x: int, y: int) -> int:
    return x + y

plugin = plugin_manager.create_dynamic_plugin(
    plugin_id="math_helper",
    name="Math Helper",
    description="Simple math operations",
    tools=[
        {
            "name": "add",
            "description": "Add two numbers",
            "function": my_function,
            "category": ToolCategory.UTILITY,
            "parameters": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
        }
    ],
)

# The plugin is immediately usable
from gathering.core.tool_registry import tool_registry
result = tool_registry.execute("add", x=5, y=3)  # Returns 8
```

### Saving Dynamic Plugins

```python
# Save to file for future sessions
plugin_manager.save_dynamic_plugin(
    "math_helper",
    output_path="./plugins/math_helper.py"
)
```

## REST API

The plugin system exposes a REST API at `/plugins`:

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plugins` | List all plugins |
| GET | `/plugins/available` | List available plugin IDs |
| GET | `/plugins/stats` | Get plugin statistics |
| GET | `/plugins/{id}` | Get plugin info |
| GET | `/plugins/{id}/health` | Check plugin health |
| GET | `/plugins/{id}/tools` | List plugin tools |
| POST | `/plugins/load` | Load a plugin |
| POST | `/plugins/{id}/unload` | Unload a plugin |
| POST | `/plugins/{id}/enable` | Enable a plugin |
| POST | `/plugins/{id}/disable` | Disable a plugin |
| POST | `/plugins/discover` | Discover plugins in directory |
| POST | `/plugins/dynamic` | Create dynamic plugin |
| POST | `/plugins/{id}/save` | Save dynamic plugin |
| GET | `/plugins/health/all` | Health check all plugins |

### Example: Create Dynamic Plugin via API

```bash
curl -X POST http://localhost:8000/plugins/dynamic \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "greeter",
    "name": "Greeter Plugin",
    "description": "A simple greeting plugin",
    "tools": [
      {
        "name": "greet",
        "description": "Greet someone",
        "category": "custom",
        "code": "def greet(name): return f\"Hello, {name}!\"",
        "parameters": {"name": {"type": "string"}}
      }
    ]
  }'
```

## Built-in Plugins

### Core Plugin

Essential tools always available:

| Tool | Category | Description |
|------|----------|-------------|
| `calculate` | utility | Safe math evaluation |
| `read_file` | filesystem | Read file contents |
| `write_file` | filesystem | Write to files |
| `list_directory` | filesystem | List directory contents |
| `git_status` | version_control | Git repository status |
| `git_diff` | version_control | Show git diff |
| `run_command` | code_execution | Execute shell commands |
| `python_eval` | code_execution | Execute Python code |

### Design Plugin (Example)

AI-powered design tools:

| Tool | Description |
|------|-------------|
| `generate_image` | AI image generation |
| `edit_image` | Image manipulation |
| `generate_palette` | Color palette creation |
| `create_mockup` | UI mockup generation |

## Tool Categories

```python
class ToolCategory(str, Enum):
    FILE_SYSTEM = "filesystem"
    VERSION_CONTROL = "version_control"
    CODE_EXECUTION = "code_execution"
    TESTING = "testing"
    LLM = "llm"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DATA_ANALYSIS = "data_analysis"
    DATABASE = "database"
    FINANCE = "finance"
    CAD = "cad"
    WEB = "web"
    API = "api"
    CUSTOM = "custom"
    UTILITY = "utility"
```

## Competency Categories

```python
class CompetencyCategory(str, Enum):
    # Development
    PROGRAMMING = "programming"
    WEB_DEVELOPMENT = "web_development"
    DATABASE = "database"
    DEVOPS = "devops"

    # AI & ML
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"

    # Creative
    GRAPHIC_DESIGN = "graphic_design"
    UI_UX_DESIGN = "ui_ux_design"

    # Business
    FINANCIAL_ANALYSIS = "financial_analysis"
    MARKETING = "marketing"

    # Science
    DATA_SCIENCE = "data_science"
    SCIENTIFIC_COMPUTING = "scientific_computing"

    # Other
    CUSTOM = "custom"
```

## Best Practices

### 1. Use Clear IDs

```python
# Good
id="image_generator"
id="financial_analyzer"

# Bad
id="plugin1"
id="my_tool"
```

### 2. Define Dependencies

```python
PluginMetadata(
    id="advanced_ml",
    dependencies=["core", "data_science"],  # Other plugins
    python_dependencies=["torch>=2.0", "transformers"],
)
```

### 3. Implement Health Checks

```python
def health_check(self) -> dict:
    return {
        "plugin_id": self.metadata.id,
        "status": "healthy",  # or "degraded", "unhealthy"
        "details": {
            "api_connected": self._check_api(),
            "cache_size": len(self._cache),
        }
    }
```

### 4. Handle Configuration

```python
def __init__(self, config: dict | None = None):
    super().__init__(config)
    self.api_key = config.get("api_key") if config else None
    self.max_size = config.get("max_size", 1024)
```

### 5. Use Appropriate Categories

Match tools to the right category for discoverability:
- `FILE_SYSTEM` for file operations
- `VERSION_CONTROL` for git/svn
- `LLM` for AI model interactions
- `CUSTOM` for domain-specific tools

## Example: Finance Plugin

```python
class FinancePlugin(Plugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="finance",
            name="Finance Tools",
            version="1.0.0",
            description="Financial analysis and calculations",
            python_dependencies=["yfinance", "pandas"],
        )

    def register_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="stock_price",
                description="Get current stock price",
                category=ToolCategory.FINANCE,
                function=self.get_stock_price,
                parameters={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                    },
                    "required": ["symbol"],
                },
                plugin_id="finance",
            ),
            ToolDefinition(
                name="portfolio_value",
                description="Calculate portfolio value",
                category=ToolCategory.FINANCE,
                function=self.calculate_portfolio,
                parameters={...},
                plugin_id="finance",
            ),
        ]

    def get_stock_price(self, symbol: str) -> dict:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        return {"symbol": symbol, "price": ticker.info["regularMarketPrice"]}
```

## Plugin Discovery Convention

For automatic discovery, plugins should:

1. Be in a `.py` file or package with `__init__.py`
2. Contain a `Plugin` subclass
3. Optionally export `plugin_class = MyPlugin`

```
my_plugins/
├── image_tools.py        # Single file plugin
├── finance/              # Package plugin
│   ├── __init__.py
│   └── tools.py
└── _internal/            # Ignored (starts with _)
    └── helpers.py
```
