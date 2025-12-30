# Phase 2: Mémoire PostgreSQL Persistante

## Résumé

Cette phase connecte le système de mémoire des agents à PostgreSQL avec pgvector pour une recherche sémantique persistante. Les agents peuvent maintenant conserver leur mémoire entre les sessions et retrouver des informations pertinentes via la similarité vectorielle.

## Changements Réalisés

### 1. Nouveau: PostgresMemoryStore (`gathering/agents/postgres_store.py`)

Bridge entre `MemoryService` (agents) et `MemoryManager` (RAG) pour la persistance PostgreSQL.

```python
from gathering.agents.postgres_store import PostgresMemoryStore
from gathering.agents.memory import MemoryService

# Créer un store avec connexion PostgreSQL + OpenAI embeddings
store = PostgresMemoryStore.from_env()
memory = MemoryService(store=store)

# Stocker une mémoire (persistée dans PostgreSQL avec embedding)
await memory.remember(
    agent_id=1,
    content="L'utilisateur préfère le mode sombre",
    memory_type="preference",
)

# Rechercher par similarité sémantique
results = await memory.recall(
    agent_id=1,
    query="Quelles sont les préférences ?",
)
```

**Fonctionnalités:**
- Normalisation automatique des types de mémoire (ex: "conversation" → "context")
- Fallback vers recherche par mots-clés si les embeddings échouent
- Seuil de similarité configurable (défaut: 0.4)
- Support des types valides: `fact`, `preference`, `context`, `decision`, `error`, `feedback`, `learning`

### 2. Fix: Bug VectorStore Search (`gathering/rag/vectorstore.py`)

**Problème:** L'ordre des paramètres SQL était incorrect, causant une erreur "smallint cannot be cast to vector".

**Solution:** Reconstruction correcte des paramètres pour la requête pgvector:
```python
# Avant (incorrect)
params[:-2] + [embedding_str, embedding_str, threshold, limit]

# Après (correct)
[embedding_str] + params + [embedding_str, threshold, embedding_str, limit]
```

### 3. Injection Automatique dans API (`gathering/api/dependencies.py`)

Le `get_memory_service()` utilise automatiquement PostgreSQL quand les variables d'environnement sont configurées:

```python
# Si OPENAI_API_KEY et (DATABASE_URL ou DB_HOST) sont définis:
#   → Utilise PostgresMemoryStore
# Sinon:
#   → Fallback vers InMemoryStore (volatile)
```

### 4. Tests: 14 nouveaux tests (`tests/test_postgres_store.py`)

- Tests unitaires pour la normalisation des types
- Tests des opérations store/search/recall
- Tests de fallback et gestion d'erreurs
- Couverture: 77% du nouveau fichier

## Configuration Requise

### Variables d'Environnement (.env)

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/gathering
# ou
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gathering
DB_USER=user
DB_PASSWORD=pass

# OpenAI (pour les embeddings)
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Schéma Base de Données

Le schéma `memory` avec pgvector doit être installé:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory.memories (
    id BIGSERIAL PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id),
    memory_type memory_type NOT NULL,
    key VARCHAR(255),
    value TEXT NOT NULL,
    embedding vector(1536),
    importance FLOAT DEFAULT 0.5,
    -- ... autres colonnes
);
```

## Exemple d'Utilisation Complet

```python
import asyncio
from gathering.agents.postgres_store import PostgresMemoryStore
from gathering.agents.memory import MemoryService
from gathering.agents.persona import AgentPersona
from gathering.agents.wrapper import AgentWrapper, AgentConfig
from gathering.llm.providers import AnthropicProvider

async def main():
    # Configuration
    store = PostgresMemoryStore.from_env()
    memory = MemoryService(store=store)

    persona = AgentPersona(
        name="Sophie",
        role="Assistant AI",
        traits=["helpful", "mémorise le contexte"],
    )
    memory.set_persona(1, persona)

    llm = AnthropicProvider(
        name="anthropic",
        config={"model": "claude-sonnet-4-20250514"},
    )

    agent = AgentWrapper(
        agent_id=1,  # ID existant dans la DB
        persona=persona,
        llm=llm,
        memory=memory,
    )

    # La mémoire est automatiquement:
    # - Injectée dans le contexte avant chaque réponse
    # - Enrichie après chaque échange
    response = await agent.chat("Que sais-tu sur moi ?")
    print(response.content)

asyncio.run(main())
```

## Tests

```bash
# Tous les tests
python -m pytest tests/ -v

# Seulement PostgresMemoryStore
python -m pytest tests/test_postgres_store.py -v
```

## Résultats

- **566 tests passent** (14 nouveaux)
- **Couverture: 80.37%**
- **Mémoire persistante fonctionnelle** avec recherche sémantique
- **Agents se souviennent** du contexte entre les sessions

## Prochaines Étapes

1. **Phase 3: Dashboard → DB** - Connecter les endpoints API à PostgreSQL
2. **Phase 4: Multi-agents** - Collaboration entre agents avec mémoire partagée
3. **Phase 5: Optimisation** - Cache d'embeddings, batch processing
