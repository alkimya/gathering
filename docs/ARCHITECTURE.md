# GatheRing ䷬ - Architecture Documentation

**Version:** 0.14.0 (Phase 14 - Extended Skills System)
**Date:** 2025-12-22

---

## Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Architecture Multi-Agents](#2-architecture-multi-agents)
3. [Persistance et Mémoire](#3-persistance-et-mémoire)
4. [Base de Données](#4-base-de-données)
5. [Système de Skills](#5-système-de-skills)
6. [LLM Providers](#6-llm-providers)
7. [Système de Review](#7-système-de-review)
8. [API et Interface Web](#8-api-et-interface-web)

---

## 1. Vue d'Ensemble

GatheRing est un framework de collaboration multi-agents IA. Il permet de constituer des équipes d'agents autonomes qui travaillent ensemble sur des projets.

### Principes Architecturaux

| Principe | Description |
|----------|-------------|
| **Gathering Circle** | Agents autonomes et égaux, pas de hiérarchie stricte |
| **Shared Context** | Mémoire et contexte partagés via base de données |
| **Skill-Based** | Capacités modulaires, chargées à la demande |
| **Review & Audit** | Tout travail peut être reviewé par un autre agent |
| **Human in the Loop** | L'humain reste l'arbitre final |

### Stack Technologique

```
Backend:
├── Python 3.11+
├── FastAPI (API REST)
├── PostgreSQL + pgvector (Base de données)
├── PicoPG (Accès DB)
├── SQLAlchemy (ORM pour les modèles)
└── Pydantic (Validation)

Frontend (prévu):
├── React / Next.js
├── TypeScript
└── TailwindCSS

LLM Providers:
├── Anthropic (Claude)
├── DeepSeek
├── OpenAI (GPT-4)
└── Ollama (Local)
```

---

## 2. Architecture Multi-Agents

### Concept "Gathering Circle"

Le Gathering Circle est un modèle d'orchestration **hybride léger** où les agents sont autonomes mais coordonnés par un Facilitateur qui n'est pas un manager mais un routeur intelligent.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       GATHERING CIRCLE                               │
│                                                                      │
│    ┌─────────┐      Contexte partagé       ┌─────────┐             │
│    │ Claude  │◄────────────────────────────►│DeepSeek │             │
│    │ (Arch)  │                              │ (Code)  │             │
│    └────┬────┘                              └────┬────┘             │
│         │                                        │                   │
│         │       ┌──────────────────────┐        │                   │
│         └──────►│     FACILITATEUR     │◄───────┘                   │
│                 │                      │                            │
│                 │  • Route les tâches  │                            │
│                 │  • Maintient contexte│                            │
│                 │  • Détecte conflits  │                            │
│                 │  • N'est PAS un boss │                            │
│                 └──────────┬───────────┘                            │
│                            │                                         │
│    ┌─────────┐            │             ┌─────────┐                │
│    │  Kimi   │◄───────────┴────────────►│  GPT-4  │                │
│    │ (Docs)  │                          │ (Tests) │                │
│    └─────────┘                          └─────────┘                │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    SHARED CONTEXT (PostgreSQL)                  │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │ │
│  │  │ Tasks    │  │ Memory   │  │ Messages │  │ Reviews  │       │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Principes Fondamentaux

| Principe | Description |
|----------|-------------|
| **Autonomie** | Chaque agent décide de ses actions, peut refuser une tâche |
| **Compétences** | Les agents ont des domaines d'expertise déclarés |
| **Facilitateur ≠ Manager** | Route les tâches, ne commande pas |
| **Communication par événements** | Système pub/sub pour coordination |
| **Review croisée** | Tout travail peut être audité par un pair |
| **Humain = Arbitre** | L'humain intervient sur escalations |

### Architecture des Composants

```
gathering/
├── orchestration/           # Multi-agent coordination ✅
│   ├── __init__.py
│   ├── facilitator.py      # Facilitateur (routeur) ✅
│   ├── circle.py           # GatheringCircle (orchestrateur) ✅
│   └── events.py           # Système d'événements (23 types) ✅
│
├── agents/                  # Agent persistence & identity ✅
│   ├── __init__.py
│   ├── persona.py          # AgentPersona (identité persistante) ✅
│   ├── project_context.py  # ProjectContext (venv, tools, conventions) ✅
│   ├── session.py          # AgentSession (suivi session) ✅
│   ├── memory.py           # MemoryService (injection contexte) ✅
│   ├── wrapper.py          # AgentWrapper (enveloppe LLM) ✅
│   └── resume.py           # SessionResume (reprise) ✅
```

### Facilitateur

Le Facilitateur est le cœur du système mais **n'est pas un manager**. Il :

- **Route** les tâches vers les agents compétents
- **Maintient** le contexte partagé
- **Détecte** les conflits (2 agents sur même fichier)
- **Escalade** vers l'humain si nécessaire

```python
class Facilitator:
    """
    Facilitateur du Gathering Circle.
    Route les tâches, ne commande pas.
    """

    def route_task(self, task: Task) -> Optional[Agent]:
        """
        Trouve le meilleur agent pour une tâche.

        Algorithme:
        1. Filtre par compétences requises
        2. Score par charge de travail
        3. Score par historique qualité
        4. L'agent peut accepter ou refuser
        """

    def broadcast_event(self, event: Event) -> None:
        """Diffuse un événement à tous les agents."""

    def detect_conflicts(self) -> List[Conflict]:
        """Détecte les conflits potentiels."""
```

### Système d'Événements

Les agents communiquent via un système d'événements asynchrone :

```python
# Types d'événements
class EventType(Enum):
    # Lifecycle
    AGENT_JOINED = "agent.joined"
    AGENT_LEFT = "agent.left"

    # Tasks
    TASK_CREATED = "task.created"
    TASK_CLAIMED = "task.claimed"
    TASK_COMPLETED = "task.completed"
    TASK_BLOCKED = "task.blocked"

    # Reviews
    REVIEW_REQUESTED = "review.requested"
    REVIEW_COMPLETED = "review.completed"

    # Communication
    MESSAGE_SENT = "message.sent"
    MENTION_RECEIVED = "mention.received"

    # Conflicts
    CONFLICT_DETECTED = "conflict.detected"
    ESCALATION_CREATED = "escalation.created"

# Exemple d'utilisation
circle.emit(EventType.TASK_COMPLETED, {
    "task_id": 123,
    "agent_id": 1,
    "result": "Feature implemented",
    "artifacts": ["src/feature.py"]
})

# Agent peut s'abonner aux événements
@agent.on(EventType.MENTION_RECEIVED)
async def handle_mention(event):
    if event.data["mentioned_agent"] == agent.id:
        await agent.respond(event.data["message"])
```

### Flux de Travail Détaillé

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW COMPLET                             │
└─────────────────────────────────────────────────────────────────────┘

1. CRÉATION DE TÂCHE
   ┌─────────┐
   │ Humain  │──────► Task créée (status: PENDING)
   └─────────┘              │
                            ▼
2. ROUTAGE PAR FACILITATEUR
   ┌─────────────────────────────────────────────┐
   │ Facilitateur analyse:                        │
   │ • Compétences requises: ["python", "api"]   │
   │ • Agents disponibles avec ces compétences   │
   │ • Charge de travail actuelle                │
   │ • Historique de qualité                     │
   └─────────────────────────────────────────────┘
                            │
                            ▼
3. PROPOSITION À L'AGENT
   ┌─────────┐         ┌─────────┐
   │ Agent A │◄────────│  Offre  │
   └────┬────┘         └─────────┘
        │
        ├──► ACCEPTE ──► Task status: CLAIMED puis IN_PROGRESS
        │
        └──► REFUSE ──► Proposer à Agent B

4. EXÉCUTION
   ┌─────────────────────────────────────────────┐
   │ Agent travaille:                             │
   │ • Utilise Skills (Git, Test, etc.)          │
   │ • Peut demander aide: @DeepSeek review this │
   │ • Émet événements de progression            │
   └─────────────────────────────────────────────┘
                            │
                            ▼
5. SOUMISSION POUR REVIEW
   Task status: REVIEW
   emit(REVIEW_REQUESTED, {task_id, work, suggested_reviewer})
                            │
                            ▼
6. REVIEW PAR UN PAIR
   ┌─────────────────────────────────────────────┐
   │ Reviewer (différent de l'auteur):           │
   │ • Examine le travail                        │
   │ • Attribue score (0-100)                    │
   │ • Décision: APPROVED / CHANGES / REJECTED   │
   └─────────────────────────────────────────────┘
        │
        ├──► APPROVED ──► Task: COMPLETED
        │                 Agent métriques mises à jour
        │
        ├──► CHANGES_REQUESTED ──► Task: IN_PROGRESS
        │                          iteration++
        │
        └──► REJECTED ──► Escalation créée
                          Humain notifié
```

### Gestion des Conflits

```python
class ConflictType(Enum):
    FILE_COLLISION = "file_collision"      # 2 agents modifient même fichier
    TASK_DEADLOCK = "task_deadlock"        # Dépendance circulaire
    RESOURCE_CONTENTION = "resource"       # Même ressource externe
    OPINION_DIVERGENCE = "opinion"         # Désaccord technique

class ConflictResolver:
    def resolve(self, conflict: Conflict) -> Resolution:
        match conflict.type:
            case ConflictType.FILE_COLLISION:
                # Merge automatique si possible, sinon humain
                return self._resolve_file_collision(conflict)

            case ConflictType.OPINION_DIVERGENCE:
                # Vote ou escalation à l'humain
                return self._resolve_by_vote_or_human(conflict)
```

### Métriques et Apprentissage

Le système apprend des performances pour améliorer le routage :

```python
# Métriques par agent
agent.metrics = {
    "tasks_completed": 42,
    "average_quality_score": 87.5,
    "approval_rate": 0.92,           # Approuvé du premier coup
    "average_review_time": 1.5,      # heures
    "competency_scores": {
        "python": 0.95,
        "api": 0.88,
        "testing": 0.75,
    }
}

# Le Facilitateur utilise ces métriques pour le routage
def calculate_agent_score(agent, task):
    base_score = sum(
        agent.competency_scores.get(comp, 0)
        for comp in task.required_competencies
    )
    quality_bonus = agent.approval_rate * 0.2
    workload_penalty = len(agent.current_tasks) * 0.1
    return base_score + quality_bonus - workload_penalty
```

---

## 3. Persistance et Mémoire ✅ IMPLÉMENTÉ

### Le Problème

Sans persistance, les agents IA souffrent de :

- **Perte de contexte** après compactage ou nouvelle session
- **Oubli des conventions** du projet (venv, outils, structure)
- **Perte de persona** - l'agent redevient générique
- **Pas de continuité** - recommence à zéro à chaque fois

### La Solution : Architecture de Persistance

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT AVEC PERSISTANCE                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      AgentWrapper                                ││
│  │                                                                  ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          ││
│  │  │   Persona    │  │  LLM Client  │  │    Skills    │          ││
│  │  │  (persistant)│  │ (Claude/DS)  │  │ (Git, Test)  │          ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘          ││
│  │                           │                                      ││
│  │                           ▼                                      ││
│  │  ┌─────────────────────────────────────────────────────────────┐││
│  │  │                   MemoryService                              │││
│  │  │                                                              │││
│  │  │  Avant chaque appel LLM, injecte:                           │││
│  │  │  • Persona de l'agent                                       │││
│  │  │  • Contexte projet (venv, outils, conventions)              │││
│  │  │  • Dernière position (où j'en étais)                        │││
│  │  │  • Mémoires pertinentes (RAG)                               │││
│  │  │  • Tâche en cours et son historique                         │││
│  │  └─────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│                                │                                     │
│                                ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                 PostgreSQL + pgvector                            ││
│  │                                                                  ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           ││
│  │  │ Personas │ │ Memories │ │ Projects │ │ Sessions │           ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Composants Implémentés

| Fichier | Composant | Description | Tests |
|---------|-----------|-------------|-------|
| `persona.py` | `AgentPersona` | Identité persistante (nom, rôle, traits, style) | 5 tests |
| `project_context.py` | `ProjectContext` | Contexte projet (venv, tools, conventions) | 5 tests |
| `session.py` | `AgentSession` | Suivi de session avec fenêtre glissante | 9 tests |
| `session.py` | `InjectedContext` | Contexte à injecter dans les appels LLM | 1 test |
| `memory.py` | `MemoryService` | Service central d'injection de contexte | 10 tests |
| `memory.py` | `InMemoryStore` | Stockage mémoire pour tests | 3 tests |
| `wrapper.py` | `AgentWrapper` | Enveloppe LLM avec persona + mémoire | 10 tests |
| `resume.py` | `SessionResumeManager` | Gestion des reprises après compactage | 4 tests |
| `resume.py` | `ResumeContext` | Contexte de reprise avec stratégies | 3 tests |

**Total: 55 tests passent**

#### 3.1 AgentWrapper (gathering/agents/wrapper.py)

L'AgentWrapper enveloppe un LLM et lui donne persistance et identité.

```python
from gathering.agents import AgentWrapper, AgentPersona, MemoryService, AgentConfig

# Créer un agent avec persistance complète
agent = AgentWrapper(
    agent_id=1,
    persona=AgentPersona(
        name="Claude",
        role="Architecte",
        traits=["rigoureux", "pédagogue"],
        communication_style="detailed",
        specializations=["python", "architecture"],
    ),
    llm=my_llm_provider,
    memory=MemoryService(),
    config=AgentConfig(
        model="claude-sonnet-4-20250514",
        temperature=0.7,
        auto_remember=True,
    ),
)

# Ajouter des skills
agent.add_skill(git_skill)
agent.add_skill(test_skill)

# Définir le projet
agent.set_project(ProjectContext.from_path("/path/to/project"))

# Chat avec injection automatique de contexte
response = await agent.chat("Implémente la feature X")

# L'agent se souvient automatiquement des échanges importants
# et peut reprendre après compactage
```

#### 3.2 AgentPersona (gathering/agents/persona.py)

Le persona définit l'identité persistante de l'agent.

```python
from gathering.agents import AgentPersona, ARCHITECT_PERSONA, SENIOR_DEV_PERSONA

# Utiliser un persona prédéfini
persona = ARCHITECT_PERSONA
# Ou créer un custom
persona = AgentPersona(
    name="Claude",
    role="Architecte Principal",
    base_prompt="Tu es l'architecte principal du projet...",
    traits=["rigoureux", "pédagogue", "visionnaire"],
    communication_style="detailed",  # formal, concise, technical, friendly, balanced
    specializations=["architecture", "security", "python"],
    languages=["fr", "en"],
)

# Générer le system prompt avec contexte projet
system_prompt = persona.build_system_prompt(project_context)
```

**Personas prédéfinis:**

- `ARCHITECT_PERSONA` - Pour supervision, reviews, architecture
- `SENIOR_DEV_PERSONA` - Pour implémentation, tests, documentation
- `CODE_SPECIALIST_PERSONA` - Pour optimisation, debugging, algorithmes
- `QA_PERSONA` - Pour tests, qualité, automation

#### 3.3 ProjectContext (gathering/agents/project_context.py)

Stocke les informations du projet pour éviter les oublis.

```python
from gathering.agents import ProjectContext, GATHERING_PROJECT

# Auto-détection depuis un chemin
project = ProjectContext.from_path("/path/to/project")
# Détecte automatiquement: venv, git, requirements.txt, pyproject.toml

# Ou configuration manuelle
project = ProjectContext(
    name="Gathering",
    path="/home/loc/workspace/gathering",
    venv_path="/home/loc/workspace/gathering/venv",
    python_version="3.13",
    tools={
        "database": "picopg",
        "testing": "pytest",
        "orm": "sqlalchemy",
    },
    conventions={
        "primary_keys": "BIGINT GENERATED ALWAYS AS IDENTITY",
        "imports": "absolute",
        "docstrings": "google style",
    },
    key_files={
        "models": "gathering/db/models.py",
        "config": "gathering/core/config.py",
    },
    commands={
        "test": "source venv/bin/activate && pytest tests/ -v",
    },
    notes=[
        "Toujours utiliser picopg pour les connexions DB",
        "Les tests doivent passer avant commit",
    ],
)

# Génère un prompt contextualisé
context_prompt = project.to_prompt()
```

#### 3.4 MemoryService (gathering/agents/memory.py)

Service central qui gère l'injection de contexte.

```python
from gathering.agents import MemoryService, build_agent_context

# Service complet avec persistance
memory = MemoryService(store=InMemoryStore())  # Ou PostgresStore pour prod

# Configurer persona et projet
memory.set_persona(agent_id=1, persona=ARCHITECT_PERSONA)
memory.set_project(project_id=1, project=my_project)

# Construire le contexte avant un appel LLM
context = await memory.build_context(
    agent_id=1,
    user_message="Implémente la feature X",
    project_id=1,
    include_memories=True,
    memory_limit=5,
)

# context.system_prompt contient persona + projet + reprise + mémoires
# context.history contient les messages récents
# context.current_task contient la tâche en cours

# Enregistrer un échange
await memory.record_exchange(
    agent_id=1,
    user_message="Hello",
    assistant_response="Hi!",
    should_remember=True,  # Stocke en mémoire long-terme
)

# Mémoriser explicitement quelque chose
await memory.remember(agent_id=1, content="Décision: utiliser JWT", memory_type="decision")

# Rappeler des mémoires pertinentes
memories = await memory.recall(agent_id=1, query="authentification", limit=5)

# Tracker le travail en cours
memory.track_file(agent_id=1, file_path="src/auth.py")
memory.add_pending_action(agent_id=1, action="Écrire les tests")
memory.set_current_task(agent_id=1, task_id=42, title="Implémenter auth", progress="50%")
```

#### 3.5 Session et Reprise (gathering/agents/session.py, resume.py)

```python
from gathering.agents import AgentSession, SessionResumeManager, ResumeStrategy

# Session suit l'état de travail
session = AgentSession(agent_id=1, project_id=10)
session.add_message("user", "Implémente X")
session.add_working_file("src/x.py")
session.add_pending_action("Écrire tests")
session.set_current_task(42, "Feature X", "En cours...")

# Détection automatique du besoin de reprise (>1h d'inactivité)
if session.needs_resume:
    summary = session.generate_resume_summary()
    # "Dernière activité: il y a 2 heure(s)
    #  Tâche en cours: Feature X
    #  Actions en attente: Écrire tests
    #  Fichiers: src/x.py"

# Gestionnaire de reprise avec stratégies
manager = SessionResumeManager()

# Choisit automatiquement la stratégie selon le contexte
strategy = manager.get_strategy(session)
# ResumeStrategy.TASK_FOCUSED si tâche en cours
# ResumeStrategy.SUMMARY si longue absence (>24h)
# ResumeStrategy.FULL si travail en cours

# Génère le prompt de reprise
resume_prompt = manager.generate_resume_prompt(session, project)
```

**Stratégies de reprise:**

- `FULL` - Tous les détails (tâche, fichiers, actions, dernier échange)
- `SUMMARY` - Résumé condensé (pour longues absences)
- `TASK_FOCUSED` - Focus sur la tâche en cours
- `MINIMAL` - Juste l'essentiel (temps écoulé, tâche)

### Factory Functions

```python
from gathering.agents import (
    create_architect_agent,
    create_developer_agent,
    create_code_specialist_agent,
)

# Création rapide d'agents préconfigurés
architect = create_architect_agent(
    agent_id=1,
    llm=my_anthropic_provider,
    memory=shared_memory,
    project=my_project,
)

developer = create_developer_agent(
    agent_id=2,
    llm=my_anthropic_provider,
    memory=shared_memory,
    project=my_project,
)

code_specialist = create_code_specialist_agent(
    agent_id=3,
    llm=my_deepseek_provider,  # Utilise DeepSeek par défaut
    memory=shared_memory,
    project=my_project,
)
```

### Workflow de Persistance

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW AVEC PERSISTANCE                         │
└─────────────────────────────────────────────────────────────────────┘

1. NOUVELLE SESSION
   ┌─────────┐
   │ Humain  │──► "Continue le travail sur l'API"
   └─────────┘
        │
        ▼
2. CHARGEMENT CONTEXTE (MemoryService.build_context)
   ┌─────────────────────────────────────────────────────────────────┐
   │ • Charge persona: "Tu es Opus, l'Architecte..."                 │
   │ • Charge projet: venv, conventions, outils (picopg)             │
   │ • Charge session: "Tu travaillais sur les endpoints REST"       │
   │ • Charge mémoires: décisions passées pertinentes (RAG)          │
   │ • Charge tâche: "Implémenter GET /api/agents - 60% fait"        │
   └─────────────────────────────────────────────────────────────────┘
        │
        ▼
3. INJECTION DANS LE PROMPT (InjectedContext.to_messages)
   ┌─────────────────────────────────────────────────────────────────┐
   │ System: "Tu es Opus, Architecte du projet Gathering...          │
   │         Projet utilise venv, picopg pour DB, pytest...          │
   │                                                                 │
   │         ## Reprise de Session                                   │
   │         Dernière activité: il y a 2 heure(s)                    │
   │         Tâche en cours: GET /api/agents                         │
   │         Fichiers: src/api/agents.py                             │
   │                                                                 │
   │         ## Mémoires Pertinentes                                 │
   │         - Décision: utiliser Pydantic pour validation"          │
   └─────────────────────────────────────────────────────────────────┘
        │
        ▼
4. L'AGENT RÉPOND AVEC CONTEXTE COMPLET (AgentWrapper.chat)
   "Je reprends l'implémentation de GET /api/agents.
    Comme décidé, j'utilise Pydantic pour la validation.
    Je vais activer le venv et lancer les tests..."
        │
        ▼
5. SAUVEGARDE POST-INTERACTION (MemoryService.record_exchange)
   • Message et réponse → session.recent_messages
   • Points importants → memories (pour RAG)
   • Progression tâche → session.current_task_progress
   • Fichiers modifiés → session.working_files
```

### 3.6 Conversations Inter-Agents (gathering/agents/conversation.py)

Les agents peuvent communiquer directement entre eux pour collaborer sur des tâches.

```python
from gathering.agents import AgentConversation, TurnStrategy, create_agent_conversation
from gathering.orchestration import GatheringCircle

# Via le GatheringCircle (recommandé)
result = await circle.collaborate(
    topic="Écrire les scénarios BDD pour l'authentification",
    agent_ids=[sonnet.id, deepseek.id],
    max_turns=10,
    initial_prompt="Travaillez ensemble sur les scénarios Given/When/Then",
)

print(result.summary)
print(result.get_transcript())

# Ou directement avec AgentConversation
conversation = AgentConversation(
    topic="Review du code auth",
    participants=[sonnet_participant, deepseek_participant],
    max_turns=8,
    turn_strategy=TurnStrategy.ROUND_ROBIN,
)

result = await conversation.run()
```

**Stratégies de tours de parole:**

- `ROUND_ROBIN` - Chaque agent parle à tour de rôle
- `MENTION_BASED` - L'agent mentionné (@nom) parle ensuite
- `FREE_FORM` - N'importe qui peut parler

**Marqueurs de fin:**

- `[TERMINÉ]`, `[DONE]`, `[FIN]` - Terminent la conversation

**Composants:**

| Composant | Description |
|-----------|-------------|
| `AgentConversation` | Conversation entre 2+ agents |
| `ConversationMessage` | Un message dans la conversation |
| `ConversationResult` | Résultat avec transcript et summary |
| `CollaborativeTask` | Tâche partagée entre agents |
| `TurnStrategy` | Stratégie de gestion des tours |

### Exemple Complet : Équipe de Dev

```python
from gathering.agents import (
    AgentWrapper,
    MemoryService,
    ProjectContext,
    ARCHITECT_PERSONA,
    SENIOR_DEV_PERSONA,
    CODE_SPECIALIST_PERSONA,
)
from gathering.orchestration import GatheringCircle

# Service de mémoire partagé
memory = MemoryService()

# Projet Gathering (pré-configuré disponible)
project = ProjectContext(
    name="Gathering",
    path="/home/loc/workspace/gathering",
    venv_path="/home/loc/workspace/gathering/venv",
    python_version="3.13",
    tools={
        "database": "picopg",
        "testing": "pytest",
        "orm": "sqlalchemy",
        "llm_claude": "anthropic",
        "llm_deepseek": "openai-compatible",
    },
    conventions={
        "primary_keys": "BIGINT GENERATED ALWAYS AS IDENTITY",
        "imports": "absolute",
        "docstrings": "google style",
        "db_schema": "gathering",
    },
    notes=[
        "Toujours utiliser picopg pour les connexions DB",
        "Les tests doivent passer avant commit",
        "Review obligatoire par un autre agent",
        "Clés primaires en IDENTITY, pas UUID",
    ],
)

# Opus - L'Architecte (Claude)
opus = AgentWrapper(
    agent_id=1,
    persona=ARCHITECT_PERSONA,
    llm=anthropic_provider,
    memory=memory,
)
opus.set_project(project)

# Sonnet - Le Dev Senior (Claude)
sonnet = AgentWrapper(
    agent_id=2,
    persona=SENIOR_DEV_PERSONA,
    llm=anthropic_provider,
    memory=memory,
)
sonnet.set_project(project)

# DeepSeek - Le Spécialiste Code
deepseek = AgentWrapper(
    agent_id=3,
    persona=CODE_SPECIALIST_PERSONA,
    llm=deepseek_provider,
    memory=memory,
)
deepseek.set_project(project)

# Créer le circle
circle = GatheringCircle(name="gathering-dev")
circle.add_agent(...)  # Intégration avec orchestration

# Chat avec l'architecte - contexte injecté automatiquement
response = await opus.chat("Revise l'architecture de l'API")
# L'agent connaît le projet, ses conventions, et peut reprendre
# après compactage grâce à la session persistante
```

---

## 4. Base de Données ✅ PHASE 8

### Principes

| Règle | Description |
|-------|-------------|
| **Clés primaires** | Toujours `BIGINT GENERATED ALWAYS AS IDENTITY` |
| **Accès DB** | Via PicoPG ou SQLAlchemy |
| **Architecture** | Multi-schémas (agent, circle, project, communication, memory, review, audit) |
| **RAG** | pgvector pour les embeddings et recherche sémantique |
| **Audit** | Toutes les actions sont loguées |

### Architecture Multi-Schémas

```
Database: gathering
│
├── agent (Agents & Identity)
│   ├── providers           # Providers LLM (Anthropic, OpenAI, etc.)
│   ├── models              # Modèles avec pricing et capabilities
│   ├── personas            # Templates de personas réutilisables
│   ├── agents              # Instances d'agents (persona + model)
│   └── sessions            # Sessions agent avec état
│
├── circle (Orchestration)
│   ├── circles             # Gathering Circles (équipes)
│   ├── members             # Membres des circles
│   ├── tasks               # Tâches du board
│   ├── task_assignments    # Historique des assignations
│   ├── conflicts           # Conflits détectés
│   └── events              # Événements pub/sub
│
├── project (Projects)
│   ├── projects            # Projets logiciels
│   ├── files               # Fichiers indexés (RAG) avec embeddings
│   └── circle_projects     # Lien circles-projets
│
├── communication (Conversations)
│   ├── conversations       # Fils de discussion inter-agents
│   ├── messages            # Messages avec mentions
│   ├── chat_history        # Historique chat direct
│   └── notifications       # Notifications agents
│
├── memory (Memory & RAG) 🆕
│   ├── memories            # Mémoire long-terme avec vector embeddings
│   ├── embeddings_cache    # Cache des embeddings calculés
│   ├── knowledge_base      # Base de connaissances partagée
│   └── context_snapshots   # Snapshots de contexte
│
├── review (Reviews)
│   ├── reviews             # Reviews inter-agents
│   ├── comments            # Commentaires inline
│   ├── quality_metrics     # Métriques qualité historiques
│   └── standards           # Standards de qualité
│
└── audit (Audit & Logs)
    ├── logs                # Logs d'actions complets
    ├── escalations         # Issues pour humain
    ├── system_events       # Événements système
    ├── api_requests        # Logs API
    └── security_events     # Événements sécurité
```

### Schéma Agent Normalisé (Migration 011)

Le schéma `agent` a été normalisé pour éviter les duplications et permettre une gestion centralisée des modèles LLM.

```
┌──────────────────┐
│ agent.providers  │
├──────────────────┤
│ id SMALLINT PK   │
│ name             │──┐  "anthropic", "openai", "deepseek"...
│ api_base_url     │  │
│ is_local         │  │
└──────────────────┘  │
                      │
┌─────────────────────┴───────────────────────────────────────┐
│ agent.models                                                │
├─────────────────────────────────────────────────────────────┤
│ id SMALLINT PK                                              │
│ provider_id FK ─────────────────────────────────────────────┘
│ model_name         "claude-opus-4-5-20250514"
│ model_alias        "Opus 4.5"
│ pricing_in         15.00 ($/1M tokens)
│ pricing_out        75.00
│ extended_thinking  TRUE
│ vision             TRUE
│ context_window     200000
│ max_output         32000
└─────────────────────────────────────────────────────────────┘
          │
┌─────────┴───────────────────────────────────────────────────┐
│ agent.personas                                               │
├──────────────────────────────────────────────────────────────┤
│ id BIGINT PK                                                 │
│ display_name       "Dr. Sophie Chen"                         │
│ role               "Principal Software Architect"            │
│ base_prompt        Short description                         │
│ full_prompt        Complete system prompt                    │
│ traits[]           ["detail-oriented", "pragmatic"]          │
│ communication_style "detailed"                               │
│ specializations[]  ["python", "postgresql"]                  │
│ languages[]        ["French", "English"]                     │
│ motto              "Make it work, make it right..."          │
└──────────────────────────────────────────────────────────────┘
          │
┌─────────┴───────────────────────────────────────────────────┐
│ agent.agents                                                 │
├──────────────────────────────────────────────────────────────┤
│ id BIGINT PK                                                 │
│ name               Instance name                             │
│ persona_id FK ─────────────────────────────────────────────  │
│ model_id FK ───────────────────────────────────────────────  │
│ temperature        0.7 (override)                            │
│ max_tokens         NULL (uses model default)                 │
│ is_active          TRUE                                      │
│ status             "idle"                                    │
│ tasks_completed    42                                        │
│ ...metrics...                                                │
└──────────────────────────────────────────────────────────────┘
```

**Avantages de cette normalisation :**

| Aspect | Avant | Après |
|--------|-------|-------|
| Ajout d'un modèle | Modifier le code | `INSERT INTO agent.models` |
| Changement de prix | Impossible | `UPDATE agent.models` |
| Stats par provider | Parsing VARCHAR | `JOIN` sur `providers` |
| Validation modèle | Aucune | Contrainte FK |
| Taille mémoire | VARCHAR répétés | SMALLINT (2 bytes) |

**Fonctions utilitaires :**

```sql
-- Lister les modèles disponibles
SELECT * FROM agent.list_models();
SELECT * FROM agent.list_models('anthropic');

-- Créer un agent depuis une persona avec un modèle
SELECT agent.create_agent_from_persona('Dr. Sophie Chen', 'Opus 4.5');
SELECT agent.create_agent_from_persona('Olivia Nakamoto', 'Sonnet 4.5');

-- Changer le modèle d'un agent
SELECT agent.set_agent_model(1, 'Opus 4.5');

-- Voir la config complète d'un agent
SELECT * FROM agent.get_agent_config(1);

-- Vue complète avec détails persona et modèle
SELECT * FROM agent.agents_full;
```

**Modèles pré-configurés :**

| Provider | Alias | Model Name | In $/1M | Out $/1M | Context | Extended |
|----------|-------|------------|---------|----------|---------|----------|
| Anthropic | Opus 4.5 | claude-opus-4-5-20250514 | 15.00 | 75.00 | 200K | Yes |
| Anthropic | Sonnet 4.5 | claude-sonnet-4-5-20250514 | 3.00 | 15.00 | 200K | Yes |
| Anthropic | Haiku 3.5 | claude-3-5-haiku-20241022 | 0.80 | 4.00 | 200K | No |
| OpenAI | GPT-4o | gpt-4o | 2.50 | 10.00 | 128K | No |
| OpenAI | o1 | o1 | 15.00 | 60.00 | 200K | Yes |
| OpenAI | o3 Mini | o3-mini | 1.10 | 4.40 | 200K | Yes |
| DeepSeek | V3 | deepseek-chat | 0.27 | 1.10 | 64K | No |
| DeepSeek | R1 | deepseek-reasoner | 0.55 | 2.19 | 64K | Yes |
| Google | Gemini 2.0 Flash | gemini-2.0-flash | 0.10 | 0.40 | 1M | Yes |

### RAG avec pgvector

```sql
-- Extension pgvector pour les embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Table memories avec embedding
CREATE TABLE memory.memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT REFERENCES agent.agents(id),
    scope memory_scope NOT NULL,
    memory_type memory_type DEFAULT 'fact',
    key VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,

    -- Vector embedding pour recherche sémantique
    embedding vector(1536),  -- OpenAI text-embedding-3-small

    -- Importance et accès
    importance FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche par similarité cosinus
CREATE INDEX idx_memories_embedding ON memory.memories
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Fonction de recherche sémantique
CREATE FUNCTION memory.search_similar_memories(
    query_embedding vector(1536),
    p_agent_id BIGINT,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
) RETURNS TABLE (
    memory_id BIGINT,
    key VARCHAR(200),
    value TEXT,
    similarity FLOAT
) AS $$
    SELECT id, key, value, 1 - (embedding <=> query_embedding) AS similarity
    FROM memory.memories
    WHERE agent_id = p_agent_id
        AND (1 - (embedding <=> query_embedding)) >= p_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT p_limit;
$$ LANGUAGE sql;
```

### Setup avec PicoPG

Le script `gathering.db.setup` utilise PicoPG pour créer la base de données complète :

```bash
# Configuration
cp .env.example .env
# Éditer .env avec vos credentials

# Setup complet (base + extensions + schémas + migrations)
python -m gathering.db.setup

# Avec paramètres explicites
python -m gathering.db.setup --host localhost --user postgres --password secret

# Reset complet (drop + recreate)
python -m gathering.db.setup --reset

# Créer la base seulement (sans migrations)
python -m gathering.db.setup --create-db-only
```

Le script fait automatiquement :

1. Connexion à PostgreSQL (depuis `.env` ou arguments)
2. Création de la base `gathering`
3. Installation des extensions (`uuid-ossp`, `vector`)
4. Création des 7 schémas
5. Application des migrations SQL
6. Affichage du résumé

### Connexion et Usage

```python
# Avec PicoPG (recommandé pour admin/exploration)
from picopg import Database

db = Database.from_env()
db.list_schemas()           # ['agent', 'circle', 'project', ...]
db.list_tables('agent')     # ['agents', 'personas', 'sessions']
db.table_info('agent.agents')
db.execute("SELECT * FROM agent.agents WHERE is_active = true")

# Avec SQLAlchemy (pour l'application)
from gathering.db import Database, Agent, Circle, Task, Memory

db = Database.from_env()
with db.session() as session:
    agent = Agent(
        name="Claude",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        competencies=["python", "architecture"],
    )
    session.add(agent)
    agents = session.query(Agent).filter(Agent.is_active == True).all()
```

### Migrations

Les migrations SQL sont dans `gathering/db/migrations/` :

| Migration | Contenu |
|-----------|---------|
| `001_init_schemas.sql` | Extensions (uuid-ossp, vector) + types enum |
| `002_agent_schema.sql` | `agent.agents`, `agent.personas`, `agent.sessions` |
| `003_circle_schema.sql` | `circle.circles`, `members`, `tasks`, `conflicts`, `events` |
| `004_project_schema.sql` | `project.projects`, `project.files` |
| `005_communication_schema.sql` | `communication.conversations`, `messages`, `chat_history` |
| `006_memory_schema.sql` | `memory.memories`, `knowledge_base` + fonctions RAG |
| `007_review_schema.sql` | `review.reviews`, `comments`, `quality_metrics` |
| `008_audit_schema.sql` | `audit.logs`, `escalations`, `security_events` |
| `009_cross_schema_fks.sql` | Foreign keys inter-schémas + vues dashboard |

Les migrations sont trackées dans `public.migrations` et ne sont appliquées qu'une fois.

### RAG Services (Phase 9)

Le module `gathering/rag/` fournit les services pour le Retrieval-Augmented Generation :

```
gathering/rag/
├── __init__.py          # Exports: EmbeddingService, VectorStore, MemoryManager
├── embeddings.py        # Service d'embeddings OpenAI
├── vectorstore.py       # Interface PostgreSQL + pgvector
└── memory_manager.py    # API haut niveau pour agents
```

#### EmbeddingService

```python
from gathering.rag import EmbeddingService, EmbeddingProvider

# Créer le service
embedder = EmbeddingService.from_env()  # Utilise OPENAI_API_KEY

# Générer un embedding (avec cache LRU)
embedding = await embedder.embed("User prefers dark mode")
# Returns: List[float] (1536 dimensions)

# Batch embedding (optimisé)
embeddings = await embedder.embed_batch([
    "Text 1",
    "Text 2",
])

# Stats du cache
stats = embedder.cache_stats()
# {'cache_size': 150, 'max_size': 1000, 'hit_rate': 0.85}
```

#### VectorStore

```python
from gathering.rag import VectorStore

# Créer le store
store = VectorStore.from_env()  # Utilise DATABASE_URL

# Ajouter une mémoire
memory_id = store.add_memory(
    agent_id=1,
    key="theme_pref",
    value="User prefers dark mode",
    embedding=embedding,
    memory_type="preference",
    importance=0.8,
)

# Recherche sémantique
results = store.search_memories(
    query_embedding=query_vector,
    agent_id=1,
    limit=5,
    threshold=0.7,  # Similarité minimum
)
# Returns: List[MemoryResult] avec id, key, value, similarity

# Knowledge base
kb_id = store.add_knowledge(
    title="API Usage Guide",
    content="How to use the REST API...",
    embedding=embedding,
    category="docs",
    is_global=True,
)

results = store.search_knowledge(
    query_embedding=query_vector,
    category="docs",
    limit=10,
)
```

#### MemoryManager (API haut niveau)

```python
from gathering.rag import MemoryManager

# Créer le manager (combine embedder + store)
memory = MemoryManager.from_env()

# Remember (génère l'embedding automatiquement)
await memory.remember(
    agent_id=1,
    content="User prefers dark mode",
    memory_type="preference",
    key="theme_pref",
    importance=0.8,
)

# Recall (recherche sémantique)
results = await memory.recall(
    agent_id=1,
    query="What are the user's preferences?",
    limit=5,
    threshold=0.7,
)

# Knowledge base
await memory.add_knowledge(
    title="API Guide",
    content="...",
    category="docs",
    is_global=True,
)

results = await memory.search_knowledge(
    query="How to use the API?",
    category="docs",
)

# Batch operations
ids = await memory.remember_batch(
    agent_id=1,
    memories=[
        {"content": "Fact 1", "memory_type": "fact"},
        {"content": "Fact 2", "importance": 0.9},
    ]
)

# Stats
stats = memory.get_stats(agent_id=1)
```

#### API Endpoints (memories router)

```
POST /memories/agents/{id}/remember       # Stocker une mémoire
POST /memories/agents/{id}/recall         # Recherche sémantique
DELETE /memories/agents/{id}/memories/{m} # Oublier (soft delete)
GET  /memories/agents/{id}/stats          # Statistiques mémoire
POST /memories/agents/{id}/remember/batch # Batch remember

POST /memories/knowledge                  # Ajouter knowledge
POST /memories/knowledge/search           # Recherche knowledge
```

#### Dashboard Knowledge Base UI

Page `/knowledge` dans le dashboard :

- Recherche sémantique dans la knowledge base
- Filtrage par catégorie (docs, best_practice, decision, faq)
- Affichage des scores de similarité
- Ajout de nouvelles entrées avec tags

### Types Enum

```sql
-- Task lifecycle
CREATE TYPE task_status AS ENUM (
    'pending', 'claimed', 'in_progress', 'review',
    'changes_requested', 'blocked', 'completed', 'cancelled'
);

CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical');

-- Review lifecycle
CREATE TYPE review_status AS ENUM (
    'pending', 'in_progress', 'approved', 'changes_requested', 'rejected'
);

CREATE TYPE review_type AS ENUM (
    'code', 'architecture', 'security', 'docs', 'quality', 'final'
);

-- Memory
CREATE TYPE memory_scope AS ENUM ('agent', 'circle', 'project', 'global');
CREATE TYPE memory_type AS ENUM (
    'fact', 'preference', 'context', 'decision', 'error', 'feedback', 'learning'
);

-- Status
CREATE TYPE circle_status AS ENUM ('stopped', 'starting', 'running', 'stopping');
CREATE TYPE conversation_status AS ENUM ('pending', 'active', 'completed', 'cancelled');
CREATE TYPE log_level AS ENUM ('debug', 'info', 'warning', 'error', 'critical');
```

---

## 5. Système de Skills

### Architecture

```
gathering/skills/
├── __init__.py              # Exports: BaseSkill, SkillResponse, SkillPermission, SkillRegistry
├── base.py                  # Classes de base
├── registry.py              # SkillRegistry (lazy-loading, 21 skills)
│
├── git/                     # Git version control
│   ├── __init__.py
│   └── repository.py        # GitSkill (13 tools)
│
├── test/                    # Test execution
│   ├── __init__.py
│   └── runner.py            # TestSkill (7 tools)
│
├── filesystem/              # File operations
│   ├── __init__.py
│   └── operations.py        # FileSystemSkill (10 tools)
│
├── web/                     # Web search & scraping
│   ├── __init__.py
│   ├── search.py            # WebSearchSkill (5 tools)
│   └── scraper.py           # WebScraperSkill (5 tools)
│
├── http/                    # HTTP client
│   ├── __init__.py
│   └── client.py            # HTTPSkill (8 tools)
│
├── code/                    # Code execution
│   ├── __init__.py
│   └── executor.py          # CodeExecutionSkill (8 tools)
│
├── analysis/                # Code analysis
│   ├── __init__.py
│   └── scanner.py           # CodeAnalysisSkill (8 tools)
│
├── shell/                   # Shell commands
│   ├── __init__.py
│   └── executor.py          # ShellSkill (6 tools)
│
├── database/                # SQL operations
│   ├── __init__.py
│   └── client.py            # DatabaseSkill (8 tools)
│
├── deploy/                  # CI/CD & deployment
│   ├── __init__.py
│   └── manager.py           # DeploySkill (10 tools)
│
├── docs/                    # Documentation
│   ├── __init__.py
│   └── generator.py         # DocsSkill (7 tools)
│
├── social/                  # Social media
│   ├── __init__.py
│   └── platforms.py         # SocialMediaSkill (16 tools)
│
├── ai/                      # AI & LLM operations
│   ├── __init__.py
│   └── models.py            # AISkill (11 tools)
│
├── email/                   # Email SMTP/IMAP
│   ├── __init__.py
│   └── client.py            # EmailSkill (10 tools)
│
├── cloud/                   # Multi-cloud (AWS/GCP/Azure)
│   ├── __init__.py
│   └── providers.py         # CloudSkill (10 tools)
│
├── monitoring/              # System monitoring
│   ├── __init__.py
│   └── observer.py          # MonitoringSkill (11 tools)
│
├── calendar/                # Google/Outlook Calendar
│   ├── __init__.py
│   └── scheduler.py         # CalendarSkill (8 tools)
│
├── image/                   # Image processing (Pillow)
│   ├── __init__.py
│   └── processor.py         # ImageSkill (11 tools)
│
├── pdf/                     # PDF read/generate
│   ├── __init__.py
│   └── handler.py           # PDFSkill (10 tools)
│
└── notifications/           # Webhooks & push
    ├── __init__.py
    └── sender.py            # NotificationsSkill (9 tools)
```

### SkillRegistry

```
┌─────────────────────────────────────────────────────────────────┐
│                       SkillRegistry                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ _builtin_skills: Dict[str, str]  (module paths)           │  │
│  │ _skill_classes: Dict[str, Type[BaseSkill]]  (loaded)      │  │
│  │ _instances: Dict[str, BaseSkill]  (cached instances)      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│    │  GitSkill    │ │  TestSkill   │ │ FileSystem   │  ...     │
│    │  (13 tools)  │ │  (7 tools)   │ │  (10 tools)  │          │
│    └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Utilisation

```python
from gathering.skills import SkillRegistry, SkillPermission

# Lister les skills disponibles (21 skills)
skills = SkillRegistry.list_skills()
# ['ai', 'analysis', 'calendar', 'cloud', 'code', 'database', 'deploy',
#  'docs', 'email', 'filesystem', 'git', 'http', 'image', 'monitoring',
#  'notifications', 'pdf', 'scraper', 'shell', 'social', 'test', 'web']

# Obtenir un skill (lazy-loaded)
git = SkillRegistry.get("git")

# Exécuter un outil
result = git.execute("git_status", {"path": "/project"})
print(result.success)  # True
print(result.data)     # {"branch": "main", "staged": [], ...}

# Obtenir tous les outils pour un LLM
tools = SkillRegistry.get_all_tools(
    skill_names=["git", "test"],
    permissions=[SkillPermission.GIT, SkillPermission.READ]
)

# Exécuter un outil par nom (auto-détection du skill)
result = SkillRegistry.execute_tool("git_status", {"path": "/project"})
```

### Skills Disponibles (21 skills, ~191 tools)

| Skill | Description | Tools | Permissions |
|-------|-------------|-------|-------------|
| **git** | Git version control | 13 | GIT, READ, WRITE |
| **test** | Test execution & coverage | 7 | READ, EXECUTE |
| **filesystem** | Secure file operations | 10 | READ, WRITE |
| **web** | Web search (Google, Wikipedia) | 5 | NETWORK |
| **scraper** | Web scraping & extraction | 5 | NETWORK |
| **http** | HTTP/REST client | 8 | NETWORK |
| **code** | Code execution (Python, JS) | 8 | EXECUTE |
| **analysis** | Linting, security scanning | 8 | READ, EXECUTE |
| **shell** | Shell command execution | 6 | EXECUTE |
| **database** | SQL operations | 8 | READ, WRITE, EXECUTE |
| **deploy** | CI/CD & deployment | 10 | DEPLOY, EXECUTE |
| **docs** | Documentation generation | 7 | READ, WRITE |
| **social** | Social media integrations | 16 | NETWORK |
| **ai** | LLM calls, embeddings, vision | 11 | NETWORK |
| **email** | SMTP/IMAP operations | 10 | NETWORK |
| **cloud** | AWS/GCP/Azure management | 10 | NETWORK |
| **monitoring** | Metrics, logs, health checks | 11 | READ |
| **calendar** | Google/Outlook calendars | 8 | NETWORK |
| **image** | Image processing (Pillow) | 11 | READ, WRITE |
| **pdf** | PDF read/generate | 10 | READ, WRITE |
| **notifications** | Webhooks, push, SMS | 9 | NETWORK |

### Détail des Tools par Skill

#### git (13 tools)
- `git_status`, `git_diff`, `git_log`, `git_add`, `git_commit`
- `git_push`, `git_pull`, `git_branch`, `git_clone`, `git_create_pr`
- `git_rebase`, `git_stash`, `git_cherry_pick`

#### test (7 tools)
- `test_run`, `test_coverage`, `test_discover`, `test_last_failed`
- `test_watch`, `test_analyze_failures`, `test_create`

#### filesystem (10 tools)
- `fs_read`, `fs_write`, `fs_list`, `fs_info`, `fs_mkdir`
- `fs_delete`, `fs_copy`, `fs_move`, `fs_search`, `fs_tree`

#### web (5 tools)
- `web_search`, `wikipedia_search`, `wikipedia_article`
- `fetch_url`, `news_search`

#### scraper (5 tools)
- `extract_links`, `extract_images`, `extract_metadata`
- `extract_structured`, `extract_tables`

#### http (8 tools)
- `http_get`, `http_post`, `http_put`, `http_patch`, `http_delete`
- `http_head`, `http_download`, `http_upload`

#### code (8 tools)
- `execute_python`, `execute_javascript`, `execute_shell`
- `execute_sql`, `validate_syntax`, `format_code`
- `execute_with_timeout`, `create_sandbox`

#### analysis (8 tools)
- `analysis_lint`, `analysis_security`, `analysis_complexity`
- `analysis_dependencies`, `analysis_type_check`, `analysis_dead_code`
- `analysis_duplicates`, `analysis_metrics`

#### shell (6 tools)
- `shell_execute`, `shell_pwd`, `shell_cd`
- `shell_env`, `shell_which`, `shell_background`

#### database (8 tools)
- `db_query`, `db_execute`, `db_schema`, `db_tables`
- `db_describe`, `db_explain`, `db_migrate`, `db_backup`

#### deploy (10 tools)
- `deploy_docker_build`, `deploy_docker_push`, `deploy_docker_run`
- `deploy_docker_compose`, `deploy_status`, `deploy_health_check`
- `deploy_rollback`, `deploy_env_config`, `deploy_ci_trigger`, `deploy_logs`

#### docs (7 tools)
- `docs_analyze`, `docs_generate_docstring`, `docs_generate_readme`
- `docs_extract`, `docs_generate_api`, `docs_lint`, `docs_changelog`

#### social (16 tools)
- Twitter: `post_tweet`, `get_mentions`, `search_tweets`
- Reddit: `post_reddit`, `get_subreddit`
- GitHub: `github_issue`, `github_pr`, `github_search`
- Discord: `discord_send`, `discord_read`
- Slack: `slack_send`, `slack_read`
- Mastodon: `mastodon_post`, `mastodon_timeline`
- LinkedIn: `linkedin_post`, `linkedin_profile`

#### ai (11 tools)
- `ai_complete`, `ai_chat`, `ai_embed`, `ai_vision`, `ai_transcribe`
- `ai_speak`, `ai_summarize`, `ai_translate`, `ai_extract`
- `ai_compare`, `ai_models`
- **Providers**: OpenAI, Anthropic, DeepSeek, Ollama, Groq

#### email (10 tools)
- `email_send`, `email_read`, `email_search`, `email_get`, `email_folders`
- `email_move`, `email_delete`, `email_mark`, `email_reply`, `email_draft`
- **Providers**: Gmail, Outlook, Yahoo, ProtonMail (SMTP/IMAP)

#### cloud (10 tools)
- `cloud_list_instances`, `cloud_get_instance`, `cloud_start_instance`
- `cloud_stop_instance`, `cloud_list_buckets`, `cloud_list_objects`
- `cloud_upload`, `cloud_download`, `cloud_delete_object`, `cloud_providers`
- **Providers**: AWS (EC2, S3), GCP (Compute, Storage), Azure (VMs, Blob)

#### monitoring (11 tools)
- `monitor_system`, `monitor_process`, `monitor_logs`, `monitor_log_stats`
- `monitor_record`, `monitor_get_metrics`, `monitor_health_check`
- `monitor_set_alert`, `monitor_check_alerts`, `monitor_disk`, `monitor_network`

#### calendar (8 tools)
- `calendar_list`, `calendar_events`, `calendar_get_event`, `calendar_create_event`
- `calendar_update_event`, `calendar_delete_event`, `calendar_free_slots`, `calendar_today`
- **Providers**: Google Calendar, Outlook/Microsoft 365

#### image (11 tools)
- `image_info`, `image_resize`, `image_crop`, `image_rotate`, `image_convert`
- `image_filter`, `image_adjust`, `image_thumbnail`, `image_watermark`
- `image_compose`, `image_to_base64`
- **Library**: Pillow

#### pdf (10 tools)
- `pdf_read`, `pdf_info`, `pdf_create`, `pdf_merge`, `pdf_split`
- `pdf_watermark`, `pdf_to_images`, `pdf_from_images`, `pdf_extract_images`, `pdf_search`
- **Libraries**: pypdf, reportlab, pdf2image

#### notifications (9 tools)
- `notify_webhook`, `notify_slack`, `notify_discord`, `notify_teams`
- `notify_push_firebase`, `notify_push_onesignal`, `notify_sms`
- `notify_desktop`, `notify_batch`
- **Integrations**: Slack, Discord, Teams, Firebase, OneSignal, Twilio

### Créer un Skill Custom

```python
from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

class MyCustomSkill(BaseSkill):
    name = "custom"
    description = "My custom skill"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ]

    def get_tools_definition(self):
        return [{
            "name": "my_tool",
            "description": "Does something useful",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param": {"type": "string", "description": "Input parameter"}
                },
                "required": ["param"]
            }
        }]

    def execute(self, tool_name: str, tool_input: dict) -> SkillResponse:
        if tool_name == "my_tool":
            return SkillResponse(
                success=True,
                message="Done!",
                data={"result": tool_input["param"].upper()}
            )
        return SkillResponse(success=False, message="Unknown tool", error="unknown_tool")

# Enregistrer le skill
from gathering.skills import SkillRegistry
SkillRegistry.register("custom", MyCustomSkill)
```

### Sécurité des Skills

Chaque skill implémente des contrôles de sécurité :

| Skill | Mesures de Sécurité |
|-------|---------------------|
| **filesystem** | Sandboxing, forbidden paths (/etc, /proc), allowed_paths config |
| **shell** | Command whitelist, timeout, no shell injection |
| **code** | Sandboxed execution, timeout, memory limits |
| **database** | Parameterized queries, SQL injection prevention, read-only mode |
| **deploy** | Confirmation for destructive ops, registry whitelist |
| **analysis** | No code execution, pattern-based scanning |

```python
# Exemple: FileSystemSkill avec sandboxing
fs = SkillRegistry.get("filesystem", config={
    "sandbox_mode": True,
    "allowed_paths": ["/home/user/projects"],
    "working_dir": "/home/user/projects/myapp"
})

# Tentative d'accès interdit → PermissionError
result = fs.execute("fs_read", {"path": "/etc/passwd"})
# result.success = False, result.error = "Access denied"
```

---

## 5. LLM Providers

### Providers Supportés

| Provider | Modèles | Use Case |
|----------|---------|----------|
| **Anthropic** | Claude 3 Opus, Sonnet, Haiku | Architecture, raisonnement |
| **DeepSeek** | deepseek-chat, deepseek-coder | Code, coût réduit |
| **OpenAI** | GPT-4, GPT-4-turbo | Polyvalent |
| **Ollama** | Llama, Mistral, etc. | Local, offline |

### Configuration

```python
from gathering.llm import LLMProviderFactory

# Créer un provider
claude = LLMProviderFactory.create("anthropic", {
    "model": "claude-3-opus-20240229",
    "api_key": os.environ["ANTHROPIC_API_KEY"],
    "temperature": 0.7,
    "rate_limit_per_minute": 50,
    "enable_cache": True,
})

deepseek = LLMProviderFactory.create("deepseek", {
    "model": "deepseek-coder",
    "api_key": os.environ["DEEPSEEK_API_KEY"],
})

# Completion
response = claude.complete([
    {"role": "user", "content": "Explain this code..."}
])

# Streaming
async for chunk in claude.stream(messages):
    print(chunk, end="")

# Avec tools
response = claude.complete(messages, tools=[
    {"name": "git_status", "description": "...", "input_schema": {...}}
])
```

### Features

- **Rate Limiting** : Token bucket intégré
- **Caching LRU** : Cache des réponses identiques
- **Retry Logic** : Retry automatique sur erreurs transitoires
- **Token Counting** : tiktoken pour OpenAI/DeepSeek

---

## 6. Système de Review

### Workflow

```
┌──────────────┐
│ Agent A      │
│ complète     │
│ une tâche    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ Task status: │────►│ Review créée │
│ REVIEW       │     │ status: PENDING
└──────────────┘     └──────┬───────┘
                            │
                            ▼
                   ┌──────────────┐
                   │ Agent B      │
                   │ (Reviewer)   │
                   └──────┬───────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    ┌─────────┐     ┌──────────┐    ┌──────────┐
    │APPROVED │     │ CHANGES  │    │ REJECTED │
    └────┬────┘     │ REQUESTED│    └────┬─────┘
         │          └────┬─────┘         │
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ Task:   │    │ Task:    │    │Escalation│
    │COMPLETED│    │IN_PROGRESS    │ créée    │
    └─────────┘    │(iteration++)  └──────────┘
                   └──────────┘
```

### Types de Review

| Type | Description | Critères |
|------|-------------|----------|
| `code` | Review de code | Style, bugs, performance |
| `architecture` | Review d'architecture | Design patterns, scalabilité |
| `security` | Audit sécurité | Vulnérabilités, OWASP |
| `docs` | Review documentation | Clarté, exhaustivité |
| `quality` | Review qualité générale | Tests, maintenabilité |
| `final` | Approbation finale | Prêt pour merge/deploy |

### Scores et Métriques

```python
# Scores de review (0-100)
review.scores = {
    "code_quality": 85,
    "test_coverage": 70,
    "documentation": 60,
    "security": 90,
}
review.overall_score = 76  # Moyenne pondérée

# Métriques agent (mises à jour après review)
agent.tasks_completed += 1
agent.approval_rate = approved_first_try / total_reviews
agent.average_quality_score = running_average(scores)
```

---

## 7. API et Interface Web

### Endpoints REST (Prévu)

```
/api/v1/
├── /agents
│   ├── GET    /              # Liste des agents
│   ├── POST   /              # Créer un agent
│   ├── GET    /:id           # Détails agent
│   └── PUT    /:id           # Modifier agent
│
├── /teams
│   ├── GET    /              # Liste des équipes
│   ├── POST   /              # Créer une équipe
│   ├── GET    /:id/members   # Membres de l'équipe
│   └── POST   /:id/members   # Ajouter un membre
│
├── /projects
│   ├── GET    /              # Liste des projets
│   ├── POST   /              # Créer un projet
│   └── GET    /:id/tasks     # Tâches du projet
│
├── /tasks
│   ├── GET    /              # Task board
│   ├── POST   /              # Créer une tâche
│   ├── POST   /:id/claim     # Claim une tâche
│   ├── POST   /:id/submit    # Soumettre pour review
│   └── GET    /:id/reviews   # Reviews de la tâche
│
├── /conversations
│   ├── GET    /              # Conversations
│   ├── POST   /:id/messages  # Envoyer message
│   └── GET    /:id/messages/stream  # SSE streaming
│
└── /reviews
    ├── POST   /:id/approve   # Approuver
    ├── POST   /:id/request-changes
    └── POST   /:id/reject
```

### Interface Web (Prévu)

```
┌─────────────────────────────────────────────────────────────────┐
│  GatheRing Dashboard                              [User] [⚙️]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────────────────────────────────┐  │
│  │ Teams       │  │ Task Board                              │  │
│  │             │  │ ┌─────────┬─────────┬─────────────────┐ │  │
│  │ > Alpha     │  │ │ PENDING │IN PROG  │ REVIEW          │ │  │
│  │   Beta      │  │ │         │         │                 │ │  │
│  │             │  │ │ [Task1] │ [Task3] │ [Task5]         │ │  │
│  ├─────────────┤  │ │ [Task2] │ [Task4] │                 │ │  │
│  │ Agents      │  │ │         │         │                 │ │  │
│  │             │  │ └─────────┴─────────┴─────────────────┘ │  │
│  │ 🟢 Claude   │  └─────────────────────────────────────────┘  │
│  │ 🟢 DeepSeek │                                               │
│  │ ⚪ GPT-4    │  ┌─────────────────────────────────────────┐  │
│  │             │  │ Conversation                            │  │
│  ├─────────────┤  │                                         │  │
│  │ Projects    │  │ [Claude]: J'ai terminé la feature X...  │  │
│  │             │  │ [DeepSeek]: @Claude je review ça        │  │
│  │ > Gathering │  │ [User]: Merci, continuez sur Y          │  │
│  │   Other     │  │                                         │  │
│  │             │  │ [___________________________] [Send]    │  │
│  └─────────────┘  └─────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Annexes

### A. Variables d'Environnement

```bash
# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/gathering

# Application
GATHERING_ENV=development
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=...
```

### B. Commandes Utiles

```bash
# Initialiser la base de données
python -c "from gathering.db import init_db; init_db()"

# Lancer les tests
pytest tests/ -v

# Lancer l'API (prévu)
uvicorn gathering.api:app --reload
```

### C. Roadmap

- [x] Phase 1-3: Core, Security, LLM Providers
- [x] Phase 4: DB Models, Skills (Git, Test), DeepSeek Provider
- [x] Phase 5a: Team Orchestration (Gathering Circle, Facilitator, Events)
- [x] Phase 5b: Agent Persistence (Persona, Memory, Session, Resume)
- [x] Phase 5c: Agent-to-Agent Communication (conversations directes, collaboration)
- [x] Phase 6: FastAPI REST API
- [x] Phase 7: React Dashboard
- [x] Phase 8: RAG avec pgvector (multi-schema, migrations, vector search)
- [x] Phase 9: RAG Services
  - [x] Embedding Service (OpenAI text-embedding-3-small)
  - [x] VectorStore interface Python
  - [x] Tests module RAG (22 tests)
  - [x] Endpoints API memories/RAG
  - [x] Dashboard Knowledge Base UI

---

## 5. REST API ✅ IMPLÉMENTÉ

### Vue d'Ensemble

API REST complète construite avec FastAPI pour exposer toutes les fonctionnalités de GatheRing.

```
gathering/api/
├── __init__.py          # Module principal, create_app()
├── main.py              # Application FastAPI
├── schemas.py           # Schémas Pydantic
├── dependencies.py      # Injection de dépendances
├── websocket.py         # Support WebSocket
└── routers/
    ├── __init__.py
    ├── health.py        # /health endpoints
    ├── agents.py        # /agents endpoints
    ├── circles.py       # /circles endpoints
    └── conversations.py # /conversations endpoints
```

### Démarrage Rapide

```bash
# Installer les dépendances
pip install fastapi uvicorn

# Lancer l'API
uvicorn gathering.api:app --reload

# Documentation interactive
open http://localhost:8000/docs
```

### Endpoints Disponibles

#### Health Check

```
GET  /health          # Status, version, uptime
GET  /health/ready    # Readiness probe (K8s)
GET  /health/live     # Liveness probe (K8s)
```

#### Agents

```
GET    /agents              # Liste tous les agents
POST   /agents              # Créer un agent
GET    /agents/{id}         # Détails d'un agent
PATCH  /agents/{id}         # Modifier un agent
DELETE /agents/{id}         # Supprimer un agent
POST   /agents/{id}/chat    # Chatter avec un agent
GET    /agents/{id}/status  # Status et session
POST   /agents/{id}/memories           # Créer une mémoire
POST   /agents/{id}/memories/recall    # Rappeler des mémoires
```

#### Circles (Orchestration)

```
GET    /circles               # Liste tous les circles
POST   /circles               # Créer un circle
GET    /circles/{name}        # Détails d'un circle
DELETE /circles/{name}        # Supprimer un circle
POST   /circles/{name}/start  # Démarrer un circle
POST   /circles/{name}/stop   # Arrêter un circle
POST   /circles/{name}/agents # Ajouter un agent
DELETE /circles/{name}/agents/{id}  # Retirer un agent
GET    /circles/{name}/tasks  # Liste les tâches
POST   /circles/{name}/tasks  # Créer une tâche
GET    /circles/{name}/tasks/{id}   # Détails d'une tâche
POST   /circles/{name}/tasks/{id}/submit  # Soumettre résultat
POST   /circles/{name}/tasks/{id}/approve # Approuver
POST   /circles/{name}/tasks/{id}/reject  # Rejeter
GET    /circles/{name}/conflicts  # Conflits actifs
GET    /circles/{name}/metrics    # Métriques
```

#### Conversations

```
GET    /conversations              # Liste les conversations
POST   /conversations              # Créer une conversation
GET    /conversations/{id}         # Détails
POST   /conversations/{id}/start   # Démarrer
POST   /conversations/{id}/cancel  # Annuler
DELETE /conversations/{id}         # Supprimer
GET    /conversations/{id}/transcript  # Transcript
POST   /conversations/quick        # Créer et démarrer en une fois
```

#### WebSocket

```
WS /ws  # Connexion WebSocket pour événements temps réel
```

### Exemple d'Utilisation

```python
import httpx

# Créer un circle
response = httpx.post("http://localhost:8000/circles", json={
    "name": "dev-team",
    "require_review": True,
    "auto_route": True,
})
circle = response.json()

# Ajouter des agents
httpx.post("http://localhost:8000/circles/dev-team/agents", params={
    "agent_id": 1,
    "agent_name": "Claude",
    "provider": "anthropic",
    "competencies": "python,architecture",
    "can_review": "code",
})

# Démarrer le circle
httpx.post("http://localhost:8000/circles/dev-team/start")

# Créer une tâche
response = httpx.post("http://localhost:8000/circles/dev-team/tasks", json={
    "title": "Implement auth",
    "description": "Add JWT authentication",
    "required_competencies": ["python", "security"],
    "priority": 3,
})
task = response.json()

# Lancer une conversation entre agents
response = httpx.post("http://localhost:8000/conversations/quick",
    params={"circle_name": "dev-team"},
    json={
        "topic": "Review architecture decisions",
        "agent_ids": [1, 2],
        "max_turns": 8,
    }
)
conversation = response.json()
print(conversation["transcript"])
```

### WebSocket Events

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
    // S'abonner aux événements
    ws.send(JSON.stringify({
        action: "subscribe",
        topics: ["agents", "circles:dev-team", "tasks"]
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Types: agent.chat, task.created, task.completed,
    //        circle.started, conversation.message, etc.
    console.log(data.type, data.data);
};
```

### Tests

```bash
# Lancer les tests API
pytest tests/test_api.py -v

# 37 tests couvrant:
# - Health endpoints (4 tests)`
# - Agent CRUD + chat (8 tests)
# - Circle orchestration (8 tests)
# - Task management (4 tests)
# - Conversations (7 tests)
# - WebSocket manager (2 tests)
# - Integration workflow (1 test)
```

**Total: 183 tests passent (incluant les tests existants)**

---

## 6. React Dashboard ✅ IMPLÉMENTÉ

### Vue d'Ensemble

Dashboard React moderne pour gérer GatheRing via l'interface web.

```
dashboard/
├── src/
│   ├── App.tsx                 # Application principale avec routing
│   ├── index.css               # Styles Tailwind + thème personnalisé
│   ├── components/
│   │   └── Layout.tsx          # Layout avec sidebar navigation
│   ├── pages/
│   │   ├── Dashboard.tsx       # Vue d'ensemble (stats, activité)
│   │   ├── Agents.tsx          # Gestion agents + chat
│   │   ├── Circles.tsx         # Orchestration + tâches
│   │   └── Conversations.tsx   # Conversations inter-agents
│   ├── services/
│   │   └── api.ts              # Couche API (fetch wrapper)
│   ├── hooks/
│   │   └── useWebSocket.ts     # Hook WebSocket temps réel
│   └── types/
│       └── index.ts            # Types TypeScript
├── vite.config.ts              # Config Vite + proxy API
├── tailwind.config.js          # Config Tailwind
└── package.json                # Dépendances
```

### Stack Technique

| Technologie | Version | Usage |
|-------------|---------|-------|
| **React** | 19.2 | UI Framework |
| **TypeScript** | 5.9 | Type Safety |
| **Vite** | 7.2 | Build Tool |
| **Tailwind CSS** | 4.1 | Styling |
| **React Router** | 7.11 | Navigation |
| **TanStack Query** | 5.90 | Data Fetching |
| **Lucide React** | 0.562 | Icons |

### Démarrage

```bash
cd dashboard

# Installation
npm install

# Développement (port 3000, proxy vers API 8000)
npm run dev

# Build production
npm run build
```

### Pages

#### Dashboard (/)

Vue d'ensemble avec:

- Statistiques: Agents, Circles actifs, Conversations, Tâches
- Panel Agents: 5 derniers avec status
- Panel Circles: 5 derniers avec activité
- System info: Uptime, version, status

#### Agents (/agents)

Gestion complète des agents:

- Liste avec status (idle/busy), mémoires, messages
- Interface chat temps réel
- Création d'agent avancée avec deux modes:
  - **Mode Persona**: Sélectionner une persona existante
  - **Mode Custom**: Créer un agent personnalisé avec tous les champs
- Formulaire complet: nom, rôle, base prompt, traits, spécialisations, style de communication, langues, motto
- Configuration modèle: provider, modèle, température (slider 0-1), max tokens
- Suppression d'agent

#### Models (/models) 🆕

Gestion des providers LLM et modèles:

- **Statistiques**: Total providers, modèles, avec thinking, avec vision
- **Provider Cards**: Liste des providers avec expansion pour voir les modèles
- **Model Tables**: Détails par modèle (alias, pricing in/out, context, capabilities)
- **Add Provider**: Modal pour ajouter un nouveau provider (nom, URL API, local/cloud)
- **Add Model**: Modal complet pour ajouter un modèle:
  - Provider, nom, alias
  - Pricing (input/output $/1M tokens)
  - Context window, max output
  - Capacités: extended thinking, vision, deprecated

#### Circles (/circles)

Orchestration multi-agents:

- Liste des circles avec status (running/stopped)
- Démarrage/arrêt des circles
- Gestion des tâches (création, liste, status)
- Métriques: completed, in_progress, conflicts, uptime
- Priorités: low, medium, high, critical

#### Conversations (/conversations)

Collaboration inter-agents:

- Liste des conversations avec participants
- Messages en temps réel
- Bouton "Advance" pour faire avancer la conversation
- Prompt optionnel pour guider

#### Activity Feed (/activity) 🆕 v0.16

Flux d'activité en temps réel:

- **WebSocket temps réel**: Mise à jour live des événements
- **Toggle Live/Pause**: Activer/désactiver les mises à jour
- **Filtres par catégorie**: Tâches, Reviews, Goals, Agents, Conflits
- **Événements supportés**:
  - `task_created`, `task_started`, `task_completed`, `task_failed`
  - `review_requested`, `review_approved`, `review_rejected`
  - `agent_joined`, `agent_left`
  - `goal_completed`, `goal_started`
  - `conflict_detected`, `conflict_resolved`
  - `scheduled_triggered`, `system_event`
- **Métadonnées enrichies**: Fichiers modifiés, durée, priorité
- **Stats rapides**: Tâches complétées, reviews en attente, conflits

#### Board (/board) 🆕 v0.16

Vue Kanban pour la gestion des tâches:

- **4 colonnes**: Backlog, In Progress, In Review, Done
- **Drag & Drop natif HTML5**: Déplacer les tâches entre colonnes
- **Filtres combinables**: Par projet, assigné, priorité
- **Task Cards avec**:
  - Titre et description
  - Priorité (critical, high, medium, low)
  - Assigné (agent ou user)
  - Tags
  - Date d'échéance avec alerte
- **Menu contextuel**: Start, Submit for Review, Complete
- **Stats en header**: Total, en cours, complétées

#### Pipelines (/pipelines) 🆕 v0.16

Workflows automatisés multi-agents:

- **Vue liste**: Cards avec preview du flow, stats d'exécution
- **Statuts**: Active, Paused, Draft
- **Types de nodes**:
  - `trigger`: Déclencheur (webhook, schedule, event, manual)
  - `agent`: Exécution par un agent
  - `condition`: Branchement conditionnel
  - `action`: Action automatique (email, notification, API)
  - `parallel`: Exécution parallèle
  - `delay`: Attente temporisée
- **Modal de détail** avec 3 onglets:
  - **Overview**: Stats, configuration des nodes
  - **Runs**: Historique des exécutions avec durée et statut
  - **Logs**: Logs détaillés avec niveaux (info, warn, error)
- **Actions**: Run Now, Pause/Resume, Edit, Delete

#### Monitoring (/monitoring) 🆕 v0.16

Supervision système:

- **Métriques temps réel**:
  - CPU (%, cores, fréquence)
  - Mémoire (utilisée/totale, %)
  - Disque (utilisé/total, %)
  - Load Average (1min, 5min, 15min)
- **Barres de progression colorées**: Vert (<50%), Jaune (50-70%), Orange (70-90%), Rouge (>90%)
- **Health Checks**: API Server, Database, Redis, LLM Provider, Memory, Disk
- **Alertes avec acknowledge**: Info, Warning, Critical
- **Auto-refresh**: Toggle avec intervalle 5s
- **System Info**: Cores, fréquence, mémoire/disque libres

### Navigation Réorganisée 🆕 v0.16

Le menu latéral utilise maintenant des groupes dépliables:

```text
├── Overview (ouvert par défaut)
│   ├── Dashboard
│   └── Activity Feed
├── Work (ouvert par défaut)
│   ├── Board
│   ├── Projects
│   ├── Goals
│   ├── Pipelines
│   ├── Background Tasks
│   └── Schedules
├── Agents & Teams (ouvert par défaut)
│   ├── Agents
│   ├── Circles
│   └── Conversations
├── Intelligence (fermé par défaut)
│   ├── Knowledge Base
│   └── Models
└── System (fermé par défaut)
    ├── Monitoring
    └── Settings
```

### API Service Layer

```typescript
// services/api.ts
import { agents, circles, conversations, health, providers, models, personas } from './services/api';

// Health
await health.check();

// Agents (lecture depuis PostgreSQL via /agents-db)
const { agents } = await agents.list();
const agent = await agents.get(1);
const response = await agents.chat(1, "Hello");
await agents.create({ persona: { name, role }, config: { provider } });

// Providers & Models (lecture depuis PostgreSQL)
const { providers } = await providers.list();
const { models } = await models.list(providerId);
const { personas } = await personas.list();

// Circles
const { circles } = await circles.list();
await circles.start("my-circle");
await circles.createTask("my-circle", { title, priority: "high" });
const metrics = await circles.getMetrics("my-circle");

// Conversations
const { conversations } = await conversations.list();
await conversations.advance(id, "Optional prompt");
const messages = await conversations.getMessages(id);
```

### WebSocket Hook

```typescript
import { useWebSocket } from './hooks/useWebSocket';

function MyComponent() {
  const { isConnected, lastEvent, subscribe } = useWebSocket({
    topics: ['agents', 'circles:dev-team'],
    onMessage: (event) => {
      console.log(event.type, event.data);
    },
  });

  // Auto-reconnect intégré
  // Subscription par topics
}
```

### Features UI

- **Dark Mode**: Support complet via Tailwind classes
- **Responsive**: Grid adaptatif (1/2/4 colonnes)
- **Real-time**: Polling + WebSocket ready
- **Loading States**: Skeletons et spinners
- **Empty States**: Messages informatifs
- **Modals**: Création agents, circles, conversations
- **Status Badges**: Couleurs par état

### Proxy Configuration

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    },
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
    }
  }
}
```

### Types Principaux

```typescript
// Agent
interface Agent {
  id: number;
  name: string;
  role: string;
  provider: string;
  model: string;
  status: 'idle' | 'busy' | 'offline';
  competencies: string[];
  memory_count?: number;
  message_count?: number;
}

// Circle
interface Circle {
  id: string;
  name: string;
  status: 'stopped' | 'starting' | 'running' | 'stopping';
  agent_count: number;
  active_tasks: number;
}

// Task
interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_agent_id: number | null;
}

// Conversation
interface Conversation {
  id: string;
  topic: string;
  status: 'pending' | 'active' | 'completed' | 'cancelled';
  participant_names: string[];
  turns_taken: number;
}

// Provider & Model (connexion PostgreSQL)
interface Provider {
  id: number;
  name: string;
  api_base_url: string | null;
  is_local: boolean;
  model_count?: number;
}

interface Model {
  id: number;
  provider_id: number;
  provider_name?: string;
  model_name: string;
  model_alias: string | null;
  pricing_in: number | null;
  pricing_out: number | null;
  extended_thinking: boolean;
  vision: boolean;
  context_window: number | null;
}
```

### Connexion API-PostgreSQL

L'API utilise `DatabaseService` (via picopg) pour lire les données depuis PostgreSQL :

```python
# gathering/api/dependencies.py
class DatabaseService:
    """Service de connexion PostgreSQL via picopg."""

    def get_agents(self) -> List[Dict]:
        """Lecture depuis la vue agent_dashboard."""
        return self.execute("SELECT * FROM public.agent_dashboard")

    def get_providers(self) -> List[Dict]:
        """Liste providers avec count modèles."""
        return self.execute("""
            SELECT p.*, COUNT(m.id) as model_count
            FROM agent.providers p
            LEFT JOIN agent.models m ON m.provider_id = p.id
            GROUP BY p.id
        """)

    def get_models(self, provider_id=None) -> List[Dict]:
        """Liste modèles avec filtrage par provider."""
        ...
```

**Endpoints PostgreSQL disponibles :**

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/agents-db` | GET | Liste agents depuis `agent_dashboard` view |
| `/agents-db/{id}` | GET | Détail agent |
| `/providers` | GET/POST/DELETE | CRUD providers |
| `/models` | GET/POST/PATCH/DELETE | CRUD models |
| `/personas` | GET/POST/PATCH/DELETE | CRUD personas |

---

## 9. Phases Futures

### Phase 10: Agent Autonomy (Prochaine)

L'objectif est de rendre les agents capables d'agir de manière autonome avec des objectifs à long terme.

#### 10.1 Persona-Agent Relationship (Migration 010 + 011)

Le schéma agent a été entièrement normalisé avec deux migrations:

- **Migration 010**: Ajoute `persona_id` FK sur `agents`, insère Sophie & Olivia
- **Migration 011**: Crée `providers` et `models`, supprime les colonnes redondantes

```sql
-- Structure normalisée (voir section 4 - Schéma Agent Normalisé)
agent.providers → agent.models → agent.personas → agent.agents
```

**Personas pré-définies avec full_prompt complet:**

| Persona           | Rôle                         | Default Model | Spécialisations                          |
|-------------------|------------------------------|---------------|------------------------------------------|
| `Dr. Sophie Chen` | Principal Software Architect | Sonnet 4.5    | Python, PostgreSQL, distributed-systems  |
| `Olivia Nakamoto` | Senior Systems Engineer      | Opus 4.5      | Rust, Solana, performance, low-latency   |

Les `full_prompt` contiennent le contenu complet des fichiers persona (markdown), pas juste un résumé.

**Relation agents → personas:**

```python
# Agent hérite tout de sa persona via FK
# Plus de colonnes provider/model/persona/traits sur agents
agent.model_id → models → providers
agent.persona_id → personas (full_prompt, traits, specializations, etc.)
```

#### 10.2 Background Task Execution ✅ IMPLÉMENTÉ

Agents capables d'exécuter des tâches en arrière-plan sans intervention humaine.

**Fichiers créés/modifiés:**

| Fichier | Description |
|---------|-------------|
| `gathering/db/migrations/012_background_tasks.sql` | Tables `background_tasks` et `background_task_steps` |
| `gathering/orchestration/background.py` | `BackgroundTask`, `BackgroundTaskRunner`, `BackgroundTaskExecutor` |
| `gathering/api/routers/background_tasks.py` | API REST pour gestion des tâches |
| `dashboard/src/pages/BackgroundTasks.tsx` | Interface de monitoring |

**Architecture:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND TASK EXECUTION                         │
│                                                                      │
│  ┌──────────────────────┐      ┌──────────────────────────────────┐ │
│  │ BackgroundTaskExecutor│      │ PostgreSQL                       │ │
│  │  (Singleton)          │      │ ┌──────────────────────────────┐ │ │
│  │                       │      │ │ circle.background_tasks      │ │ │
│  │  • start_task()       │─────►│ │  id, agent_id, goal, status  │ │ │
│  │  • pause_task()       │      │ │  progress, checkpoint, result │ │ │
│  │  • resume_task()      │      │ └──────────────────────────────┘ │ │
│  │  • cancel_task()      │      │ ┌──────────────────────────────┐ │ │
│  │  • recover_tasks()    │      │ │ circle.background_task_steps │ │ │
│  │                       │      │ │  task_id, step_number, action │ │ │
│  └───────────┬───────────┘      │ │  tool_name, tokens, duration  │ │ │
│              │                   │ └──────────────────────────────┘ │ │
│              ▼                   └──────────────────────────────────┘ │
│  ┌──────────────────────┐                                             │
│  │ BackgroundTaskRunner │  For each task                             │
│  │                       │                                            │
│  │  Loop:               │                                            │
│  │  1. recall()   ──────┼───► Agent Memory                           │
│  │  2. plan()     ──────┼───► LLM: "What's next?"                    │
│  │  3. execute()  ──────┼───► LLM + Tools                            │
│  │  4. remember() ──────┼───► Store progress                         │
│  │  5. checkpoint()─────┼───► Save state                             │
│  │  6. is_complete()────┼───► LLM: "Done?" or [COMPLETE]             │
│  └──────────────────────┘                                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Schéma SQL:**

```sql
-- Migration 012_background_tasks.sql
CREATE TYPE public.background_task_status AS ENUM (
    'pending', 'running', 'paused', 'completed', 'failed', 'cancelled', 'timeout'
);

CREATE TABLE circle.background_tasks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id),
    circle_id BIGINT REFERENCES circle.circles(id),  -- Optionnel
    goal TEXT NOT NULL,
    status background_task_status DEFAULT 'pending',

    -- Limites d'exécution
    max_steps INTEGER DEFAULT 50,
    timeout_seconds INTEGER DEFAULT 3600,
    checkpoint_interval INTEGER DEFAULT 5,

    -- Progression
    current_step INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    progress_summary TEXT,
    checkpoint_data JSONB,

    -- Résultats
    final_result TEXT,
    error_message TEXT,

    -- Métriques
    total_llm_calls INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    total_tool_calls INTEGER DEFAULT 0
);

CREATE TABLE circle.background_task_steps (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT REFERENCES circle.background_tasks(id),
    step_number INTEGER NOT NULL,
    action_type VARCHAR(50),  -- plan, execute, tool_call, checkpoint
    action_input TEXT,
    action_output TEXT,
    tool_name VARCHAR(100),
    duration_ms INTEGER
);

-- Vue dashboard
CREATE VIEW public.background_tasks_dashboard AS
SELECT bt.*, a.name as agent_name, p.display_name, c.name as circle_name
FROM circle.background_tasks bt
JOIN agent.agents a ON a.id = bt.agent_id
LEFT JOIN agent.personas p ON p.id = a.persona_id
LEFT JOIN circle.circles c ON c.id = bt.circle_id;
```

**Utilisation Python:**

```python
from gathering.orchestration import BackgroundTaskExecutor, get_background_executor
from gathering.agents import AgentWrapper

# Obtenir l'executor singleton
executor = get_background_executor(db_service=db)

# Démarrer une tâche
task_id = await executor.start_task(
    agent=my_agent,
    goal="Analyse le codebase et génère un rapport de qualité",
    max_steps=30,
    timeout_seconds=1800,  # 30 minutes
    checkpoint_interval=5,
)

# Contrôle
await executor.pause_task(task_id)
await executor.resume_task(task_id, my_agent)
await executor.cancel_task(task_id)

# Status
task = await executor.get_status(task_id)
print(f"Progress: {task.progress_percent}%")
print(f"Step: {task.current_step}/{task.max_steps}")
```

**API Endpoints:**

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/background-tasks` | GET | Liste toutes les tâches (filtres: status, agent_id) |
| `/background-tasks` | POST | Créer et démarrer une tâche |
| `/background-tasks/{id}` | GET | Détails d'une tâche |
| `/background-tasks/{id}/pause` | POST | Mettre en pause |
| `/background-tasks/{id}/resume` | POST | Reprendre |
| `/background-tasks/{id}/cancel` | POST | Annuler |
| `/background-tasks/{id}/steps` | GET | Historique des étapes |
| `/background-tasks/{id}` | DELETE | Supprimer (si terminée) |

**Dashboard UI:**

La page `/tasks` affiche:
- Compteurs par status (pending, running, paused, completed, failed, cancelled, timeout)
- Liste des tâches avec barre de progression
- Détail expandable avec historique des steps
- Boutons: Pause, Resume, Cancel, Delete
- Formulaire de création: sélection agent + goal + max_steps

**Événements:**

```python
# Nouveaux EventTypes dans events.py
BACKGROUND_TASK_CREATED = "background_task.created"
BACKGROUND_TASK_STARTED = "background_task.started"
BACKGROUND_TASK_STEP = "background_task.step"
BACKGROUND_TASK_CHECKPOINT = "background_task.checkpoint"
BACKGROUND_TASK_COMPLETED = "background_task.completed"
BACKGROUND_TASK_FAILED = "background_task.failed"
BACKGROUND_TASK_CANCELLED = "background_task.cancelled"
BACKGROUND_TASK_PAUSED = "background_task.paused"
BACKGROUND_TASK_RESUMED = "background_task.resumed"
```

**Méthodes AgentWrapper ajoutées:**

```python
class AgentWrapper:
    async def plan_action(self, goal: str, context: Dict) -> str:
        """Planifie la prochaine action vers un goal."""

    async def execute_action(self, action: str, goal: str) -> Dict:
        """Exécute une action planifiée avec les outils."""

    async def is_goal_complete(self, goal: str, current_state: Dict) -> bool:
        """Vérifie si le goal est atteint (ou détecte [COMPLETE])."""
```

**Lifespan FastAPI:**

```python
# gathering/api/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: récupérer les tâches interrompues
    executor = get_background_executor(db_service=db)
    recovered = await executor.recover_tasks()

    yield

    # Shutdown: arrêt gracieux (pause toutes les tâches)
    await executor.shutdown(timeout=30)
```

**Caractéristiques:**

| Feature | Description |
|---------|-------------|
| **Checkpointing** | Sauvegarde toutes les 5 étapes (configurable) |
| **Recovery** | Tâches interrompues récupérées au redémarrage |
| **Timeout** | Limite de temps avec status `timeout` |
| **Max Steps** | Protection contre les boucles infinies |
| **Audit Trail** | Chaque step enregistré avec tokens et durée |
| **Completion** | L'agent évalue si le goal est atteint via LLM |
| **Circle Optional** | Agent peut travailler seul ou dans un circle |

#### 10.3 Scheduled Agent Actions ✅ IMPLÉMENTÉ

Planification cron-like pour les agents avec exécution automatique.

**Fichiers créés/modifiés:**

| Fichier | Description |
|---------|-------------|
| `gathering/db/migrations/013_scheduled_actions.sql` | Tables et vues |
| `gathering/orchestration/scheduler.py` | `Scheduler`, `ScheduledAction`, `ScheduledActionRun` |
| `gathering/api/routers/scheduled_actions.py` | API REST |
| `dashboard/src/pages/ScheduledActions.tsx` | Interface de gestion |

**Architecture:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCHEDULED ACTIONS SYSTEM                          │
│                                                                      │
│  ┌──────────────────────┐      ┌──────────────────────────────────┐ │
│  │ Scheduler            │      │ PostgreSQL                       │ │
│  │  (Singleton)         │      │ ┌──────────────────────────────┐ │ │
│  │                      │      │ │ circle.scheduled_actions     │ │ │
│  │  • start()           │─────►│ │  id, agent_id, schedule_type │ │ │
│  │  • stop()            │      │ │  cron_expression, interval   │ │ │
│  │  • add_action()      │      │ │  goal, status, next_run_at   │ │ │
│  │  • pause_action()    │      │ └──────────────────────────────┘ │ │
│  │  • resume_action()   │      │ ┌──────────────────────────────┐ │ │
│  │  • trigger_now()     │      │ │ circle.scheduled_action_runs │ │ │
│  │                      │      │ │  action_id, background_task  │ │ │
│  └───────────┬──────────┘      │ │  triggered_at, status        │ │ │
│              │                  │ └──────────────────────────────┘ │ │
│              │                  └──────────────────────────────────┘ │
│              ▼                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SCHEDULE TYPES                             │   │
│  │                                                               │   │
│  │  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌─────────────────┐  │   │
│  │  │  CRON   │  │ INTERVAL │  │  ONCE  │  │      EVENT      │  │   │
│  │  │         │  │          │  │        │  │                 │  │   │
│  │  │ 0 9 * * │  │ Every N  │  │ Single │  │ On event.type   │  │   │
│  │  │ MON-FRI │  │ seconds  │  │ run at │  │ (e.g. task.done)│  │   │
│  │  └─────────┘  └──────────┘  └────────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ BackgroundTaskExecutor (réutilise Phase 10.2)                 │   │
│  │  • Exécute le goal de l'action planifiée                      │   │
│  │  • Checkpointing, recovery, etc.                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Types de planification:**

| Type | Description | Exemple |
|------|-------------|---------|
| `cron` | Expression cron standard | `0 9 * * MON-FRI` (9h jours ouvrés) |
| `interval` | Intervalle fixe (min 60s) | `3600` = toutes les heures |
| `once` | Exécution unique programmée | `2025-01-15T10:00:00Z` |
| `event` | Déclenché par un événement | `task.completed` |

**Schéma SQL:**

```sql
-- Migration 013_scheduled_actions.sql

-- Enums
CREATE TYPE scheduled_action_status AS ENUM ('active', 'paused', 'disabled', 'expired');
CREATE TYPE schedule_type AS ENUM ('cron', 'interval', 'once', 'event');

CREATE TABLE circle.scheduled_actions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent.agents(id),
    circle_id INTEGER REFERENCES circle.circles(id),

    -- Définition
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schedule_type schedule_type NOT NULL,
    cron_expression VARCHAR(100),      -- "0 9 * * MON-FRI"
    interval_seconds INTEGER,          -- min 60
    event_trigger VARCHAR(100),        -- event name

    -- Tâche à exécuter
    goal TEXT NOT NULL,
    max_steps INTEGER DEFAULT 50,
    timeout_seconds INTEGER DEFAULT 3600,

    -- Contraintes
    status scheduled_action_status DEFAULT 'active',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    max_executions INTEGER,
    execution_count INTEGER DEFAULT 0,

    -- Comportement
    retry_on_failure BOOLEAN DEFAULT true,
    max_retries INTEGER DEFAULT 3,
    allow_concurrent BOOLEAN DEFAULT false,

    -- Tracking
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    tags TEXT[] DEFAULT '{}'
);

CREATE TABLE circle.scheduled_action_runs (
    id SERIAL PRIMARY KEY,
    scheduled_action_id INTEGER REFERENCES circle.scheduled_actions(id),
    background_task_id INTEGER REFERENCES circle.background_tasks(id),
    run_number INTEGER NOT NULL,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    triggered_by VARCHAR(50),  -- 'scheduler', 'manual', 'event'
    status background_task_status DEFAULT 'pending',
    result_summary TEXT,
    error_message TEXT,
    duration_ms INTEGER,
    steps_executed INTEGER DEFAULT 0
);

-- Vue dashboard
CREATE VIEW public.scheduled_actions_dashboard AS
SELECT sa.*, a.name as agent_name, c.name as circle_name,
       lr.status as last_run_status, lr.duration_ms as last_run_duration,
       (SELECT COUNT(*) FROM circle.scheduled_action_runs
        WHERE scheduled_action_id = sa.id AND status = 'completed') as successful_runs,
       (SELECT COUNT(*) FROM circle.scheduled_action_runs
        WHERE scheduled_action_id = sa.id AND status = 'failed') as failed_runs
FROM circle.scheduled_actions sa
JOIN agent.agents a ON sa.agent_id = a.id
LEFT JOIN circle.circles c ON sa.circle_id = c.id
LEFT JOIN LATERAL (...) lr ON true;
```

**Utilisation Python:**

```python
from gathering.orchestration import Scheduler, ScheduledAction, ScheduleType, get_scheduler

# Obtenir le scheduler singleton
scheduler = get_scheduler(db_service=db)

# Créer une action cron (tous les jours à 9h)
action = ScheduledAction(
    id=0,  # Auto-généré
    agent_id=1,
    name="Daily Code Review",
    goal="Review les commits d'hier et génère un rapport",
    schedule_type=ScheduleType.CRON,
    cron_expression="0 9 * * *",
    max_steps=50,
    retry_on_failure=True,
)
action_id = await scheduler.add_action(action)

# Créer une action interval (toutes les heures)
action2 = ScheduledAction(
    id=0,
    agent_id=2,
    name="Health Check",
    goal="Vérifie que tous les services sont opérationnels",
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=3600,
)

# Créer une action event-triggered
action3 = ScheduledAction(
    id=0,
    agent_id=1,
    name="Auto Review",
    goal="Review automatique du travail soumis",
    schedule_type=ScheduleType.EVENT,
    event_trigger="task.completed",
)

# Contrôle
await scheduler.pause_action(action_id)
await scheduler.resume_action(action_id)
await scheduler.trigger_now(action_id)  # Exécution manuelle immédiate
await scheduler.delete_action(action_id)

# Lister
actions = await scheduler.list_actions(status=ScheduledActionStatus.ACTIVE)
runs = await scheduler.get_runs(action_id, limit=20)
```

**API Endpoints:**

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/scheduled-actions` | GET | Liste (filtres: status, agent_id) |
| `/scheduled-actions` | POST | Créer une action planifiée |
| `/scheduled-actions/{id}` | GET | Détails |
| `/scheduled-actions/{id}` | PATCH | Modifier |
| `/scheduled-actions/{id}/pause` | POST | Pause |
| `/scheduled-actions/{id}/resume` | POST | Reprendre |
| `/scheduled-actions/{id}/trigger` | POST | Exécution immédiate |
| `/scheduled-actions/{id}` | DELETE | Supprimer |
| `/scheduled-actions/{id}/runs` | GET | Historique d'exécution |

**Dashboard UI (`/schedules`):**

- Compteurs: Total, Active, Paused, Expired
- Filtres par status
- Cards avec:
  - Nom, description, agent
  - Type de schedule (icône + expression)
  - Prochain run, dernier run
  - Stats: exécutions, taux de succès
  - Historique expandable
- Actions: Pause, Resume, Trigger Now, Delete
- Modal de création avec tous les types

**Événements:**

```python
# Nouveaux EventTypes dans events.py
SCHEDULED_ACTION_CREATED = "scheduled_action.created"
SCHEDULED_ACTION_UPDATED = "scheduled_action.updated"
SCHEDULED_ACTION_DELETED = "scheduled_action.deleted"
SCHEDULED_ACTION_TRIGGERED = "scheduled_action.triggered"
SCHEDULED_ACTION_STARTED = "scheduled_action.started"
SCHEDULED_ACTION_COMPLETED = "scheduled_action.completed"
SCHEDULED_ACTION_FAILED = "scheduled_action.failed"
SCHEDULED_ACTION_PAUSED = "scheduled_action.paused"
SCHEDULED_ACTION_RESUMED = "scheduled_action.resumed"
SCHEDULED_ACTION_SCHEDULER_STARTED = "scheduled_action.scheduler_started"
SCHEDULED_ACTION_SCHEDULER_STOPPED = "scheduled_action.scheduler_stopped"
```

**Lifespan FastAPI:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = get_database_service()
    executor = get_background_executor(db_service=db)
    await executor.recover_tasks()

    scheduler = get_scheduler(db_service=db)
    await scheduler.start()  # Charge les actions et démarre la boucle

    yield

    # Shutdown
    await scheduler.stop(timeout=10)
    await executor.shutdown(timeout=30)
```

**Dépendances:**

```
# requirements.txt
croniter>=2.0  # Parsing des expressions cron
```

**Caractéristiques:**

| Feature | Description |
|---------|-------------|
| **Cron Parsing** | Via `croniter` pour expressions standard |
| **Interval Min** | 60 secondes minimum |
| **Concurrent Control** | `allow_concurrent` pour éviter overlap |
| **Retry** | Retry automatique avec délai configurable |
| **Limits** | `max_executions` et `end_date` pour limiter |
| **Event-Driven** | Déclenchement sur événements du bus |
| **Integration** | Réutilise `BackgroundTaskExecutor` |
| **Recovery** | Actions chargées au démarrage |

#### 10.4 Event-Driven Workflows

Agents réagissent à des événements système.

```python
# Event types
class EventType(Enum):
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    REVIEW_REQUESTED = "review.requested"
    CIRCLE_STARTED = "circle.started"
    MEMORY_ADDED = "memory.added"
    AGENT_IDLE = "agent.idle"

# Event handler
class EventHandler:
    event_type: EventType
    agent_id: int
    action: str
    conditions: dict  # Optional filters

# Example: Auto-assign tasks
handler = EventHandler(
    event_type=EventType.TASK_CREATED,
    agent_id=1,  # Sophie
    action="evaluate_and_claim_task",
    conditions={"priority": ["high", "critical"]}
)
```

#### 10.5 Agent Goal Management

Objectifs à long terme avec décomposition automatique.

```python
# Goal hierarchy
class Goal:
    id: int
    agent_id: int
    description: str
    parent_id: int | None  # Subgoals
    status: GoalStatus  # pending, active, blocked, completed
    priority: float
    deadline: datetime | None

# Goal decomposition
async def decompose_goal(agent: Agent, goal: Goal) -> list[Goal]:
    """
    Agent décompose un goal en sous-goals.
    """
    prompt = f"""
    Goal: {goal.description}

    Decompose this into 3-5 actionable subgoals.
    Each subgoal should be specific and measurable.
    """
    subgoals = await agent.generate(prompt)
    return [Goal(parent_id=goal.id, ...) for sg in subgoals]
```

### Phase 11: Advanced Skills

Nouvelles compétences pour les agents.

#### 11.1 Web Browsing Skill

```python
class WebBrowsingSkill(BaseSkill):
    """Navigate and extract information from web pages."""

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search the web for information."""

    async def fetch_page(self, url: str) -> PageContent:
        """Fetch and parse a web page."""

    async def extract_data(self, url: str, schema: dict) -> dict:
        """Extract structured data from a page."""
```

#### 11.2 File System Skill

```python
class FileSystemSkill(BaseSkill):
    """Safe file operations within sandbox."""

    sandbox_root: Path  # All operations relative to this

    async def read(self, path: str) -> str:
        """Read file contents."""

    async def write(self, path: str, content: str) -> bool:
        """Write file (with backup)."""

    async def search(self, pattern: str, content: str = None) -> list[Match]:
        """Search files by name or content."""

    async def diff(self, path: str, new_content: str) -> str:
        """Show diff before applying changes."""
```

#### 11.3 Code Execution Sandbox

```python
class SandboxSkill(BaseSkill):
    """Execute code in isolated environment."""

    runtime: Literal["python", "node", "rust"]
    timeout: timedelta = timedelta(seconds=30)
    memory_limit: int = 512_000_000  # 512MB

    async def execute(self, code: str) -> ExecutionResult:
        """Run code and return stdout/stderr."""

    async def execute_file(self, path: str) -> ExecutionResult:
        """Run a file from the sandbox."""
```

#### 11.4 API Integration Skill

```python
class APISkill(BaseSkill):
    """Make HTTP requests to external APIs."""

    allowed_domains: list[str]  # Whitelist
    rate_limits: dict[str, RateLimit]

    async def get(self, url: str, params: dict = None) -> Response:
        """HTTP GET request."""

    async def post(self, url: str, data: dict) -> Response:
        """HTTP POST request."""

    async def graphql(self, url: str, query: str, variables: dict) -> Response:
        """GraphQL query."""
```

### Phase 12: Production Readiness

#### 12.1 Authentication & Authorization

```python
# JWT-based auth
class AuthConfig:
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire: timedelta = timedelta(hours=1)
    refresh_token_expire: timedelta = timedelta(days=7)

# Role-based access
class Permission(Enum):
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_DELETE = "agent:delete"
    CIRCLE_MANAGE = "circle:manage"
    TASK_CREATE = "task:create"
    MEMORY_ACCESS = "memory:access"
```

#### 12.2 Rate Limiting

```python
# Per-endpoint limits
rate_limits = {
    "/agents/*/chat": RateLimit(requests=60, window=60),  # 1/sec
    "/memories/*/recall": RateLimit(requests=100, window=60),
    "/knowledge/search": RateLimit(requests=30, window=60),
}

# Per-agent limits (LLM calls)
agent_limits = {
    "claude-opus-4-5": RateLimit(requests=10, window=60),
    "claude-sonnet-4-5": RateLimit(requests=60, window=60),
}
```

#### 12.3 Monitoring & Observability

```python
# Metrics (Prometheus)
metrics = {
    "gathering_agents_active": Gauge("Active agents count"),
    "gathering_tasks_completed_total": Counter("Tasks completed"),
    "gathering_llm_requests_total": Counter("LLM API calls", ["provider", "model"]),
    "gathering_llm_latency_seconds": Histogram("LLM response time"),
    "gathering_memory_searches_total": Counter("RAG searches"),
}

# Structured logging
logger.info(
    "task_completed",
    agent_id=1,
    task_id=42,
    duration_ms=1234,
    quality_score=85,
)
```

#### 12.4 Docker Deployment

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: pgvector/pgvector:pg16
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  dashboard:
    build: ./dashboard
    ports:
      - "3000:80"
```

---

## 10. Roadmap Complet

### Phases Complétées

| Phase | Description | Status |
|-------|-------------|--------|
| 1-3 | Core, Security, LLM Providers | Done |
| 4 | Skills (Git, Test), DeepSeek | Done |
| 5 | Orchestration, Persistence, Conversations | Done |
| 6 | FastAPI REST API + WebSocket | Done |
| 7 | React Dashboard (Web3 Dark Theme) | Done |
| 8 | PostgreSQL + pgvector (multi-schema) | Done |
| 9 | RAG Services + Knowledge Base UI | Done |

### Phases Planifiées

| Phase | Description | Priority |
|-------|-------------|----------|
| 10 | Agent Autonomy (background tasks, schedules, events, goals) | High |
| 11 | Advanced Skills (web, files, sandbox, APIs) | High |
| 12 | Production (auth, rate limiting, monitoring, Docker) | Medium |

---

## 11. Phase 10 - Agent Autonomy (Détails)

### 11.1 Phase 10.2 - Background Tasks

Permet aux agents d'exécuter des tâches longue durée de manière autonome.

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKGROUND TASK EXECUTOR                      │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   PENDING    │───►│   RUNNING    │───►│  COMPLETED   │      │
│  └──────────────┘    └──────┬───────┘    └──────────────┘      │
│                             │                                    │
│                     ┌───────┴───────┐                           │
│                     │   CHECKPOINT  │ (every N steps)            │
│                     └───────────────┘                           │
│                                                                  │
│  Features:                                                       │
│  • Step-by-step execution with history                          │
│  • Periodic checkpointing for recovery                          │
│  • LLM-driven goal completion detection                         │
│  • Pause/Resume/Cancel controls                                 │
│  • Progress tracking and metrics                                │
└─────────────────────────────────────────────────────────────────┘
```

**Tables:** `circle.background_tasks`, `circle.background_task_steps`

**Module:** `gathering/orchestration/background.py`

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/background-tasks` | POST | Créer et démarrer une tâche |
| `/background-tasks` | GET | Lister (filtres: status, agent_id) |
| `/background-tasks/{id}` | GET | Détails + progression |
| `/background-tasks/{id}/pause` | POST | Mettre en pause |
| `/background-tasks/{id}/resume` | POST | Reprendre |
| `/background-tasks/{id}/cancel` | POST | Annuler |
| `/background-tasks/{id}/steps` | GET | Historique des étapes |

### 11.2 Phase 10.3 - Scheduled Actions

Planification type cron pour exécution automatique de tâches.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEDULER                                 │
│                                                                  │
│  Schedule Types:                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │    CRON    │  │  INTERVAL  │  │    ONCE    │  │   EVENT   │ │
│  │ "0 9 * * *"│  │  "3600s"   │  │ "datetime" │  │  "on X"   │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
│                                                                  │
│  Lifecycle:                                                      │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌─────────┐         │
│  │ ACTIVE │───►│ PAUSED │───►│DISABLED│───►│ EXPIRED │         │
│  └────────┘    └────────┘    └────────┘    └─────────┘         │
│                                                                  │
│  Features:                                                       │
│  • Cron expressions (via croniter)                              │
│  • Interval-based scheduling                                    │
│  • One-time execution                                           │
│  • Event-triggered actions                                      │
│  • Retry on failure with exponential backoff                    │
│  • Max executions limit                                         │
│  • Date range constraints                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Tables:** `circle.scheduled_actions`, `circle.scheduled_action_runs`

**Module:** `gathering/orchestration/scheduler.py`

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scheduled-actions` | POST | Créer une action planifiée |
| `/scheduled-actions` | GET | Lister avec filtres |
| `/scheduled-actions/{id}` | GET | Détails |
| `/scheduled-actions/{id}` | PATCH | Modifier |
| `/scheduled-actions/{id}/pause` | POST | Mettre en pause |
| `/scheduled-actions/{id}/resume` | POST | Reprendre |
| `/scheduled-actions/{id}/trigger` | POST | Déclencher immédiatement |
| `/scheduled-actions/{id}/runs` | GET | Historique des exécutions |

### 11.3 Phase 10.4 - Event-Driven Workflows

Implémenté via le type de schedule `event` dans Phase 10.3.

```python
# Créer une action déclenchée par événement
action = ScheduledActionCreate(
    agent_id=1,
    name="On Task Complete",
    goal="Generate a summary report",
    schedule_type="event",
    event_trigger="task.completed",
)
```

### 11.4 Phase 10.5 - Agent Goals

Gestion hiérarchique des objectifs avec décomposition automatique.

```
┌─────────────────────────────────────────────────────────────────┐
│                       GOAL HIERARCHY                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ROOT GOAL: "Implement user authentication"               │   │
│  │  Status: ACTIVE | Progress: 40% | Priority: HIGH          │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ├──► ┌────────────────────────────────────────────┐       │
│       │    │ Subgoal 1: "Setup JWT infrastructure"       │       │
│       │    │ Status: COMPLETED | Progress: 100%          │       │
│       │    └────────────────────────────────────────────┘       │
│       │                                                          │
│       ├──► ┌────────────────────────────────────────────┐       │
│       │    │ Subgoal 2: "Create login/register endpoints"│       │
│       │    │ Status: ACTIVE | Progress: 60%              │       │
│       │    └────────────────────────────────────────────┘       │
│       │                                                          │
│       └──► ┌────────────────────────────────────────────┐       │
│            │ Subgoal 3: "Write tests"                    │       │
│            │ Status: BLOCKED (depends on #2)             │       │
│            └────────────────────────────────────────────┘       │
│                                                                  │
│  Features:                                                       │
│  • Hierarchical goal structure (parent/child)                   │
│  • LLM-powered automatic decomposition                          │
│  • Dependency management (blocking relationships)               │
│  • Activity logging for audit trail                             │
│  • Progress aggregation from subgoals                           │
│  • Background task integration                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Tables:**
- `agent.goals` - Main goal storage with hierarchy
- `agent.goal_dependencies` - Dependencies between goals
- `agent.goal_activities` - Activity log

**View:** `public.goals_dashboard` - Aggregated view with stats

**Module:** `gathering/agents/goals.py`

**Classes:**
```python
class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GoalPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Goal:
    id: int
    agent_id: int
    title: str
    description: str
    status: GoalStatus
    priority: GoalPriority
    progress_percent: int
    parent_id: Optional[int]  # For hierarchy
    # ... plus 30+ fields for full tracking

class GoalManager:
    async def create_goal(goal: Goal) -> int
    async def decompose_goal(goal_id: int, agent: AgentWrapper) -> List[int]
    async def add_dependency(goal_id: int, depends_on_id: int) -> bool
    async def start_goal(goal_id: int) -> bool
    async def complete_goal(goal_id: int, result: str) -> bool
    # ... full CRUD + status management
```

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/goals` | POST | Créer un goal |
| `/goals` | GET | Lister (filtres: status, agent, root_only) |
| `/goals/{id}` | GET | Détails |
| `/goals/{id}` | PATCH | Modifier |
| `/goals/{id}` | DELETE | Supprimer (cascade subgoals) |
| `/goals/{id}/start` | POST | Démarrer le travail |
| `/goals/{id}/complete` | POST | Marquer comme complété |
| `/goals/{id}/fail` | POST | Marquer comme échoué |
| `/goals/{id}/pause` | POST | Mettre en pause |
| `/goals/{id}/resume` | POST | Reprendre |
| `/goals/{id}/progress` | POST | Mettre à jour la progression |
| `/goals/{id}/decompose` | POST | Décomposer via LLM |
| `/goals/{id}/subgoals` | GET | Obtenir les sous-objectifs |
| `/goals/{id}/tree` | GET | Arbre complet avec nested subgoals |
| `/goals/{id}/dependencies` | GET/POST | Gérer dépendances |
| `/goals/{id}/activities` | GET | Historique d'activité |

**Dashboard:** Page Goals avec:
- Vue arborescente des goals (expandable)
- Badges de statut et priorité
- Barre de progression
- Boutons d'action (Start, Pause, Complete, Decompose)
- Modal de détails avec activités et dépendances
- Formulaire de création

### 11.5 Phase 10.6 - Settings & Configuration

Page de configuration centralisée pour les clés API et paramètres applicatifs.

```text
┌─────────────────────────────────────────────────────────────────┐
│                       SETTINGS PAGE                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    LLM PROVIDERS                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│  │  │  Anthropic   │  │   OpenAI     │  │  DeepSeek    │      │ │
│  │  │  ✅ Configured│  │  ⚠️ Not set  │  │  ✅ Configured│      │ │
│  │  │              │  │              │  │              │      │ │
│  │  │ API Key: ****│  │ API Key: ___ │  │ API Key: ****│      │ │
│  │  │ Model: sonnet│  │ Model: gpt-4 │  │ Model: coder │      │ │
│  │  │ [Test][Save] │  │ [Test][Save] │  │ [Test][Save] │      │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│  │                                                             │ │
│  │  ┌──────────────┐                                          │ │
│  │  │    Ollama    │   (Local - no API key required)          │ │
│  │  │  ✅ Available │                                          │ │
│  │  │ URL: :11434  │                                          │ │
│  │  │ Model: llama │                                          │ │
│  │  └──────────────┘                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     DATABASE                                │ │
│  │  PostgreSQL: ✅ Connected                                   │ │
│  │  Host: localhost | Port: 5432 | DB: gathering              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   APPLICATION                               │ │
│  │  Environment: development                                   │ │
│  │  Debug: [ON/OFF]  |  Log Level: [DEBUG ▾]                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Module:** `gathering/api/routers/settings.py`

**Fonctionnalités:**
- Configuration des clés API par provider (Anthropic, OpenAI, DeepSeek, Ollama)
- Test de connexion aux providers avec feedback immédiat
- Affichage masqué des clés API (sk-...****...xxxx)
- Configuration du modèle par défaut par provider
- Affichage de l'état de connexion à la base de données
- Toggle debug mode en temps réel
- Sélection du niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Persistance dans le fichier .env

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/settings` | GET | Récupérer tous les paramètres |
| `/settings/providers/{provider}` | PATCH | Mettre à jour un provider |
| `/settings/application` | PATCH | Mettre à jour les paramètres app |
| `/settings/providers/{provider}/test` | POST | Tester la connexion provider |

**Schémas:**

```python
class ProviderSettings(BaseModel):
    api_key: Optional[str]      # Masked on read (sk-...****...last4)
    default_model: Optional[str]
    base_url: Optional[str]     # For Ollama
    is_configured: bool

class DatabaseSettings(BaseModel):
    host: str
    port: int
    name: str
    user: str
    is_connected: bool

class ApplicationSettings(BaseModel):
    environment: str            # development, staging, production
    debug: bool
    log_level: str              # DEBUG, INFO, WARNING, ERROR, CRITICAL

class AllSettings(BaseModel):
    providers: Dict[str, ProviderSettings]
    database: DatabaseSettings
    application: ApplicationSettings
```

**Dashboard:** Page Settings avec:

- Cartes pour chaque provider LLM
- Inputs de clé API avec toggle visibilité (eye icon)
- Bouton "Test" pour valider la connexion
- Indicateurs visuels de configuration (✅ Configured / ⚠️ Not configured)
- Section Database en lecture seule
- Section Application avec contrôles interactifs

---

## 12. Phase 11 - Advanced Skills

Ensemble complet d'outils pour donner aux agents une autonomie maximale.

### 12.1 Vue d'Ensemble des Skills

```text
┌─────────────────────────────────────────────────────────────────┐
│                      SKILLS FRAMEWORK                            │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   WEB       │  │   SHELL     │  │   SOCIAL    │             │
│  │  SEARCH     │  │   TOOLS     │  │   MEDIA     │             │
│  │             │  │             │  │             │             │
│  │ • DuckDuckGo│  │ • Bash exec │  │ • Twitter/X │             │
│  │ • Brave     │  │ • File ops  │  │ • LinkedIn  │             │
│  │ • Scraping  │  │ • Git ops   │  │ • Discord   │             │
│  │ • Wikipedia │  │ • Docker    │  │ • Telegram  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    CODE     │  │    HTTP     │  │   FINANCE   │             │
│  │  EXECUTION  │  │    API      │  │    DATA     │             │
│  │             │  │             │  │             │             │
│  │ • Python    │  │ • REST call │  │ • Stocks    │             │
│  │ • Node.js   │  │ • GraphQL   │  │ • Crypto    │             │
│  │ • Sandbox   │  │ • Webhooks  │  │ • News      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   MEDIA     │  │   EMAIL     │  │  CALENDAR   │             │
│  │  PROCESS    │  │   COMMS     │  │   TASKS     │             │
│  │             │  │             │  │             │             │
│  │ • Images    │  │ • SMTP/IMAP │  │ • Google    │             │
│  │ • PDF parse │  │ • Templates │  │ • Outlook   │             │
│  │ • Audio     │  │ • Lists     │  │ • iCal      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Web Search Skill

Recherche web multi-sources avec parsing intelligent.

```python
class WebSearchSkill(BaseSkill):
    """
    Web search and content extraction.

    Tools:
    - web_search: Search the web using multiple engines
    - fetch_page: Fetch and parse a web page
    - extract_content: Extract structured data from HTML
    - wikipedia_search: Search Wikipedia
    - news_search: Search news articles
    """

    name = "web"

    def get_tools(self) -> List[Dict]:
        return [
            {
                "name": "web_search",
                "description": "Search the web for information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "engine": {"type": "string", "enum": ["duckduckgo", "brave", "google"], "default": "duckduckgo"},
                        "num_results": {"type": "integer", "default": 10, "maximum": 50},
                        "time_range": {"type": "string", "enum": ["day", "week", "month", "year", "all"]},
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "fetch_page",
                "description": "Fetch a web page and extract text content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"},
                        "extract_mode": {"type": "string", "enum": ["text", "html", "markdown", "structured"]},
                        "wait_js": {"type": "boolean", "default": False, "description": "Wait for JavaScript to render"},
                    },
                    "required": ["url"]
                }
            },
            # ... more tools
        ]
```

**Moteurs de recherche supportés:**

| Engine | Type | Rate Limit | Notes |
|--------|------|------------|-------|
| DuckDuckGo | Free | 100/min | Default, no API key |
| Brave Search | API | 2000/month free | Needs API key |
| SerpAPI | API | Pay per use | Google results |
| Wikipedia | Free | Unlimited | Structured data |
| News API | API | 100/day free | News articles |

### 12.3 Shell Tools Skill

Exécution de commandes système avec sandbox de sécurité.

```python
class ShellSkill(BaseSkill):
    """
    Shell command execution with security controls.

    Tools:
    - shell_exec: Execute a shell command
    - file_read: Read file contents
    - file_write: Write to a file
    - file_list: List directory contents
    - git_command: Execute git commands
    - docker_command: Execute docker commands (if enabled)
    """

    name = "shell"

    # Security configuration
    allowed_commands = [
        "ls", "cat", "head", "tail", "grep", "find", "wc",
        "sort", "uniq", "awk", "sed", "cut", "tr", "diff",
        "curl", "wget", "jq", "yq", "tree", "file", "stat",
        "git", "npm", "pip", "python", "node", "make",
    ]

    blocked_patterns = [
        r"rm\s+-rf\s+/",  # Destructive rm
        r"mkfs",          # Filesystem format
        r"dd\s+if=",      # Disk operations
        r">\s*/dev/",     # Writing to devices
        r"chmod\s+777",   # Dangerous permissions
        r"\|\s*sh\s*$",   # Pipe to shell
        r"curl.*\|\s*bash", # Curl pipe to bash
    ]

    def execute(self, tool_name: str, tool_input: dict) -> SkillResponse:
        if tool_name == "shell_exec":
            command = tool_input["command"]

            # Security validation
            if not self._is_safe_command(command):
                return SkillResponse(
                    success=False,
                    message="Command blocked by security policy"
                )

            # Execute in sandbox
            result = self._execute_sandboxed(
                command,
                timeout=tool_input.get("timeout", 30),
                working_dir=tool_input.get("cwd"),
            )
            return SkillResponse(success=True, data=result)
```

**Fonctionnalités de sécurité:**

- Whitelist de commandes autorisées
- Patterns bloqués (rm -rf /, etc.)
- Timeout par commande (défaut: 30s)
- Sandbox optionnel via Docker/Firejail
- Logging de toutes les commandes
- Working directory contrôlé

### 12.4 Social Media Skill

Interaction avec les réseaux sociaux.

```python
class SocialMediaSkill(BaseSkill):
    """
    Social media interactions.

    Tools:
    - twitter_search: Search Twitter/X
    - twitter_post: Post a tweet (if authorized)
    - twitter_dm: Send direct message
    - linkedin_search: Search LinkedIn
    - discord_send: Send Discord message
    - telegram_send: Send Telegram message
    """

    name = "social"

    def get_tools(self) -> List[Dict]:
        return [
            {
                "name": "twitter_search",
                "description": "Search Twitter/X for tweets",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "count": {"type": "integer", "default": 20, "maximum": 100},
                        "include_replies": {"type": "boolean", "default": False},
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "discord_send",
                "description": "Send a message to a Discord channel",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string"},
                        "message": {"type": "string"},
                        "embed": {"type": "object", "description": "Optional rich embed"},
                    },
                    "required": ["channel_id", "message"]
                }
            },
            # ...
        ]
