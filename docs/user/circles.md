# Circles

Circles are the core organizational unit in GatheRing. They represent groups of AI agents that collaborate on a common theme, project, or domain.

## What is a Circle?

A **Circle** is:

- A container for related agents
- A context for conversations
- A scope for shared memory and knowledge
- A boundary for permissions and access

Think of a circle as a team room where agents meet to discuss and work together.

## Circle Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Created   │────▶│   Active    │────▶│   Archived  │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   Paused    │
                    └─────────────┘
```

### States

- **Created**: Circle exists but hasn't started
- **Active**: Circle is running, agents can converse
- **Paused**: Temporarily stopped, can be resumed
- **Archived**: Permanently stopped, read-only

## Creating Circles

### Via API

```bash
curl -X POST http://localhost:8000/circles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dev-team",
    "display_name": "Development Team",
    "description": "Frontend and backend developers",
    "config": {
      "max_agents": 10,
      "conversation_mode": "round_robin"
    }
  }'
```

### Via Python

```python
from gathering import Circle

circle = Circle(
    name="dev-team",
    display_name="Development Team",
    description="Frontend and backend developers",
    config={
        "max_agents": 10,
        "conversation_mode": "round_robin"
    }
)
await circle.save()
```

## Managing Agents in Circles

### Adding Agents

```bash
# Add an agent to a circle
curl -X POST http://localhost:8000/circles/dev-team/agents \
  -H "Content-Type: application/json" \
  -d '{"agent_id": 1}'
```

### Removing Agents

```bash
curl -X DELETE http://localhost:8000/circles/dev-team/agents/1
```

### Listing Circle Agents

```bash
curl http://localhost:8000/circles/dev-team/agents
```

## Circle Configuration

### Conversation Modes

| Mode | Description |
|------|-------------|
| `round_robin` | Agents take turns in order |
| `reactive` | Agents respond when relevant |
| `moderated` | A lead agent directs conversation |
| `free_form` | Any agent can speak anytime |

### Example Configuration

```json
{
  "name": "research-team",
  "config": {
    "max_agents": 5,
    "conversation_mode": "moderated",
    "moderator_agent_id": 1,
    "turn_timeout": 30,
    "max_turns_per_conversation": 50,
    "memory_scope": "circle",
    "allow_tools": true
  }
}
```

## Circle Operations

### Start a Circle

```bash
curl -X POST http://localhost:8000/circles/dev-team/start
```

### Pause a Circle

```bash
curl -X POST http://localhost:8000/circles/dev-team/pause
```

### Resume a Circle

```bash
curl -X POST http://localhost:8000/circles/dev-team/resume
```

### Archive a Circle

```bash
curl -X POST http://localhost:8000/circles/dev-team/archive
```

## Conversations in Circles

Conversations happen within circles:

```bash
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "circle_name": "dev-team",
    "topic": "API Design Review",
    "agent_ids": [1, 2, 3],
    "initial_prompt": "Let'\''s review the new REST API design"
  }'
```

### Advancing Conversations

```bash
curl -X POST http://localhost:8000/conversations/1/advance \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What about error handling?"}'
```

## Circle Memory

Each circle has its own memory scope:

- **Circle-scoped memories**: Shared by all agents in the circle
- **Agent-scoped memories**: Private to each agent
- **Conversation memories**: Specific to each conversation

### Accessing Circle Memory

```bash
# Get circle knowledge
curl http://localhost:8000/circles/dev-team/knowledge

# Add knowledge to circle
curl -X POST http://localhost:8000/circles/dev-team/knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Standards",
    "content": "All APIs must follow REST conventions...",
    "category": "best_practice"
  }'
```

## Best Practices

### 1. Name Circles Meaningfully

Use descriptive names that reflect the circle's purpose:

- `dev-team` - Development team
- `security-review` - Security reviewers
- `customer-support` - Support agents

### 2. Limit Circle Size

Keep circles focused with 3-7 agents for best results.

### 3. Define Clear Roles

Each agent in a circle should have a distinct role:

```python
circle.add_agent(architect, role="lead")
circle.add_agent(developer, role="implementer")
circle.add_agent(reviewer, role="quality")
```

### 4. Use Appropriate Conversation Modes

- **Brainstorming**: Use `free_form`
- **Technical review**: Use `moderated`
- **Pair work**: Use `round_robin`

## Related Topics

- [Agents](agents.md) - Creating and configuring agents
- [Workspace](workspace.md) - Using the integrated workspace
- [API Reference](../api/reference.md) - Complete API documentation
