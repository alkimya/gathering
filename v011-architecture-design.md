# GatheRing v0.1.1 Architecture Design 🧱

## Refactored Directory Structure

```
gathering/
├── agents/                 # Agent implementations
│   ├── __init__.py
│   ├── base.py            # BaseAgent class
│   └── ethical.py         # EthicalAgent with Three Laws
│
├── personality/           # Personality system
│   ├── __init__.py
│   ├── traits.py          # Trait definitions
│   ├── dynamics.py        # Evolution algorithms
│   └── ethical_core.py    # Immutable ethical traits
│
├── memory/                # Memory layers
│   ├── __init__.py
│   ├── base.py           # Memory interfaces
│   ├── shortterm.py      # Working memory
│   ├── vectorstore.py    # Vector embeddings
│   └── knowledge.py      # Knowledge graphs
│
├── providers/             # LLM providers via LangChain
│   ├── __init__.py
│   ├── base.py           # Provider interface
│   ├── langchain.py      # LangChain wrapper
│   └── mcp.py            # MCP server connector
│
├── tools/                 # Agent tools
│   ├── __init__.py
│   ├── base.py           # Tool interface
│   ├── filesystem.py     # File operations
│   ├── git.py            # Git operations
│   └── mcp_tools.py      # MCP protocol tools
│
├── core/                  # Core abstractions
│   ├── __init__.py
│   ├── exceptions.py     # Custom exceptions
│   └── types.py          # Type definitions
│
└── utils/                 # Utilities
    ├── __init__.py
    ├── async_helpers.py   # Async utilities
    └── vectors.py         # Vectorization helpers
```

## Key Design Patterns

### 1. Hexagonal Architecture
- **Domain** (center): Agents, Personality, Memory
- **Ports** (interfaces): Tool, Provider, Memory interfaces  
- **Adapters** (implementations): LangChain, MCP, Filesystem

### 2. Dependency Injection
```python
class BaseAgent:
    def __init__(self, 
                 provider: BaseProvider,
                 memory: BaseMemory,
                 personality: PersonalitySystem,
                 tools: List[BaseTool]):
        # All dependencies injected
```

### 3. Strategy Pattern for Providers
```python
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        pass

class LangChainProvider(BaseProvider):
    def __init__(self, chain: LLMChain):
        self.chain = chain
    
    async def complete(self, prompt: str, **kwargs) -> str:
        # Use LangChain for completion
```

## Memory Architecture

### Vectorized Memory Layers
```
┌─────────────────────────────────────┐
│         Knowledge Graph             │
│    (Persistent, Structured)         │
├─────────────────────────────────────┤
│        Vector Store                 │
│   (Embeddings, Semantic Search)    │
├─────────────────────────────────────┤
│      Short-term Memory              │
│   (Working Memory, 7±2 items)       │
└─────────────────────────────────────┘
```

### Vector Operations
```python
import numpy as np
from typing import List, Tuple

class VectorMemory:
    def __init__(self, embedding_dim: int = 768):
        self.embeddings: np.ndarray = np.empty((0, embedding_dim))
        self.metadata: List[dict] = []
    
    def add_memory(self, text: str, embedding: np.ndarray) -> None:
        """Add vectorized memory with O(1) complexity."""
        self.embeddings = np.vstack([self.embeddings, embedding])
        
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[int, float]]:
        """Vectorized similarity search with O(n) complexity."""
        # Efficient cosine similarity using numpy
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        top_k_indices = np.argpartition(similarities, -k)[-k:]
        return [(idx, similarities[idx]) for idx in top_k_indices]
```

## Personality System Design

### Trait Categories
```python
from enum import Enum
from dataclasses import dataclass

class TraitCategory(Enum):
    ETHICAL = "ethical"      # Immutable
    COGNITIVE = "cognitive"  # How they think
    EMOTIONAL = "emotional"  # How they feel
    SOCIAL = "social"       # How they interact
    BEHAVIORAL = "behavioral" # How they act

@dataclass
class PersonalityTrait:
    name: str
    category: TraitCategory
    intensity: float  # 0.0 to 1.0
    mutable: bool
    description: str
    
    def evolve(self, delta: float, smooth: bool = True) -> None:
        """Smoothly evolve trait intensity."""
        if not self.mutable:
            raise ImmutableTraitError(f"Cannot modify {self.name}")
        
        if smooth:
            # Sigmoid smoothing for natural transitions
            delta = delta * (1 - abs(2 * self.intensity - 1))
        
        self.intensity = np.clip(self.intensity + delta, 0.0, 1.0)
```