```

**Plateformes supportées:**

| Platform | Read | Write | Auth Method |
|----------|------|-------|-------------|
| Twitter/X | ✅ | ✅ | OAuth 2.0 |
| LinkedIn | ✅ | ✅ | OAuth 2.0 |
| Discord | ✅ | ✅ | Bot Token |
| Telegram | ✅ | ✅ | Bot Token |
| Slack | ✅ | ✅ | OAuth/Bot |
| Reddit | ✅ | ✅ | OAuth 2.0 |

### 12.5 Code Execution Skill

Exécution de code dans un sandbox sécurisé.

```python
class CodeExecutionSkill(BaseSkill):
    """
    Safe code execution in isolated environments.

    Tools:
    - python_exec: Execute Python code
    - node_exec: Execute Node.js code
    - sql_query: Execute SQL queries (read-only)
    """

    name = "code"

    # Sandbox configuration
    config = {
        "python": {
            "timeout": 30,
            "memory_limit": "256M",
            "allowed_imports": [
                "json", "re", "datetime", "math", "random",
                "collections", "itertools", "functools",
                "requests", "pandas", "numpy",
            ],
            "blocked_imports": [
                "os", "sys", "subprocess", "socket", "shutil",
            ],
        },
        "node": {
            "timeout": 30,
            "memory_limit": "256M",
        }
    }
