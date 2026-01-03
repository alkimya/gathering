# Agents

Agents are AI personalities that can think, communicate, and collaborate. Each agent has unique traits, skills, and behaviors.

## Agent Anatomy

An agent consists of:

```
┌─────────────────────────────────────────┐
│                 Agent                    │
├─────────────────────────────────────────┤
│  Identity                               │
│  ├── Name, Role, Background             │
│  └── Model & Provider                   │
├─────────────────────────────────────────┤
│  Personality                            │
│  ├── Traits (curious, analytical, etc.) │
│  └── Communication style                │
├─────────────────────────────────────────┤
│  Capabilities                           │
│  ├── Skills & Competencies              │
│  └── Tools (filesystem, calculator)     │
├─────────────────────────────────────────┤
│  Memory                                 │
│  ├── Short-term (conversation)          │
│  └── Long-term (persistent)             │
└─────────────────────────────────────────┘
```

## Creating Agents

### Basic Agent

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sophie",
    "role": "Software Architect",
    "provider": "openai",
    "model": "gpt-4"
  }'
```

### Full Agent Configuration

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sophie Chen",
    "role": "Lead Technical Architect",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "personality": {
      "traits": ["analytical", "creative", "detail-oriented"],
      "communication_style": "professional",
      "languages": ["English", "French", "Mandarin"]
    },
    "background": {
      "history": "15 years in software architecture, PhD from MIT",
      "expertise": ["distributed systems", "API design", "cloud architecture"]
    },
    "config": {
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }'
```

## Supported Providers

GatheRing supports multiple LLM providers:

### OpenAI

```json
{
  "provider": "openai",
  "model": "gpt-4o"
}
```

Available models: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`

### Anthropic

```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514"
}
```

Available models: `claude-sonnet-4-20250514`, `claude-opus-4-20250514`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`

### Ollama (Local)

```json
{
  "provider": "ollama",
  "model": "llama3.2"
}
```

Available models: Any model installed in your local Ollama instance

### Choosing the Right Provider

| Provider | Use Case | Considerations |
|----------|----------|----------------|
| OpenAI | General purpose, wide compatibility | API costs, rate limits |
| Anthropic | Long context, complex reasoning | API costs, rate limits |
| Ollama | Privacy, offline use, cost control | Requires local setup, hardware dependent |

## Personality System

### Available Traits

| Category | Traits |
|----------|--------|
| Cognitive | `analytical`, `creative`, `logical`, `intuitive` |
| Social | `empathetic`, `collaborative`, `diplomatic`, `direct` |
| Work Style | `detail-oriented`, `big-picture`, `methodical`, `agile` |
| Communication | `formal`, `casual`, `technical`, `accessible` |

### Trait Intensity

Traits can have varying intensities (0.0 to 1.0):

```json
{
  "personality": {
    "traits": {
      "curious": 0.9,
      "analytical": 0.8,
      "creative": 0.6
    }
  }
}
```

### Communication Styles

- `professional`: Formal, structured responses
- `casual`: Friendly, conversational tone
- `technical`: Precise, jargon-appropriate
- `accessible`: Simple, clear explanations

## Agent Skills

### Built-in Skills

```json
{
  "skills": [
    "code_review",
    "documentation",
    "testing",
    "debugging",
    "architecture"
  ]
}
```

### Custom Competencies

```json
{
  "competencies": {
    "python": "expert",
    "react": "advanced",
    "kubernetes": "intermediate",
    "machine_learning": "basic"
  }
}
```

## Agent Tools

Agents can use tools to interact with the world:

### Available Tools

| Tool | Description |
|------|-------------|
| `filesystem` | Read/write files |
| `calculator` | Mathematical operations |
| `web_search` | Search the web |
| `code_executor` | Run code snippets |
| `git` | Git operations |

### Configuring Tools

```json
{
  "tools": {
    "filesystem": {
      "enabled": true,
      "permissions": ["read", "write"],
      "base_path": "/workspace"
    },
    "calculator": {
      "enabled": true
    }
  }
}
```

## Agent Memory

### Memory Scopes

- **Conversation**: Current conversation context
- **Session**: Current session across conversations
- **Agent**: Persistent agent-specific memories
- **Circle**: Shared with circle members
- **Global**: Shared across all agents

### Memory Operations

```bash
# Get agent memories
curl http://localhost:8000/agents/1/memories

# Add a memory
curl -X POST http://localhost:8000/agents/1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "key": "user_preference",
    "value": "Prefers detailed explanations",
    "scope": "agent"
  }'
```

## Agent States

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Idle    │────▶│  Active  │────▶│  Busy    │
└──────────┘     └──────────┘     └──────────┘
     ▲                                  │
     └──────────────────────────────────┘
```

### States

- **Idle**: Ready to receive tasks
- **Active**: Engaged in conversation
- **Busy**: Processing a complex task
- **Offline**: Not available

## Agent Sessions

Sessions track agent activity:

```bash
# Start a session
curl -X POST http://localhost:8000/agents/1/sessions

# Get current session
curl http://localhost:8000/agents/1/sessions/current

# End session
curl -X POST http://localhost:8000/agents/1/sessions/current/end
```

## Using Personas

GatheRing includes pre-built personas for common roles. See the `personas/` directory for examples:

- `sophie_chen.md` - Lead Technical Architect
- `olivia_nakamoto.md` - Senior Systems Engineer
- `marcus_johnson.md` - DevOps Engineer
- And many more...

### Loading a Persona

```python
from gathering import Agent

# Load from persona file
agent = Agent.from_persona("personas/sophie_chen.md")
```

## Best Practices

### 1. Match Model to Task

Use faster/cheaper models for simple tasks, more capable models for complex reasoning.

### 2. Define Clear Roles

Each agent should have a specific, well-defined role.

### 3. Balanced Personalities

Avoid extreme trait intensities; balance creates more natural interactions.

### 4. Appropriate Memory Scope

Use the narrowest scope that works for your use case.

### 5. Tool Permissions

Only grant tools that the agent actually needs.

## Related Topics

- [Circles](circles.md) - Organizing agents into teams
- [Workspace](workspace.md) - Agent development environment
- [API Reference](../api/reference.md) - Complete API documentation
