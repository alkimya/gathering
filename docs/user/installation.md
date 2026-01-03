# Installation

This guide covers how to install GatheRing on your system.

## Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.11 or higher |
| Node.js | 18 or higher (for dashboard) |
| PostgreSQL | 15 or higher (with pgvector) |
| Redis | 7 or higher (optional, for caching) |
| Memory | 4GB minimum, 8GB recommended |

## Quick Install

### 1. Clone the Repository

```bash
git clone https://github.com/alkimya/gathering.git
cd gathering
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

### 4. Install Dashboard Dependencies

```bash
cd dashboard
npm install
cd ..
```

### 5. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gathering

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Server
API_HOST=0.0.0.0
API_PORT=8000

# Authentication (required for production)
SECRET_KEY=your-secret-key-min-32-characters
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=$2b$12$...  # Generate with: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
```

### 6. Setup Database

Create the database and run migrations:

```bash
# Create database
createdb gathering

# Enable pgvector extension
psql -d gathering -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
python -m gathering.db.migrate
```

### 7. Start the Application

Using the start script:

```bash
./scripts/start-workspace.sh
```

Or manually:

```bash
# Terminal 1: Start API
uvicorn gathering.api:app --reload --port 8000

# Terminal 2: Start Dashboard
cd dashboard && npm run dev
```

## Docker Installation

```bash
# Build and run with docker-compose
docker-compose up -d
```

This starts:
- PostgreSQL with pgvector
- Redis
- GatheRing API
- Dashboard

## Verifying Installation

1. Open http://localhost:8000/docs for API documentation
2. Open http://localhost:3000 for the dashboard
3. Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Or run tests:

```bash
pytest tests/
```

## Troubleshooting

### PostgreSQL Connection Issues

Ensure PostgreSQL is running:

```bash
sudo systemctl status postgresql
```

### pgvector Extension Not Found

Install pgvector:

```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# macOS with Homebrew
brew install pgvector
```

### Node.js Version Issues

Use nvm to manage Node versions:

```bash
nvm install 18
nvm use 18
```

## Next Steps

- Read the [Quickstart Guide](quickstart.md) to create your first circle
- Explore the [User Guide](guide.md) for detailed usage
- Check [FAQ](faq.md) for common questions