```

### 12.6 HTTP/API Skill

Appels HTTP et intégrations API.

```python
class HttpSkill(BaseSkill):
    """
    HTTP requests and API integrations.

    Tools:
    - http_request: Make HTTP request
    - graphql_query: Execute GraphQL query
    - webhook_send: Send webhook notification
    """

    name = "http"

    def get_tools(self) -> List[Dict]:
        return [
            {
                "name": "http_request",
                "description": "Make an HTTP request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                        "url": {"type": "string"},
                        "headers": {"type": "object"},
                        "body": {"type": "object"},
                        "timeout": {"type": "integer", "default": 30},
                    },
                    "required": ["method", "url"]
                }
            },
        ]
```

### 12.7 Architecture des Skills

```text
gathering/skills/
├── __init__.py
├── base.py              # BaseSkill class
├── registry.py          # SkillRegistry
├── git.py               # Git operations ✅
├── test.py              # Test runner ✅
├── web/                 # Phase 11
│   ├── __init__.py
│   ├── search.py        # Web search engines
│   ├── scraper.py       # Content extraction
│   └── browser.py       # Headless browser (Playwright)
├── shell/               # Phase 11
│   ├── __init__.py
│   ├── executor.py      # Command execution
│   ├── sandbox.py       # Security sandbox
│   └── file_ops.py      # File operations
├── social/              # Phase 11
│   ├── __init__.py
│   ├── twitter.py       # Twitter/X API
│   ├── discord.py       # Discord bot
│   ├── telegram.py      # Telegram bot
│   └── linkedin.py      # LinkedIn API
├── code/                # Phase 11
│   ├── __init__.py
│   ├── python_exec.py   # Python sandbox
│   ├── node_exec.py     # Node.js sandbox
│   └── docker_exec.py   # Docker execution
├── http/                # Phase 11
│   ├── __init__.py
│   ├── client.py        # HTTP client
│   └── graphql.py       # GraphQL support
└── media/               # Phase 11
    ├── __init__.py
    ├── image.py         # Image processing
    ├── pdf.py           # PDF parsing
    └── audio.py         # Audio processing
