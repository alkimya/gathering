# Phase 3: Toggle Demo/Database pour Dashboard

## Résumé

Cette phase ajoute un système de toggle `USE_DEMO_DATA` qui permet de basculer entre données démo et données réelles PostgreSQL pour le dashboard. Cela préserve les données de développement tout en permettant la connexion à la base de données.

## Changements Réalisés

### 1. Variable d'Environnement `.env`

```bash
# Data Source Toggle
USE_DEMO_DATA=true   # Utilise données démo (défaut)
USE_DEMO_DATA=false  # Utilise PostgreSQL
```

### 2. DataService (`gathering/api/dependencies.py`)

Service centralisé qui gère la source de données:

```python
from gathering.api.dependencies import get_data_service, use_demo_data

# Vérifier le mode
if use_demo_data():
    print("Mode démo actif")

# Utiliser le service
data = get_data_service()
agents = data.get_agents()      # Retourne démo ou DB selon le mode
providers = data.get_providers()
models = data.get_models()
```

**Méthodes disponibles:**
- `get_agents()` / `get_agent(id)`
- `get_providers()` / `get_provider(id)`
- `get_models(provider_id?)` / `get_model(id)`
- `is_demo_mode` (property)

### 3. Endpoints Dashboard (`/dashboard/*`)

Nouveaux endpoints dédiés au dashboard web:

| Endpoint | Description |
|----------|-------------|
| `GET /dashboard/config` | Configuration (mode, version, features) |
| `GET /dashboard/agents` | Liste des agents |
| `GET /dashboard/agents/{id}` | Détails d'un agent |
| `GET /dashboard/providers` | Liste des providers LLM |
| `GET /dashboard/providers/{id}` | Détails d'un provider |
| `GET /dashboard/models` | Liste des modèles |
| `GET /dashboard/models/{id}` | Détails d'un modèle |
| `GET /dashboard/stats` | Statistiques agrégées |

Chaque réponse inclut `demo_mode: true/false` pour que le frontend sache d'où viennent les données.

### 4. Données Démo

3 agents de démo:
- **Dr. Sophie Chen** - Lead AI Researcher (Anthropic)
- **Olivia Nakamoto** - Full-Stack Developer (Anthropic)
- **Marcus Webb** - DevOps Engineer (OpenAI)

4 providers démo:
- Anthropic, OpenAI, DeepSeek, Ollama

5 modèles démo:
- claude-sonnet-4, claude-opus-4, gpt-4, gpt-4-turbo, deepseek-coder

### 5. Tests (`tests/test_dashboard.py`)

23 nouveaux tests:
- Tests du toggle `USE_DEMO_DATA`
- Tests du DataService en mode démo
- Tests du DataService en mode DB (mocked)
- Tests de la structure des données démo

## Usage

### Mode Démo (développement dashboard)

```bash
# .env
USE_DEMO_DATA=true

# Lancer l'API
uvicorn gathering.api:app --reload

# Tester
curl http://localhost:8000/dashboard/agents
# → Retourne les 3 agents démo
```

### Mode Database (production)

```bash
# .env
USE_DEMO_DATA=false
DATABASE_URL=postgresql://...

# Lancer l'API
uvicorn gathering.api:app --reload

# Tester
curl http://localhost:8000/dashboard/agents
# → Retourne les agents depuis PostgreSQL
```

### Exemple de Réponse

```json
{
  "agents": [
    {
      "id": 1,
      "name": "Dr. Sophie Chen",
      "role": "Lead AI Researcher",
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514",
      "status": "idle",
      "competencies": ["research", "analysis", "python"],
      "tasks_completed": 47,
      "is_active": true
    }
  ],
  "total": 3,
  "demo_mode": true
}
```

## Résultats

- **589 tests passent** (23 nouveaux)
- **Couverture: 79.90%**
- **Toggle fonctionnel** entre démo et DB
- **Dashboard préservé** avec données de développement

## Prochaines Étapes

1. **Phase 4: Multi-agents** - Collaboration entre agents
2. **Dashboard Frontend** - Connecter le frontend aux endpoints `/dashboard/*`
3. **WebSocket** - Mises à jour temps réel pour le dashboard
