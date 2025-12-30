# Phase 4: Multi-Agents - Collaboration et Mémoire Partagée

## Résumé

Cette phase ajoute la persistance PostgreSQL pour les circles (équipes d'agents) et implémente la mémoire partagée au niveau circle, permettant aux agents de collaborer et partager leurs connaissances.

## Changements Réalisés

### 1. CircleStore - Persistance PostgreSQL (`gathering/orchestration/circle_store.py`)

Service de persistance pour les Gathering Circles, utilisant picopg.

```python
from gathering.orchestration.circle_store import CircleStore

store = CircleStore.from_env()

# Créer un circle
circle_id = store.create_circle(
    name="dev-team",
    display_name="Development Team",
    description="Équipe multi-agents",
    auto_route=True,
    require_review=True,
)

# Ajouter des membres
store.add_member(
    circle_id=circle_id,
    agent_id=1,
    role='lead',
    competencies=['python', 'architecture'],
    can_review=['code', 'docs'],
)

# Créer une tâche
task_id = store.create_task(
    circle_id=circle_id,
    title="Implémenter feature X",
    required_competencies=['python'],
    priority='high',
)

# Démarrer le circle
store.update_circle_status(circle_id, 'running')

# Logger un événement
store.log_event(
    circle_id=circle_id,
    event_type='task_started',
    data={'task_id': task_id},
)
```

**Opérations supportées:**
- **Circles**: create, get, list, update_status, delete
- **Membres**: add_member, remove_member, list_members
- **Tâches**: create_task, get_task, list_tasks, update_task_status
- **Événements**: log_event, get_events

**Tables PostgreSQL utilisées:**
- `circle.circles` - Circles avec configuration
- `circle.members` - Association agents ↔ circles
- `circle.tasks` - Tâches assignées dans le circle
- `circle.events` - Événements du circle

### 2. Mémoire Partagée au Niveau Circle

Extension du système de mémoire pour supporter le partage au scope `circle`.

#### VectorStore - Ajout du paramètre `scope_id`

```python
# Avant
store.add_memory(
    agent_id=1,
    key="decision",
    value="On utilise PostgreSQL",
    embedding=embedding,
    scope="agent",  # scope_id fixé à agent_id
)

# Après
store.add_memory(
    agent_id=1,
    key="decision",
    value="On utilise PostgreSQL",
    embedding=embedding,
    scope="circle",
    scope_id=circle_id,  # Mémoire partagée dans le circle
)
```

#### MemoryManager - Support scope/scope_id

```python
from gathering.rag.memory_manager import MemoryManager

memory = MemoryManager.from_env()

# Stocker une mémoire au scope circle
memory_id = await memory.remember(
    agent_id=1,
    content="Décision: Utiliser PostgreSQL + pgvector",
    memory_type="decision",
    scope="circle",
    scope_id=circle_id,
    importance=0.9,
)

# Tous les agents du circle peuvent trouver cette mémoire
results = await memory.recall(
    agent_id=2,  # Autre agent du circle
    query="Quelle base de données ?",
)
```

**Scopes disponibles:**
- `agent` - Mémoire privée de l'agent (défaut)
- `circle` - Partagée entre les membres du circle
- `project` - Partagée au niveau projet
- `global` - Accessible à tous

### 3. Modifications des Fichiers

| Fichier | Changement |
|---------|-----------|
| [vectorstore.py](gathering/rag/vectorstore.py#L131-L184) | Ajout `scope_id` param à `add_memory()` |
| [memory_manager.py](gathering/rag/memory_manager.py#L105-L160) | Ajout `scope`, `scope_id` params à `remember()` |
| [circle_store.py](gathering/orchestration/circle_store.py) | **Nouveau** - Service persistance circles |

## Schéma Base de Données

### circle.circles

```sql
CREATE TABLE circle.circles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    display_name VARCHAR,
    description TEXT,
    auto_route BOOLEAN DEFAULT true,
    require_review BOOLEAN DEFAULT true,
    status circle_status DEFAULT 'stopped',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### circle.members

```sql
CREATE TABLE circle.members (
    id BIGSERIAL PRIMARY KEY,
    circle_id BIGINT REFERENCES circle.circles(id),
    agent_id BIGINT REFERENCES agent.agents(id),
    role agent_role,  -- lead, member, specialist, reviewer, observer
    competencies TEXT[],
    can_review TEXT[],
    is_active BOOLEAN DEFAULT true,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(circle_id, agent_id)
);
```

### circle.tasks

```sql
CREATE TABLE circle.tasks (
    id BIGSERIAL PRIMARY KEY,
    circle_id BIGINT REFERENCES circle.circles(id),
    title VARCHAR NOT NULL,
    description TEXT,
    status task_status DEFAULT 'pending',
    priority task_priority DEFAULT 'medium',
    required_competencies TEXT[],
    assigned_agent_id BIGINT,
    result TEXT,
    artifacts JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### memory.memories (scope circle)

```sql
-- Champs pertinents pour mémoire partagée
scope memory_scope,  -- agent, circle, project, global
scope_id BIGINT,     -- ID du scope (circle_id, project_id, etc.)
agent_id BIGINT,     -- Agent qui a créé la mémoire
```

## Exemples d'Usage

### Exemple 1: Créer un Circle et Ajouter des Agents

```python
from gathering.orchestration.circle_store import CircleStore

store = CircleStore.from_env()

# Créer le circle
circle_id = store.create_circle(
    name="ai-research",
    display_name="AI Research Team",
)

# Ajouter Sophie (lead) et Olivia (member)
store.add_member(circle_id, agent_id=1, role='lead')
store.add_member(circle_id, agent_id=2, role='member')

# Lister les membres
members = store.list_members(circle_id)
for m in members:
    print(f"{m['agent_name']} - {m['role']}")
```

### Exemple 2: Mémoire Partagée entre Agents

```python
from gathering.rag.memory_manager import MemoryManager

memory = MemoryManager.from_env()

# Agent 1 partage une décision
await memory.remember(
    agent_id=1,
    content="On utilise React pour le dashboard",
    memory_type="decision",
    scope="circle",
    scope_id=circle_id,
)

# Agent 2 peut retrouver cette décision
results = await memory.recall(
    agent_id=2,
    query="Quelle techno pour le dashboard ?",
)
# → Trouve: "On utilise React pour le dashboard"
```

### Exemple 3: Workflow Complet

```python
from gathering.orchestration.circle_store import CircleStore
from gathering.rag.memory_manager import MemoryManager

# Setup
circle_store = CircleStore.from_env()
memory = MemoryManager.from_env()

# 1. Créer circle
circle_id = circle_store.create_circle(name="backend-team")
circle_store.add_member(circle_id, agent_id=1, role='lead')
circle_store.add_member(circle_id, agent_id=2, role='member')

# 2. Créer tâche
task_id = circle_store.create_task(
    circle_id=circle_id,
    title="Optimiser les requêtes DB",
    priority='high',
)

# 3. Agent 1 travaille et partage ses découvertes
await memory.remember(
    agent_id=1,
    content="Découverte: Ajouter un index sur user_id améliore les perfs de 300%",
    memory_type="learning",
    scope="circle",
    scope_id=circle_id,
    tags=["performance", "database"],
)

# 4. Agent 2 bénéficie de cette connaissance
learnings = await memory.recall(
    agent_id=2,
    query="Comment optimiser les requêtes ?",
)
```

## Tests

**Tests automatisés ajoutés (`tests/test_dashboard_circles.py`):**
- 14 nouveaux tests pour les endpoints dashboard circles
- Tests du DataService en mode démo pour circles/members/tasks
- Validation de la structure des données démo
- Vérification de la cohérence des compteurs (member_count, task_count)

**Tests manuels:**
- ✅ Création de circles avec CircleStore
- ✅ Ajout/suppression de membres
- ✅ Création de tâches
- ✅ Mémoire partagée scope=circle
- ✅ Recherche sémantique cross-agents
- ✅ Endpoints dashboard circles en mode démo

**Résultats:**
- **603 tests passent** (14 nouveaux)
- **Couverture: 77.98%**

### 3. Endpoints Dashboard Circles (`gathering/api/routers/dashboard.py`)

Nouveaux endpoints pour visualiser les circles dans le dashboard web.

**Endpoints ajoutés:**
```
GET /dashboard/circles          - Liste tous les circles
GET /dashboard/circles/{id}     - Détails d'un circle
GET /dashboard/circles/{id}/members  - Membres d'un circle
GET /dashboard/circles/{id}/tasks    - Tâches d'un circle
GET /dashboard/stats            - Statistiques (incluant circles)
```

**Exemple - Lister les circles:**
```bash
curl http://localhost:8000/dashboard/circles
```

```json
{
  "circles": [
    {
      "id": 1,
      "name": "ai-research",
      "display_name": "AI Research Team",
      "description": "Research and experimentation with LLMs",
      "status": "running",
      "member_count": 2,
      "task_count": 3
    }
  ],
  "total": 3,
  "demo_mode": true
}
```

**Exemple - Membres d'un circle:**
```bash
curl http://localhost:8000/dashboard/circles/1/members
```

```json
{
  "circle_id": 1,
  "members": [
    {
      "id": 1,
      "agent_id": 1,
      "agent_name": "Dr. Sophie Chen",
      "role": "lead",
      "competencies": ["research", "analysis"]
    },
    {
      "id": 2,
      "agent_id": 2,
      "agent_name": "Olivia Nakamoto",
      "role": "member",
      "competencies": ["python", "typescript"]
    }
  ],
  "total": 2,
  "demo_mode": true
}
```

**Données démo ajoutées:**
- 3 circles: ai-research, backend-team, devops
- 5 membres répartis entre les circles
- 10 tâches avec différents statuts (pending, in_progress, completed)

### 4. Intégration Projet - Agents Travaillent sur Projet Externe

Circle et agents peuvent maintenant être liés à un projet externe et travailler sur ses fichiers.

**Changements:**
- Ajout `project_id` à `circle.circles` (migration 015)
- `CircleStore.create_circle()` accepte `project_id`
- `CircleStore.create_task()` accepte `project_id`
- `CircleStore.list_circles(project_id=...)` filtre par projet
- `AgentWrapper.load_project_context()` charge automatiquement projet
- Skills project-aware : résolution automatique chemins relatifs

**Workflow complet:**

```python
from gathering.orchestration.circle_store import CircleStore
from gathering.agents.wrapper import AgentWrapper

# 1. Créer circle lié au projet
store = CircleStore.from_env()
circle_id = store.create_circle(
    name="my-app-team",
    project_id=1,  # ID du projet
)

# 2. Ajouter agents
store.add_member(circle_id, agent_id=1, role='lead')
store.add_member(circle_id, agent_id=2, role='member')

# 3. Créer tâche sur fichier du projet
task_id = store.create_task(
    circle_id=circle_id,
    title="Fix bug in src/api/auth.py",
    project_id=1,
    context={"file": "src/api/auth.py", "issue": "Validation broken"},
)

# 4. Agent charge projet et travaille
agent = AgentWrapper(agent_id=1, persona=..., llm=...)
agent.load_project_context("/home/user/my-app", project_id=1)

# Chemins relatifs résolus automatiquement !
response = await agent.chat("Read src/api/auth.py and find the bug")
# → Résout automatiquement vers /home/user/my-app/src/api/auth.py
```

**Auto-résolution des chemins:**
- Quand `project` chargé, les skills `filesystem`, `git`, `code` résolvent les chemins relatifs
- Agent peut dire "lis src/main.py" → devient "/project/root/src/main.py"
- Contexte projet injecté dans le system prompt

## Prochaines Étapes

**Phase 4 (complet):**
1. ✅ Endpoints `/dashboard/circles` pour visualiser les circles
2. ✅ Intégration projet → circle → agents avec chemins auto-résolus
3. ⏳ WebSocket pour updates temps réel des circles

**Phase 5 (future):**
1. Orchestration automatique des tâches
2. Review workflow entre agents
3. Résolution de conflits