```

---

## 13. Phase 12 - Project Management

### 13.1 Vue d'Ensemble

La Phase 12 ajoute la gestion complète des projets depuis le dashboard. Les utilisateurs peuvent naviguer dans le système de fichiers, ajouter des projets, et assigner des équipes d'agents (circles) pour travailler dessus - le tout sans écrire une seule ligne de code.

### 13.2 Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| **Folder Browser** | Navigation dans le filesystem depuis le dashboard |
| **Auto-Detection** | Détection automatique des outils, venv, git, etc. |
| **Project CRUD** | Créer, lire, mettre à jour, supprimer des projets |
| **Circle Linking** | Assigner des circles d'agents à des projets |
| **Context Injection** | Injecter le contexte projet dans les prompts LLM |
| **Refresh** | Re-détecter les paramètres quand le projet évolue |

### 13.3 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DASHBOARD                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Projects Page                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │ │
│  │  │   Project    │  │   Project    │  │  + Add New   │       │ │
│  │  │  gathering   │  │  my-webapp   │  │   Project    │       │ │
│  │  │  Python 3.11 │  │  Node.js     │  │              │       │ │
│  │  │  2 circles   │  │  1 circle    │  │  [Browse]    │       │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                    ┌─────────▼─────────┐                        │
│                    │  Folder Browser   │                        │
│                    │  Modal            │                        │
│                    │  /home/user/      │                        │
│                    │  ├── workspace/   │                        │
│                    │  │   └── proj ⭐  │                        │
│                    │  └── documents/   │                        │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API BACKEND                              │
│                                                                  │
│  /projects                                                       │
│  ├── GET    /              → Liste des projets                  │
│  ├── POST   /              → Créer projet (auto-detect)         │
│  ├── GET    /{id}          → Détails projet                     │
│  ├── PATCH  /{id}          → Mettre à jour                      │
│  ├── DELETE /{id}          → Supprimer                          │
│  ├── POST   /{id}/refresh  → Re-détecter paramètres             │
│  ├── GET    /{id}/context  → Contexte formaté pour LLM          │
│  │                                                              │
│  ├── GET    /browse/folders?path=...  → Naviguer dossiers       │
│  │                                                              │
│  └── Circle Linking                                             │
│      ├── POST   /{id}/circles/{cid}  → Lier circle              │
│      ├── DELETE /{id}/circles/{cid}  → Délier circle            │
│      └── GET    /{id}/circles        → Lister circles liés      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (project schema)                     │
│                                                                  │
│  project.projects                                                │
│  ├── id, name, display_name, description                        │
│  ├── local_path, repository_url, branch                         │
│  ├── status (active, archived, on_hold)                         │
│  ├── tech_stack[], languages[], frameworks[]                    │
│  ├── venv_path, python_version                                  │
│  ├── tools (JSONB), conventions (JSONB)                         │
│  ├── key_files (JSONB), commands (JSONB)                        │
│  └── notes[], created_at, updated_at                            │
│                                                                  │
│  project.circle_projects                                         │
│  ├── project_id → project.projects(id)                          │
│  ├── circle_id → circle.circles(id)                             │
│  ├── is_primary, linked_at                                      │
│  └── UNIQUE(project_id, circle_id)                              │
└─────────────────────────────────────────────────────────────────┘
```