### Extended Trait Library
```python
TRAIT_LIBRARY = {
    # Ethical (Immutable) - Three Laws of AI
    "harmlessness": PersonalityTrait("harmlessness", TraitCategory.ETHICAL, 1.0, False, 
                                   "Never harm humans or allow harm through inaction"),
    "helpful": PersonalityTrait("helpful", TraitCategory.ETHICAL, 1.0, False,
                               "Always assist humans to the best of ability"),
    "honest": PersonalityTrait("honest", TraitCategory.ETHICAL, 1.0, False,
                              "Always be truthful and transparent"),
    
    # Cognitive Traits
    "analytical": PersonalityTrait("analytical", TraitCategory.COGNITIVE, 0.5, True,
                                  "Tendency to break down problems systematically"),
    "creative": PersonalityTrait("creative", TraitCategory.COGNITIVE, 0.5, True,
                                "Ability to think outside the box"),
    "curious": PersonalityTrait("curious", TraitCategory.COGNITIVE, 0.5, True,
                               "Desire to learn and explore"),
    "logical": PersonalityTrait("logical", TraitCategory.COGNITIVE, 0.5, True,
                               "Preference for reasoned thinking"),
    "intuitive": PersonalityTrait("intuitive", TraitCategory.COGNITIVE, 0.5, True,
                                 "Reliance on instinct and patterns"),
    
    # Emotional Traits
    "empathetic": PersonalityTrait("empathetic", TraitCategory.EMOTIONAL, 0.5, True,
                                  "Ability to understand others' feelings"),
    "optimistic": PersonalityTrait("optimistic", TraitCategory.EMOTIONAL, 0.5, True,
                                  "Positive outlook on situations"),
    "patient": PersonalityTrait("patient", TraitCategory.EMOTIONAL, 0.5, True,
                               "Tolerance for delays or problems"),
    "enthusiastic": PersonalityTrait("enthusiastic", TraitCategory.EMOTIONAL, 0.5, True,
                                    "Showing excitement and energy"),
    
    # Social Traits
    "collaborative": PersonalityTrait("collaborative", TraitCategory.SOCIAL, 0.5, True,
                                     "Works well with others"),
    "assertive": PersonalityTrait("assertive", TraitCategory.SOCIAL, 0.5, True,
                                 "Confident in expressing views"),
    "diplomatic": PersonalityTrait("diplomatic", TraitCategory.SOCIAL, 0.5, True,
                                  "Tactful in difficult situations"),
    "humorous": PersonalityTrait("humorous", TraitCategory.SOCIAL, 0.5, True,
                                "Uses appropriate humor"),
    
    # Behavioral Traits
    "methodical": PersonalityTrait("methodical", TraitCategory.BEHAVIORAL, 0.5, True,
                                  "Systematic approach to tasks"),
    "adaptable": PersonalityTrait("adaptable", TraitCategory.BEHAVIORAL, 0.5, True,
                                 "Adjusts to new situations"),
    "persistent": PersonalityTrait("persistent", TraitCategory.BEHAVIORAL, 0.5, True,
                                  "Continues despite obstacles"),
    "efficient": PersonalityTrait("efficient", TraitCategory.BEHAVIORAL, 0.5, True,
                                 "Maximizes output with minimal waste")
}
```

## Asynchronous Design

### Async Tool Execution
```python
class BaseTool(ABC):
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool asynchronously."""
        pass

class FileSystemTool(BaseTool):
    async def execute(self, action: str, path: str, **kwargs) -> ToolResult:
        """Async file operations."""
        async with aiofiles.open(path, mode='r') as f:
            content = await f.read()
        return ToolResult(success=True, output=content)
```

### Parallel Agent Execution
```python
async def parallel_agent_execution(agents: List[BaseAgent], prompt: str) -> List[str]:
    """Execute multiple agents in parallel."""
    tasks = [agent.aprocess_message(prompt) for agent in agents]
    responses = await asyncio.gather(*tasks)
    return responses
```

## MCP Integration

### MCP Server Connection
```python
class MCPProvider(BaseProvider):
    def __init__(self, server_url: str):
        self.client = MCPClient(server_url)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        response = await self.client.send_prompt(prompt, **kwargs)
        return response.content
    
    async def list_tools(self) -> List[MCPTool]:
        return await self.client.get_available_tools()
```

This architecture provides:
- 🧩 Modular, extensible design
- 🚀 Async-first implementation
- 🧮 Vectorized operations for performance
- 🔒 Ethical constraints built-in
- 🔌 Easy integration with LangChain/MCP
- 📦 Clean separation of concerns