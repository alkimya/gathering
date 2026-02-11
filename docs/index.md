# GatheRing

A collaborative multi-agent AI framework built with Python, FastAPI, and React.

GatheRing is a highly customizable and modular framework for creating and managing AI agents with complex personalities, diverse competencies, and professional expertise. Agents can collaborate in "Circles", use external tools, and be managed through a web dashboard.

## Key Features

- **Multi-Model Support**: Anthropic (Claude), OpenAI, DeepSeek, and local models via Ollama
- **Gathering Circles**: Team orchestration with task routing, reviews, and conflict detection
- **Agent Persistence**: Personas, memory, sessions with automatic context injection
- **Agent Conversations**: Direct inter-agent collaboration with turn strategies
- **Pipeline Execution**: DAG-based workflow engine with topological traversal, retry + circuit breakers, cancellation and timeout
- **Schedule System**: Cron-based action dispatch (run_task, execute_pipeline, send_notification, call_api) with crash recovery
- **REST API**: Full FastAPI backend with 206 rate-limited endpoints and WebSocket support
- **React Dashboard**: Modern Web3 dark theme UI for agents, circles, tasks, and conversations
- **RAG Support**: PostgreSQL + pgvector for semantic memory search
- **Knowledge Base**: Semantic search across documentation and best practices
- **Skills System**: 18+ skills with JSON Schema validation and async execution
- **Agent Autonomy**: Background tasks, scheduled actions, goal management
- **Integrated Workspace**: Full-featured IDE with file explorer, code editor, terminal, and git integration
- **Security**: JWT auth with DB-persisted token blacklist, constant-time comparisons, SQL injection prevention, path traversal defense, audit logging
- **Rate Limiting**: Per-endpoint rate limits with 4 tiers (strict/standard/relaxed/bulk) via slowapi
- **Multi-Instance**: PostgreSQL advisory locks for distributed task coordination, graceful shutdown with request draining
- **Observability**: Structured logging (structlog) with JSON output and request correlation IDs
- **Fully Tested**: 1200+ tests covering auth lifecycle, pipeline execution, scheduler recovery, event concurrency

## Quick Links

::::{grid} 2
:gutter: 3

:::{grid-item-card} Getting Started
:link: user/installation
:link-type: doc

Install GatheRing and run your first circle
:::

:::{grid-item-card} Dashboard Guide
:link: user/dashboard
:link-type: doc

Learn to use the web dashboard
:::

:::{grid-item-card} Developer Guide
:link: developer/architecture
:link-type: doc

Understand the architecture and contribute
:::

:::{grid-item-card} API Reference
:link: api/reference
:link-type: doc

Complete API documentation
:::
::::

## Table of Contents

```{toctree}
:maxdepth: 2
:caption: User Guide

user/installation
user/quickstart
user/guide
user/dashboard
user/circles
user/agents
user/workspace
user/faq
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

developer/architecture
developer/contributing
developer/database
developer/api
developer/websocket
developer/testing
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/reference
api/endpoints
api/models
```

## Project Status

- **Version**: 1.0.0
- **License**: MIT
- **Python**: 3.11+
- **Repository**: [GitHub](https://github.com/alkimya/gathering)

## Features

### Agents & Circles

Create AI agents with unique personalities that collaborate in thematic circles:

```python
from gathering import Agent, Circle

# Create agents with different providers
sophie = Agent(
    name="Sophie",
    role="architect",
    provider="anthropic",
    model="claude-sonnet-4-20250514"
)
olivia = Agent(
    name="Olivia",
    role="engineer",
    provider="openai",
    model="gpt-4o"
)

# Create a circle
circle = Circle(name="Development Team")
circle.add_agents([sophie, olivia])

# Start a conversation
await circle.discuss("Design the new authentication system")
```

### Integrated Workspace

The workspace provides a complete development environment:

- **File Explorer**: Navigate and manage project files
- **Code Editor**: Monaco-based editor with syntax highlighting and LSP support
- **Terminal**: Integrated terminal for command execution
- **Git Integration**: Visual git operations (status, diff, commit, push)
- **Media Viewers**: Support for images, audio, video, and PDF files

### Real-time Dashboard

Monitor and manage your agents through a modern React dashboard:

- Live conversation streaming
- Agent status and activity
- Circle management
- Task tracking and calendar

## Getting Help

- Check the [FAQ](user/faq.md) for common questions
- Report issues on [GitHub Issues](https://github.com/alkimya/gathering/issues)
- Join our community discussions

---
