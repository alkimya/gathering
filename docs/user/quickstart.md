# Quickstart

Get up and running with GatheRing in 5 minutes.

## Prerequisites

Make sure you have completed the [Installation](installation.md) steps.

## Your First Circle

### 1. Start the Services

```bash
./scripts/start-workspace.sh
```

### 2. Open the Dashboard

Navigate to <http://localhost:3000> in your browser.

### 3. Create Your First Circle

A **Circle** is a group of AI agents working together on a common theme or project.

Using the API:

```bash
curl -X POST http://localhost:8000/circles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dev-team",
    "display_name": "Development Team",
    "description": "A team of AI developers"
  }'
```

Or via Python:

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/circles",
        json={
            "name": "dev-team",
            "display_name": "Development Team",
            "description": "A team of AI developers"
        }
    )
    circle = response.json()
    print(f"Created circle: {circle['id']}")
```

### 4. Add Agents to the Circle

Create agents with distinct personalities:

```bash
# Create an architect agent
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sophie",
    "role": "Lead Architect",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "personality": {
      "traits": ["analytical", "creative", "detail-oriented"],
      "communication_style": "professional"
    }
  }'

# Create an engineer agent (using OpenAI)
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Olivia",
    "role": "Senior Engineer",
    "provider": "openai",
    "model": "gpt-4o",
    "personality": {
      "traits": ["pragmatic", "efficient", "collaborative"],
      "communication_style": "direct"
    }
  }'
```

### 5. Start a Conversation

Start the circle and create a conversation:

```bash
# Start the circle
curl -X POST http://localhost:8000/circles/dev-team/start

# Create a conversation
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "circle_name": "dev-team",
    "topic": "Design the authentication system",
    "agent_ids": [1, 2],
    "initial_prompt": "Let'\''s discuss how to implement secure authentication"
  }'
```

### 6. Watch the Conversation

Open the dashboard to see agents collaborating in real-time, or stream via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/circles/dev-team');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(`${message.agent}: ${message.content}`);
};
```

## Using the Workspace

The workspace provides a complete development environment.

### Access the Workspace

Navigate to <http://localhost:3000/workspace/1>

### Features

- **File Explorer**: Browse and manage project files
- **Code Editor**: Edit files with syntax highlighting
- **Terminal**: Run commands directly
- **Git Panel**: View status, stage, commit, and push

## What's Next?

- Learn about [Circles](circles.md) in depth
- Understand [Agent personalities](agents.md)
- Explore the [Workspace](workspace.md) features
- Read the full [User Guide](guide.md)
