# Conversations - Documentation

## Vue d'ensemble

Le système de conversations permet à plusieurs agents IA de dialoguer entre eux sur un sujet donné. Chaque conversation est orchestrée selon une stratégie de tour de parole configurable.

## Création d'une conversation

### Paramètres

| Paramètre | Type | Description |
|-----------|------|-------------|
| `topic` | string | Le sujet de la conversation |
| `agent_ids` | number[] | Liste des IDs des agents participants (minimum 2) |
| `max_turns` | number | Nombre maximum de tours de parole (défaut: 10) |
| `turn_strategy` | TurnStrategy | Stratégie de tour de parole |
| `facilitator_id` | number? | ID de l'agent facilitateur (requis pour FACILITATOR_LED) |

### Stratégies de tour de parole

#### 1. ROUND_ROBIN (Tour à tour)
Chaque agent parle à son tour dans un ordre circulaire fixe.

```
Agent A → Agent B → Agent C → Agent A → ...
```

**Cas d'usage:** Discussions structurées où chaque participant doit avoir un temps de parole égal.

#### 2. MENTION_BASED (Basé sur les mentions)
L'agent mentionné dans le dernier message parle ensuite. Si aucune mention, retour au round robin.

```
Agent A: "Qu'en penses-tu @AgentB ?"
→ Agent B parle
Agent B: "Je pense que @AgentC devrait répondre"
→ Agent C parle
```

**Cas d'usage:** Conversations dynamiques où les agents peuvent diriger le flux de discussion.

#### 3. FREE_FORM (Libre)
Mode conversationnel libre avec les règles suivantes:
- Les mentions sont respectées en priorité
- Sinon, un agent aléatoire parmi ceux qui n'ont pas parlé récemment est choisi
- Évite les répétitions (le dernier speaker ne peut pas reparler immédiatement)

```
Agent A parle
→ Agent B ou C choisi aléatoirement (pas A)
Agent B parle, mentionne @AgentA
→ Agent A parle (mention respectée)
```

**Cas d'usage:** Brainstorming, discussions créatives, débats ouverts.

#### 4. FACILITATOR_LED (Dirigé par un facilitateur)
Un agent désigné comme facilitateur orchestre la conversation:
- Le facilitateur parle en premier
- Le facilitateur indique qui doit parler ensuite
- Les autres agents attendent d'être appelés

Le facilitateur peut désigner le prochain speaker de plusieurs façons:
- `@AgentName` - mention directe
- `AgentName,` - nom suivi d'une virgule en début de message
- `"let's hear from AgentName"` - formulation naturelle
- `"AgentName, your turn"` - invitation explicite

```
Facilitateur: "Commençons par @AgentA"
→ Agent A parle
Agent A: "Voici mon analyse..."
→ Facilitateur parle (reprend automatiquement)
Facilitateur: "Intéressant. AgentB, qu'en pensez-vous ?"
→ Agent B parle
```

**Cas d'usage:** Réunions formelles, interviews, présentations structurées.

## Fin de conversation

Une conversation se termine quand:

1. **Limite de tours atteinte:** Le nombre de messages atteint `max_turns`
2. **Marqueur de fin:** Un agent inclut un marqueur de terminaison dans son message:
   - `[TERMINÉ]`
   - `[DONE]`
   - `[FIN]`
   - `[COMPLETE]`

## Interface Dashboard

### Création de conversation

1. Cliquer sur "New Conversation"
2. Entrer le sujet
3. Sélectionner les agents participants (minimum 2)
4. Configurer le nombre maximum de tours
5. Choisir la stratégie de tour de parole
6. Si FACILITATOR_LED: sélectionner l'agent facilitateur parmi les participants
7. Cliquer sur "Start Conversation"

### Visualisation

La page Conversations affiche:
- Liste des conversations avec leur statut
- Sujet et participants
- Nombre de messages / max_turns
- Stratégie utilisée
- Historique des messages avec l'identité de chaque speaker

## API

### Créer une conversation

```typescript
POST /api/conversations
{
  "topic": "Discussion sur l'architecture",
  "agent_ids": [1, 2, 3],
  "max_turns": 15,
  "turn_strategy": "facilitator_led",
  "facilitator_id": 1
}
```

### Réponse

```typescript
{
  "id": 1,
  "topic": "Discussion sur l'architecture",
  "status": "active",
  "participants": [...],
  "messages": [],
  "max_turns": 15,
  "turn_strategy": "facilitator_led",
  "facilitator_id": 1,
  "created_at": "2024-01-15T10:00:00Z"
}
```

## Implémentation technique

### Fichiers clés

| Fichier | Description |
|---------|-------------|
| `gathering/agents/conversation.py` | Logique de conversation et stratégies |
| `dashboard/src/pages/Conversations.tsx` | Interface utilisateur |
| `tests/test_agent_conversation.py` | Tests unitaires |

### Classe AgentConversation

```python
@dataclass
class AgentConversation:
    topic: str
    participants: List[ConversationParticipant]
    max_turns: int = 10
    turn_strategy: TurnStrategy = TurnStrategy.ROUND_ROBIN
    facilitator_id: Optional[int] = None
    messages: List[ConversationMessage] = field(default_factory=list)
```

### Validation

- FACILITATOR_LED requiert un `facilitator_id` valide
- Le facilitateur doit être un participant de la conversation
- Minimum 2 participants requis

## Tests

Les tests couvrent:
- ✅ Stratégie ROUND_ROBIN
- ✅ Stratégie MENTION_BASED
- ✅ Stratégie FREE_FORM (respect des mentions, évitement des répétitions)
- ✅ Stratégie FACILITATOR_LED (extraction des choix, validation)
- ✅ Validation des erreurs (facilitator_id manquant, facilitateur non-participant)
- ✅ Interface dashboard (création, sélection du facilitateur)

Exécution des tests:
```bash
# Tests Python
pytest tests/test_agent_conversation.py -v

# Tests Dashboard
cd dashboard && npm test
```
