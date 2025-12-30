# Phase 1 : Connexion des composants - Changelog

**Date** : 2025-12-23
**Objectif** : Rendre les agents fonctionnels avec mémoire persistante et exécution de tools

---

## Résumé des changements

Cette phase a connecté les composants existants pour créer un agent réellement fonctionnel :

1. **Boucle d'exécution des tools** - Les agents peuvent maintenant utiliser des skills
2. **Injection de mémoire** - Les agents se souviennent des informations passées
3. **Format Anthropic** - Support complet du format tool_use/tool_result

---

## Fichiers modifiés

### 1. `gathering/agents/wrapper.py`

#### Protocol LLMProvider (lignes 17-31)
```python
# AVANT : async, retourne str
async def complete(...) -> str

# APRÈS : sync, retourne Dict (compatible ILLMProvider)
def complete(...) -> Dict[str, Any]
```

#### Méthode chat() - Boucle d'exécution (lignes 313-395)
```python
# AVANT : Un seul appel LLM, tool_calls ignorés
llm_response = self.llm.complete(messages)
tool_calls = llm_response.get("tool_calls", [])  # Non utilisé !

# APRÈS : Boucle complète avec exécution des tools
while iteration < self.config.max_iterations:
    llm_response = self.llm.complete(messages, tools=tools)
    tool_calls = llm_response.get("tool_calls", [])

    if not tool_calls:
        break  # Terminé

    # Exécuter chaque tool
    for tool_call in tool_calls:
        result = await self._execute_tool(tool_name, tool_args)
        messages.append({"role": "tool", "tool_use_id": id, ...})

    # Continuer la boucle pour traiter les résultats
```

**Impact** : Les agents peuvent maintenant appeler des tools (calculatrice, git, fichiers...) et recevoir les résultats.

---

### 2. `gathering/llm/providers.py`

#### AnthropicProvider.complete() - Format tool_use (lignes 407-416)
```python
# AVANT : id manquant
result["tool_calls"].append({
    "name": block.name,
    "arguments": block.input,
})

# APRÈS : id inclus pour tool_result
result["tool_calls"].append({
    "id": block.id,  # Requis pour tool_result
    "name": block.name,
    "arguments": block.input,
})
```

#### AnthropicProvider.complete() - Conversion des messages (lignes 367-405)
```python
# AVANT : Seuls system/user/assistant supportés
for msg in messages:
    if msg["role"] == "system":
        system_msg = msg["content"]
    else:
        chat_messages.append(msg)

# APRÈS : Conversion tool -> tool_result format Anthropic
elif msg["role"] == "tool":
    chat_messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": msg.get("tool_use_id"),
            "content": msg.get("content"),
        }],
    })
elif msg["role"] == "assistant" and "tool_calls" in msg:
    # Convertir en blocs tool_use
    content_blocks = [{"type": "tool_use", ...} for tc in msg["tool_calls"]]
    chat_messages.append({"role": "assistant", "content": content_blocks})
```

**Impact** : Les conversations multi-tours avec tools fonctionnent avec l'API Anthropic.

---

### 3. `gathering/agents/memory.py`

#### InMemoryStore.search_memories() - Recherche améliorée (lignes 96-141)
```python
# AVANT : Recherche exacte de la chaîne entière
if query_lower in entry.content.lower():  # "loc projet" != "L'utilisateur Loc..."

# APRÈS : Recherche par mots-clés avec scoring
stop_words = {"que", "sur", "est", ...}
query_words = [w for w in query.split() if len(w) > 2 and w not in stop_words]

for entry in memories:
    matches = sum(1 for word in query_words if word in content_lower)
    if matches > 0:
        scored_results.append((matches, entry))

# Tri par score décroissant
scored_results.sort(key=lambda x: x[0], reverse=True)
```

**Impact** : La recherche de mémoires fonctionne avec des requêtes naturelles.

---

### 4. `tests/test_agents_persistence.py`

#### Fixture mock_llm (lignes 617-626)
```python
# AVANT : Retourne string (incompatible)
llm.complete = AsyncMock(return_value="Hello!")

# APRÈS : Retourne Dict (compatible ILLMProvider)
llm.complete = MagicMock(return_value={
    "role": "assistant",
    "content": "Hello! I'm ready to help.",
})
```

---

## Tests de validation

### Test 1 : Exécution de tools
```python
# Agent avec skill calculatrice
agent.add_skill(CalculatorSkill())
response = await agent.chat("Combien font 15 * 7 + 23 ?")

# Résultat :
# - Tool appelé : calculate(expression="15 * 7 + 23")
# - Résultat : 128
# - Réponse finale : "Le calcul donne 128"
# - Itérations : 2 (1 appel tool + 1 réponse finale)
```

### Test 2 : Mémoire persistante
```python
# Stocker des faits
await agent.remember("L'utilisateur s'appelle Loc.")
await agent.remember("Loc travaille sur GatheRing.")

# Question utilisant la mémoire
response = await agent.chat("Que sais-tu sur Loc ?")

# Résultat : L'agent répond avec les informations stockées
```

---

## Architecture après Phase 1

```
┌─────────────────────────────────────────────────────────────┐
│                        AgentWrapper                          │
├─────────────────────────────────────────────────────────────┤
│  chat(message)                                               │
│    │                                                         │
│    ├─► build_context() ─► MemoryService.build_context()     │
│    │                       └─► search_memories(query)        │
│    │                       └─► inject into system_prompt     │
│    │                                                         │
│    └─► LOOP:                                                 │
│         ├─► llm.complete(messages, tools)                   │
│         │                                                    │
│         ├─► Si tool_calls:                                   │
│         │    ├─► _execute_tool(name, args)                  │
│         │    ├─► Ajouter tool_result aux messages           │
│         │    └─► Continuer la boucle                        │
│         │                                                    │
│         └─► Sinon: Retourner réponse finale                 │
│                                                              │
│    └─► record_exchange() ─► Sauvegarder en mémoire          │
└─────────────────────────────────────────────────────────────┘
```

---

## Prochaines étapes (Phase 2)

1. **Connecter à PostgreSQL** - Remplacer InMemoryStore par le vrai RAG
2. **Embeddings vectoriels** - Utiliser pgvector pour la recherche sémantique
3. **API endpoints** - Connecter les routers à la base de données
4. **Dashboard** - Afficher des données réelles au lieu de démo

---

## Statistiques

- **Tests** : 552 passed, 1 skipped
- **Couverture** : 80.53%
- **Fichiers modifiés** : 4
- **Lignes ajoutées** : ~120
- **Lignes modifiées** : ~50
