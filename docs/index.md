# GatheRing Documentation

**GatheRing** is a collaborative multi-agent AI framework that enables autonomous AI agents to work together in circles, share knowledge, and accomplish complex tasks.

## Overview

GatheRing provides:

- **Multi-Agent Collaboration**: AI agents with distinct personalities working together in circles
- **Persistent Memory**: Long-term memory with RAG (Retrieval-Augmented Generation)
- **Real-time Communication**: WebSocket-based streaming and event bus
- **Integrated Workspace**: Full-featured IDE with file explorer, code editor, terminal
- **Dashboard**: React-based monitoring and management interface

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

- **Version**: 0.5.0
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
