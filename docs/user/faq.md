# Frequently Asked Questions

## General

### What is GatheRing?

GatheRing is a collaborative multi-agent AI framework that enables autonomous AI agents to work together in circles, share knowledge, and accomplish complex tasks.

### What can I do with GatheRing?

- Create AI agents with unique personalities
- Organize agents into collaborative circles
- Run multi-agent conversations
- Manage projects through an integrated workspace
- Build AI-powered development teams

### What AI models are supported?

GatheRing supports Claude models from Anthropic:

- **Opus**: Most capable, best for complex reasoning
- **Sonnet**: Balanced performance and speed
- **Haiku**: Fastest, best for simple tasks

### Is GatheRing free?

GatheRing is open source. However, you'll need API keys for the AI providers (Anthropic, OpenAI) which have their own pricing.

## Installation

### What are the system requirements?

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector
- 4GB RAM minimum, 8GB recommended

### How do I install pgvector?

```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# macOS
brew install pgvector

# From source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make && sudo make install
```

### Why am I getting database connection errors?

1. Ensure PostgreSQL is running: `sudo systemctl status postgresql`
2. Check your `DATABASE_URL` in `.env`
3. Verify the database exists: `psql -l`
4. Run migrations: `python -m gathering.db.migrate`

### The dashboard won't start. What should I do?

1. Check Node.js version: `node --version` (should be 18+)
2. Install dependencies: `cd dashboard && npm install`
3. Check for port conflicts: `lsof -i :3000`
4. View logs: `npm run dev` without background

## Agents

### How many agents can I create?

There's no hard limit. However, for best performance:

- Keep circles to 3-7 agents
- Use appropriate models for each agent
- Consider API rate limits

### Can agents learn over time?

Yes! Agents have persistent memory:

- **Short-term**: Conversation context
- **Long-term**: Stored memories and learnings
- **Shared**: Circle-level knowledge base

### How do I customize agent personalities?

Use personality traits and communication styles:

```json
{
  "personality": {
    "traits": ["analytical", "creative"],
    "communication_style": "professional"
  }
}
```

### Can agents use external tools?

Yes, agents can use:

- Filesystem (read/write files)
- Calculator (math operations)
- Code executor (run code)
- Git (version control)
- Web search (internet access)

## Circles

### What's the difference between a circle and a conversation?

- **Circle**: A persistent group of agents (like a team)
- **Conversation**: A specific discussion within a circle (like a meeting)

### Can an agent be in multiple circles?

Yes, agents can belong to multiple circles simultaneously.

### How do I archive a circle?

```bash
curl -X POST http://localhost:8000/circles/my-circle/archive
```

Archived circles are read-only but preserved for reference.

## Workspace

### Why isn't syntax highlighting working?

1. Check file extension matches the language
2. Ensure LSP server is running
3. Try refreshing the page

### How do I enable LSP for Python?

LSP should work automatically. If not:

```bash
pip install python-lsp-server pyright
```

### Can I use the workspace without the dashboard?

Yes, all workspace features are available via API:

```bash
# List files
curl http://localhost:8000/workspace/1/files

# Read file
curl http://localhost:8000/workspace/1/files/src/main.py
```

### How do I fix terminal issues?

1. Clear terminal: type `clear` or `Ctrl+L`
2. Reset terminal: close and reopen the panel
3. Check for zombie processes: `ps aux | grep bash`

## API

### How do I authenticate API requests?

Currently, GatheRing uses API keys in the `.env` file for AI providers. The internal API doesn't require authentication by default (configure in production).

### What's the rate limit?

GatheRing doesn't impose its own rate limits, but AI providers do:

- Anthropic: Varies by plan
- OpenAI: Varies by plan

### How do I stream responses?

Use WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/circles/my-circle');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## Performance

### How do I improve response times?

1. Use Haiku for simple tasks
2. Reduce conversation history length
3. Enable Redis caching
4. Use connection pooling for database

### Why is memory usage high?

1. Clear old conversation histories
2. Reduce the number of active agents
3. Use memory compaction
4. Monitor with: `curl http://localhost:8000/health`

### How do I scale GatheRing?

- Use Redis for distributed caching
- Deploy multiple API instances
- Use a load balancer
- Consider Kubernetes for orchestration

## Troubleshooting

### Agents aren't responding

1. Check API keys in `.env`
2. Verify agent is active: `curl http://localhost:8000/agents/1`
3. Check logs: `tail -f /tmp/gathering-api.log`

### WebSocket connection fails

1. Check API is running: `curl http://localhost:8000/health`
2. Verify WebSocket URL format
3. Check browser console for errors

### Database migrations fail

1. Ensure PostgreSQL is running
2. Check database permissions
3. Try manual migration:
   ```bash
   psql -d gathering -f gathering/db/migrations/001_initial.sql
   ```

### File uploads don't work

1. Check file size limits
2. Verify write permissions
3. Check disk space: `df -h`

## Getting Help

### Where can I report bugs?

Open an issue on GitHub: <https://github.com/alkimya/gathering/issues>

### Is there a community?

- GitHub Discussions
- Discord server (coming soon)

### How can I contribute?

See the [Contributing Guide](../developer/contributing.md) for details on:

- Code contributions
- Documentation
- Bug reports
- Feature requests