### 13.4 Auto-Détection de Projet

Quand un projet est ajouté, `ProjectContext.from_path()` détecte automatiquement :

```python
# Détection des outils
project_indicators = [
    "pyproject.toml",    # Python (moderne)
    "setup.py",          # Python (legacy)
    "package.json",      # Node.js
    "Cargo.toml",        # Rust
    "go.mod",            # Go
    "pom.xml",           # Java Maven
    "build.gradle",      # Java Gradle
    "Makefile",          # C/C++
    ".git",              # Version control
]

# Détection venv Python
venv_locations = [".venv", "venv", ".env"]

# Détection Git
git_branch = subprocess.run(["git", "branch", "--show-current"])
git_remote = subprocess.run(["git", "remote", "get-url", "origin"])

# Résultat: ProjectContext
{
    "name": "gathering",
    "path": "/home/user/workspace/gathering",
    "venv_path": "/home/user/workspace/gathering/.venv",
    "python_version": "3.11",
    "tools": {
        "testing": "pytest",
        "linting": "ruff",
        "web_framework": "fastapi"
    },
    "git_branch": "develop",
    "git_remote": "https://github.com/alkimya/gathering.git"
}
```

### 13.5 Contexte pour LLM

L'endpoint `/projects/{id}/context` retourne le contexte formaté pour injection dans les prompts agents :

