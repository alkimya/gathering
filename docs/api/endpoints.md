# API Endpoints

Complete reference for all GatheRing REST API endpoints.

Base URL: `http://localhost:8000`

## Health & Status

### GET /health

Check API health status with system overview.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "agents_count": 5,
  "circles_count": 2,
  "active_tasks": 3
}
```

### GET /health/system

Get real-time system metrics (CPU, memory, disk, load average).

**Response:**

```json
{
  "cpu": {
    "percent": 25.5,
    "count": 8,
    "frequency_mhz": 3200.0
  },
  "memory": {
    "total_gb": 32.0,
    "available_gb": 18.5,
    "used_gb": 13.5,
    "percent": 42.2
  },
  "disk": {
    "total_gb": 500.0,
    "used_gb": 250.0,
    "free_gb": 250.0,
    "percent": 50.0
  },
  "load_average": {
    "1min": 1.5,
    "5min": 1.2,
    "15min": 0.9
  },
  "uptime_seconds": 3600.5
}
```

### GET /health/checks

Get detailed health checks for all services.

**Response:**

```json
{
  "checks": [
    {
      "name": "API Server",
      "status": "healthy",
      "message": "Responding normally",
      "last_check": "2025-01-01T12:00:00Z"
    },
    {
      "name": "Database",
      "status": "healthy",
      "message": "PostgreSQL connected",
      "last_check": "2025-01-01T12:00:00Z"
    },
    {
      "name": "Memory Usage",
      "status": "healthy",
      "value": "42.2%",
      "message": "Normal",
      "last_check": "2025-01-01T12:00:00Z"
    },
    {
      "name": "Disk Space",
      "status": "healthy",
      "value": "50.0%",
      "message": "Sufficient space",
      "last_check": "2025-01-01T12:00:00Z"
    },
    {
      "name": "Agents",
      "status": "healthy",
      "value": "5",
      "message": "5 agent(s) registered",
      "last_check": "2025-01-01T12:00:00Z"
    },
    {
      "name": "Circles",
      "status": "healthy",
      "value": "1/2",
      "message": "1 running, 2 total",
      "last_check": "2025-01-01T12:00:00Z"
    }
  ],
  "overall_status": "healthy"
}
```

**Status Values:**

- `healthy`: Service operating normally
- `warning`: Service degraded (memory >70%, disk >80%)
- `critical`: Service critical (memory >90%, disk >90%, connection failed)

### GET /health/ready

Kubernetes readiness probe. Returns 503 during graceful shutdown to allow load balancers to drain connections.

**Response (healthy):**

```json
{
  "ready": true
}
```

**Response (shutting down):** `503 Service Unavailable`

```json
{
  "ready": false,
  "reason": "shutting_down"
}
```

### GET /health/live

Kubernetes liveness probe.

**Response:**

```json
{
  "alive": true
}
```

## Agents

### GET /agents

List all agents.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | - | Filter by status |
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

**Response:**

```json
[
  {
    "id": 1,
    "name": "Sophie",
    "role": "Architect",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "status": "idle",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

### POST /agents

Create a new agent.

**Request Body:**

```json
{
  "name": "Sophie",
  "role": "Lead Architect",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "personality": {
    "traits": ["analytical", "creative"],
    "communication_style": "professional"
  },
  "config": {
    "temperature": 0.7
  }
}
```

**Response:** `201 Created`

```json
{
  "id": 1,
  "name": "Sophie",
  "role": "Lead Architect",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "status": "idle",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### GET /agents/{id}

Get agent by ID.

**Response:**

```json
{
  "id": 1,
  "name": "Sophie",
  "role": "Lead Architect",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "personality": {...},
  "config": {...},
  "status": "idle",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### PATCH /agents/{id}

Update an agent.

**Request Body:**

```json
{
  "role": "Senior Architect",
  "config": {
    "temperature": 0.8
  }
}
```

### DELETE /agents/{id}

Delete an agent.

**Response:** `204 No Content`

### GET /agents/{id}/sessions

Get agent sessions.

### POST /agents/{id}/sessions

Start a new session.

### GET /agents/{id}/memories

Get agent memories.

## Circles

### GET /circles

List all circles.

**Response:**

```json
[
  {
    "id": 1,
    "name": "dev-team",
    "display_name": "Development Team",
    "status": "active",
    "agent_count": 3
  }
]
```

### POST /circles

Create a new circle.

**Request Body:**

```json
{
  "name": "dev-team",
  "display_name": "Development Team",
  "description": "Frontend and backend developers",
  "config": {
    "max_agents": 10,
    "conversation_mode": "round_robin"
  }
}
```

### GET /circles/{name}

Get circle by name.

### PATCH /circles/{name}

Update a circle.

### DELETE /circles/{name}

Delete a circle.

### POST /circles/{name}/start

Start a circle.

### POST /circles/{name}/pause

Pause a circle.

### POST /circles/{name}/resume

Resume a paused circle.

### POST /circles/{name}/archive

Archive a circle.

### GET /circles/{name}/agents

List agents in a circle.

### POST /circles/{name}/agents

Add agent to circle.

**Request Body:**

```json
{
  "agent_id": 1,
  "role": "member"
}
```

### DELETE /circles/{name}/agents/{agent_id}

Remove agent from circle.

## Conversations

### GET /conversations

List conversations.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `circle_name` | string | Filter by circle |
| `status` | string | Filter by status |
| `limit` | int | Max results |

### POST /conversations

Create a new conversation.

**Request Body:**

```json
{
  "circle_name": "dev-team",
  "topic": "API Design Review",
  "agent_ids": [1, 2, 3],
  "initial_prompt": "Let's review the new API design",
  "max_turns": 20
}
```

### GET /conversations/{id}

Get conversation details.

### GET /conversations/{id}/messages

Get conversation messages.

### POST /conversations/{id}/advance

Advance the conversation.

**Request Body:**

```json
{
  "prompt": "What about error handling?"
}
```

### POST /conversations/{id}/end

End the conversation.

## Workspace

### GET /workspace/{id}/info

Get workspace information.

**Response:**

```json
{
  "id": 1,
  "path": "/home/user/project",
  "name": "my-project",
  "git_enabled": true,
  "current_branch": "main"
}
```

### GET /workspace/{id}/files

List files in workspace.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Directory path |
| `recursive` | bool | Include subdirectories |

### GET /workspace/{id}/files/{path}

Read file content.

**Response:**

```json
{
  "path": "src/main.py",
  "content": "print('hello')",
  "language": "python",
  "size": 15
}
```

### PUT /workspace/{id}/files/{path}

Write file content.

**Request Body:**

```json
{
  "content": "print('updated')"
}
```

### DELETE /workspace/{id}/files/{path}

Delete a file.

### POST /workspace/{id}/files/{path}/rename

Rename a file.

**Request Body:**

```json
{
  "new_path": "src/app.py"
}
```

### GET /workspace/{id}/git/status

Get git status.

**Response:**

```json
{
  "branch": "main",
  "ahead": 2,
  "behind": 0,
  "staged": ["src/main.py"],
  "modified": ["README.md"],
  "untracked": ["new_file.py"]
}
```

### GET /workspace/{id}/git/commits

Get commit history.

**Query Parameters:**

| Parameter | Type | Default |
|-----------|------|---------|
| `limit` | int | 20 |
| `branch` | string | current |

### POST /workspace/{id}/git/stage

Stage files.

**Request Body:**

```json
{
  "files": ["src/main.py", "README.md"]
}
```

### POST /workspace/{id}/git/unstage

Unstage files.

### POST /workspace/{id}/git/commit

Create a commit.

**Request Body:**

```json
{
  "message": "Add new feature"
}
```

### POST /workspace/{id}/git/push

Push to remote.

### POST /workspace/{id}/git/pull

Pull from remote.

### GET /workspace/{id}/git/diff

Get file diff.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | string | File path |
| `staged` | bool | Staged diff |

## Memory

### GET /memory/search

Semantic memory search.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Search query |
| `agent_id` | int | Filter by agent |
| `scope` | string | Memory scope |
| `limit` | int | Max results |

**Response:**

```json
[
  {
    "id": 1,
    "key": "user_name",
    "value": "Alice",
    "similarity": 0.92,
    "scope": "agent"
  }
]
```

### POST /memory

Create a memory.

**Request Body:**

```json
{
  "agent_id": 1,
  "scope": "agent",
  "key": "preference",
  "value": "Likes detailed explanations",
  "memory_type": "fact"
}
```

### DELETE /memory/{id}

Delete a memory.

## Dashboard

### GET /dashboard/circles

Get dashboard circle summary.

### GET /dashboard/agents

Get dashboard agent summary.

### GET /dashboard/activity

Get recent activity feed.

### GET /dashboard/stats

Get system statistics.

## Settings

### GET /settings

Get all application settings including LLM providers, database, and application configuration.

**Response:**

```json
{
  "providers": {
    "anthropic": {
      "api_key": "sk-a...xyz",
      "default_model": "claude-sonnet-4-5",
      "is_configured": true,
      "models": [
        {
          "id": 1,
          "model_name": "claude-sonnet-4-20250514",
          "model_alias": "claude-4-sonnet",
          "vision": true,
          "extended_thinking": false
        }
      ]
    },
    "openai": {
      "api_key": null,
      "default_model": "gpt-4",
      "is_configured": false,
      "models": []
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "default_model": "llama3.2",
      "is_configured": true,
      "models": []
    }
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "gathering",
    "user": "gathering",
    "is_connected": true
  },
  "application": {
    "environment": "development",
    "debug": true,
    "log_level": "INFO"
  }
}
```

**Supported Providers:**

- `anthropic`: Anthropic Claude models
- `openai`: OpenAI GPT models
- `deepseek`: DeepSeek models
- `mistral`: Mistral AI models
- `google`: Google Gemini models
- `ollama`: Local Ollama models

### PATCH /settings/providers/{provider}

Update a provider's settings.

**Path Parameters:**

| Parameter  | Type   | Description                              |
|------------|--------|------------------------------------------|
| `provider` | string | Provider name (anthropic, openai, etc.) |

**Request Body:**

```json
{
  "api_key": "sk-new-key...",
  "default_model": "claude-sonnet-4-5",
  "base_url": "http://localhost:11434"
}
```

**Response:**

```json
{
  "api_key": "sk-n...key",
  "default_model": "claude-sonnet-4-5",
  "is_configured": true,
  "models": []
}
```

### PATCH /settings/application

Update application settings.

**Request Body:**

```json
{
  "debug": false,
  "log_level": "WARNING"
}
```

**Valid log levels:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Response:**

```json
{
  "environment": "development",
  "debug": false,
  "log_level": "WARNING"
}
```

### POST /settings/providers/{provider}/test

Test connection to a provider.

**Response (success):**

```json
{
  "success": true,
  "message": "Anthropic API key is valid"
}
```

**Response (failure):**

```json
{
  "success": false,
  "message": "Invalid API key"
}
```

**Ollama response:**

```json
{
  "success": true,
  "message": "Connected to Ollama. 5 models available.",
  "models": ["llama3.2", "codellama", "mistral"]
}
```

## Tools (Agent Capabilities)

Manage which skills/tools are enabled for each agent.

### GET /tools/skills

List all available skills.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category |

**Response:**

```json
[
  {
    "id": 1,
    "name": "git",
    "display_name": "Git",
    "description": "Repository management, commits, branches, PRs",
    "category": "core",
    "required_permissions": ["git", "read", "write"],
    "is_dangerous": false,
    "is_enabled": true,
    "version": "1.0.0",
    "tools_count": 5
  }
]
```

**Skill Categories:**

- `core`: Git, Test, Filesystem
- `code`: Code Execution, Analysis
- `system`: Shell, Database, Deploy
- `web`: Web Search, Scraper, HTTP
- `ai`: AI/ML operations
- `communication`: Email, Notifications, Social
- `productivity`: Calendar, Docs
- `media`: Image, PDF
- `cloud`: Cloud providers, Monitoring
- `gathering`: Goals, Pipelines, Tasks, Schedules

### GET /tools/skills/categories

Get skill categories with counts.

**Response:**

```json
{
  "core": 5,
  "code": 2,
  "system": 3,
  "web": 3,
  "gathering": 6
}
```

### GET /tools/agents/{agent_id}

Get all tools for an agent with enabled/disabled status.

**Response:**

```json
{
  "agent_id": 1,
  "agent_name": "Sophie",
  "tools": [
    {
      "skill_id": 1,
      "skill_name": "git",
      "skill_display_name": "Git",
      "skill_category": "core",
      "required_permissions": ["git", "read", "write"],
      "is_dangerous": false,
      "is_enabled": true,
      "usage_count": 42,
      "last_used_at": "2025-01-01T12:00:00Z"
    }
  ],
  "enabled_count": 12,
  "total_count": 24
}
```

### PATCH /tools/agents/{agent_id}/skills/{skill_name}

Enable or disable a tool for an agent.

**Request Body:**

```json
{
  "is_enabled": true
}
```

**Response:**

```json
{
  "agent_id": 1,
  "skill_name": "git",
  "is_enabled": true,
  "message": "Tool 'git' enabled for agent 1"
}
```

### POST /tools/agents/{agent_id}/skills/bulk

Bulk enable/disable multiple tools.

**Request Body:**

```json
{
  "skill_names": ["git", "test", "shell"],
  "is_enabled": true
}
```

**Response:**

```json
{
  "agent_id": 1,
  "updated_count": 3,
  "is_enabled": true,
  "message": "3 tools enabled"
}
```

### POST /tools/agents/{agent_id}/skills/enable-all

Enable all tools for an agent.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Only enable tools in this category |

**Response:**

```json
{
  "agent_id": 1,
  "enabled_count": 24,
  "category": null,
  "message": "Enabled 24 tools"
}
```

### POST /tools/agents/{agent_id}/skills/disable-all

Disable all tools for an agent.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Only disable tools in this category |

### GET /tools/agents/{agent_id}/enabled

Get list of enabled skill names for an agent.

**Response:**

```json
{
  "agent_id": 1,
  "enabled_skills": ["git", "test", "filesystem", "code"]
}
```

## Rate Limiting

All endpoints enforce per-endpoint rate limits via slowapi. Rate limit tiers:

| Tier | Limit | Endpoints |
|------|-------|-----------|
| `strict` | 10/minute | `/auth/login`, `/auth/register` |
| `standard` | 60/minute | Most CRUD endpoints |
| `relaxed` | 200/minute | Read-heavy endpoints (`GET /agents`, `GET /circles`) |
| `bulk` | 30/minute | Bulk operations, imports |

When rate limited, the response includes:

```text
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1707616800
```

## Error Responses

All endpoints may return:

### 400 Bad Request

```json
{
  "detail": "Invalid request body"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```