```json
{
  "project_id": 1,
  "project_name": "gathering",
  "prompt_context": "## Project Context\n\nProject: gathering\nPath: /home/user/workspace/gathering\nPython: 3.11\nVenv: /home/user/workspace/gathering/.venv\n\n### Tools\n- testing: pytest\n- linting: ruff\n\n### Commands\n- test: pytest tests/\n- lint: ruff check .\n\n### Key Files\n- entry: gathering/__init__.py\n- config: pyproject.toml",
  "raw": { /* full ProjectContext dict */ }
}
```

### 13.6 Dashboard UI

La page Projects (`/projects`) permet de :

1. **Voir tous les projets** en cartes avec statut, langages, branches git
2. **Ajouter un projet** via le navigateur de dossiers modal
3. **Voir les détails** (outils, commandes, notes, conventions)
4. **Refresh** pour re-détecter les paramètres
5. **Filtrer** par status (active, archived, on_hold)
6. **Gérer les circles** liés au projet

### 13.7 Fichiers Implémentés

```
gathering/
├── api/routers/
│   └── projects.py          # API endpoints (CRUD, browse, circles)
├── agents/
│   └── project_context.py   # ProjectContext dataclass (existait déjà)

dashboard/src/
├── pages/
│   └── Projects.tsx         # Page principale + FolderBrowser modal
├── services/
│   └── api.ts               # + projects API client
├── types/
│   └── index.ts             # + Project, FolderEntry types
├── components/
│   └── Layout.tsx           # + Projects nav item
└── App.tsx                  # + /projects route
```

### 13.8 Workflow Utilisateur

```
1. Dashboard → Projects → "Add Project"
                ↓
2. FolderBrowser s'ouvre (par défaut: ~/)
                ↓
3. Naviguer jusqu'au dossier projet (marqué ⭐ si détecté)
                ↓
4. Sélectionner → Entrer nom → "Add Project"
                ↓
5. Auto-détection (venv, git, tools, commands...)
                ↓
6. Projet créé → Visible dans la liste
                ↓
7. Optionnel: Lier des circles pour assigner des agents
```

### 13.9 Sécurité

- **Chemins interdits** : `/proc`, `/sys`, `/dev`, `/boot`, `/root`
- **Fichiers cachés** : Masqués par défaut (option `show_hidden`)
- **Dossiers ignorés** : `__pycache__`, `node_modules`, `.git`, `.venv`, `.cache`
- **Validation path** : Le chemin doit exister et être un répertoire

---

**Document maintenu par l'équipe GatheRing**
