# Intégration Projet - Guide Complet

Guide pour faire travailler des agents sur un projet externe avec GatheRing.

## Vue d'Ensemble

GatheRing permet maintenant aux agents de travailler sur des projets externes (codebases, dossiers) avec :

- **Contexte projet automatique** - Détection environnement, outils, conventions
- **Chemins relatifs auto-résolus** - Les agents peuvent dire "lis src/main.py"
- **Mémoire projet partagée** - Connaissances partagées entre agents sur le projet
- **Circles liés à projet** - Équipes dédiées à un projet spécifique

## Quick Start

```python
from gathering.agents.wrapper import AgentWrapper
from gathering.agents.persona import AgentPersona
from gathering.orchestration.circle_store import CircleStore

# 1. Créer agent
agent = AgentWrapper(
    agent_id=1,
    persona=AgentPersona(name="Sophie", role="Developer"),
    llm=your_llm_provider,
)

# 2. Charger projet
agent.load_project_context("/home/user/my-app", project_id=1)

# 3. Travailler sur le projet
response = await agent.chat("Analyse le fichier src/main.py et trouve les bugs")
# → Agent lit automatiquement /home/user/my-app/src/main.py

# 4. Créer circle pour le projet
store = CircleStore.from_env()
circle_id = store.create_circle(
    name="my-app-team",
    project_id=1,
)
store.add_member(circle_id, agent_id=1)
```

## Fonctionnalités

### 1. Chargement Automatique du Contexte Projet

ProjectContext détecte automatiquement :

- **Environnement Python** - venv, version Python
- **Outils utilisés** - pytest, ruff, sqlalchemy, etc.
- **Structure** - Fichiers importants, dossiers clés
- **Git** - Branche, remote
- **Commandes fréquentes** - test, lint, build

```python
from gathering.agents.project_context import ProjectContext

# Charger et analyser projet
project = ProjectContext.from_path("/home/user/my-app")

# Inspecter
print(project.tools)  # {"database": "picopg", "testing": "pytest"}
print(project.venv_path)  # "/home/user/my-app/venv"
print(project.commands)  # {"test": "pytest tests/ -v"}
```

### 2. Auto-Résolution des Chemins

Quand un agent a un projet chargé, les skills filesystem/git/code résolvent automatiquement les chemins relatifs :

```python
agent.load_project_context("/home/user/my-app")

# Agent peut utiliser chemins relatifs
await agent.chat("Read src/api/routes.py")
# → Résolu vers /home/user/my-app/src/api/routes.py

await agent.chat("List files in tests/")
# → Liste /home/user/my-app/tests/
```

**Skills supportés :**
- `filesystem` (fs_read, fs_write, fs_list)
- `git` (git_status, git_diff, etc.)
- `code` (analyse code, refactoring)

### 3. Contexte Projet dans les Prompts

Le contexte projet est automatiquement injecté dans le system prompt :

```
## Contexte Projet
Projet: my-app
Chemin: /home/user/my-app

Environnement Python:
  - venv: /home/user/my-app/venv
  - Python: 3.11
  - IMPORTANT: Toujours utiliser 'source venv/bin/activate' avant les commandes Python

Outils du projet:
  - database: picopg
  - testing: pytest

Conventions:
  - primary_keys: IDENTITY
  - imports: absolute

Fichiers importants:
  - config: src/config.py
  - models: src/models/

Commandes fréquentes:
  - test: pytest tests/ -v
  - activate: source venv/bin/activate
```

### 4. Circles Liés à Projet

Créer une équipe dédiée à un projet :

```python
from gathering.orchestration.circle_store import CircleStore

store = CircleStore.from_env()

# Créer circle pour projet
circle_id = store.create_circle(
    name="backend-team",
    display_name="Backend Development Team",
    project_id=1,  # Lien vers projet
)

# Ajouter agents
store.add_member(circle_id, agent_id=1, role='lead')
store.add_member(circle_id, agent_id=2, role='member')

# Créer tâches sur fichiers du projet
task_id = store.create_task(
    circle_id=circle_id,
    title="Optimize database queries in src/db/queries.py",
    project_id=1,
    context={
        "file": "src/db/queries.py",
        "issue": "Slow queries on user table",
    },
)

# Lister circles d'un projet
circles = store.list_circles(project_id=1)
```

### 5. Mémoire Projet Partagée

Les agents peuvent partager des connaissances au niveau projet :

```python
from gathering.rag.memory_manager import MemoryManager

memory = MemoryManager.from_env()

# Agent 1 découvre quelque chose
await memory.remember(
    agent_id=1,
    content="IMPORTANT: src/db/connection.py utilise picopg, pas psycopg2",
    memory_type="decision",
    scope="project",
    scope_id=1,  # project_id
)

# Agent 2 peut retrouver cette info
results = await memory.recall(
    agent_id=2,
    query="Comment se connecter à la base de données ?",
)
# → Trouve : "src/db/connection.py utilise picopg"
```

**Scopes de mémoire :**
- `agent` - Privée à l'agent
- `circle` - Partagée dans le circle
- `project` - Partagée au niveau projet
- `global` - Accessible à tous

## Workflow Complet

### Exemple : Multi-Agents Corrigeant un Bug

```python
from gathering.orchestration.circle_store import CircleStore
from gathering.agents.wrapper import AgentWrapper
from gathering.rag.memory_manager import MemoryManager

# Setup
store = CircleStore.from_env()
memory = MemoryManager.from_env()

# 1. Créer circle pour projet
circle_id = store.create_circle(
    name="bug-fix-team",
    project_id=1,
)

# 2. Ajouter agents avec compétences
store.add_member(
    circle_id,
    agent_id=1,
    role='lead',
    competencies=['python', 'debugging'],
)
store.add_member(
    circle_id,
    agent_id=2,
    role='member',
    competencies=['testing', 'python'],
)

# 3. Créer tâche
task_id = store.create_task(
    circle_id=circle_id,
    title="Fix validation bug in auth module",
    project_id=1,
    required_competencies=['python', 'debugging'],
    context={
        "file": "src/api/auth.py",
        "issue": "Password validation allows empty strings",
        "priority": "high",
    },
)

# 4. Agent 1 (lead) analyse le bug
agent1 = AgentWrapper(agent_id=1, ...)
agent1.load_project_context("/home/user/my-app", project_id=1)

response = await agent1.chat(
    "Analyse src/api/auth.py et identifie le bug de validation"
)

# 5. Agent 1 partage ses découvertes
await memory.remember(
    agent_id=1,
    content="Bug trouvé: ligne 45 de src/api/auth.py, manque validation len(password) > 0",
    memory_type="learning",
    scope="circle",
    scope_id=circle_id,
)

# 6. Agent 2 (tester) crée tests
agent2 = AgentWrapper(agent_id=2, ...)
agent2.load_project_context("/home/user/my-app", project_id=1)

# Agent 2 accède à la connaissance partagée
response = await agent2.chat(
    "Crée des tests pour le bug de validation password"
)

# 7. Update task
store.update_task_status(
    task_id,
    status="completed",
    result="Bug fixé et tests ajoutés",
)
```

## API Reference

### AgentWrapper

```python
class AgentWrapper:
    def load_project_context(
        self,
        project_path: str,
        project_id: Optional[int] = None
    ) -> ProjectContext:
        """
        Charge contexte projet depuis filesystem.

        Args:
            project_path: Chemin absolu vers le projet
            project_id: ID optionnel pour lien DB

        Returns:
            ProjectContext avec détection auto
        """

    def set_project(
        self,
        project: ProjectContext,
        project_id: Optional[int] = None
    ) -> None:
        """Définit le projet actuel."""

    def get_project(self) -> Optional[ProjectContext]:
        """Récupère le projet actuel."""

    def get_project_id(self) -> Optional[int]:
        """Récupère l'ID du projet actuel."""
```

### CircleStore

```python
class CircleStore:
    def create_circle(
        self,
        name: str,
        project_id: Optional[int] = None,
        **kwargs
    ) -> int:
        """Crée circle lié à un projet."""

    def create_task(
        self,
        circle_id: int,
        title: str,
        project_id: Optional[int] = None,
        **kwargs
    ) -> int:
        """Crée tâche liée à un projet."""

    def list_circles(
        self,
        project_id: Optional[int] = None,
        **kwargs
    ) -> List[Dict]:
        """Liste circles filtrés par projet."""
```

### ProjectContext

```python
class ProjectContext:
    @classmethod
    def from_path(cls, path: str, name: Optional[str] = None) -> "ProjectContext":
        """
        Crée ProjectContext avec détection auto.

        Détecte:
        - venv et version Python
        - Outils (pytest, ruff, etc.)
        - Structure projet
        - Git branch/remote
        - Commandes fréquentes
        """

    def to_prompt(self) -> str:
        """Génère contexte pour injection dans prompts."""

    def add_tool(self, name: str, value: str) -> None:
        """Enregistre un outil."""

    def add_convention(self, key: str, value: Any) -> None:
        """Enregistre une convention."""
```

## Cas d'Usage

### 1. Code Review Multi-Agents

```python
# Circle de review
circle_id = store.create_circle("code-review", project_id=1)
store.add_member(circle_id, agent_id=1, role='lead')  # Reviewer
store.add_member(circle_id, agent_id=2, role='member')  # Author

# Tâche de review
task_id = store.create_task(
    circle_id=circle_id,
    title="Review PR #42",
    context={"files": ["src/api/users.py", "tests/test_users.py"]},
)
```

### 2. Refactoring Coordonné

```python
# Circle refactoring
circle_id = store.create_circle("refactor-team", project_id=1)

# Tâche avec sous-tâches
parent_task = store.create_task(
    circle_id=circle_id,
    title="Refactor authentication module",
)

# Agents travaillent sur différents fichiers
agent1.load_project_context(project_path, project_id=1)
agent2.load_project_context(project_path, project_id=1)

# Mémoire partagée pour coordination
await memory.remember(
    agent_id=1,
    content="J'ai renommé validate_user() en authenticate_user()",
    scope="circle",
    scope_id=circle_id,
)
```

### 3. Documentation Automatique

```python
agent.load_project_context("/home/user/my-app")

response = await agent.chat(
    "Génère documentation pour tous les fichiers dans src/api/"
)
```

## Bonnes Pratiques

1. **Toujours charger le projet avant de travailler**
   ```python
   agent.load_project_context(project_path, project_id)
   ```

2. **Utiliser chemins relatifs dans les instructions**
   ```python
   await agent.chat("Read src/main.py")  # Bon
   # vs
   await agent.chat("Read /absolute/path/src/main.py")  # Éviter
   ```

3. **Partager découvertes via mémoire circle/project**
   ```python
   await memory.remember(
       agent_id=1,
       content="IMPORTANT: ...",
       scope="circle",  # ou "project"
       scope_id=circle_id,
   )
   ```

4. **Lier circles et tasks au projet**
   ```python
   circle_id = store.create_circle(name="...", project_id=1)
   task_id = store.create_task(..., project_id=1)
   ```

## Troubleshooting

### Chemins non résolus

**Problème :** Agent ne trouve pas les fichiers

**Solution :** Vérifier que projet est chargé
```python
assert agent.get_project() is not None
assert agent.get_project_id() == expected_id
```

### Contexte projet absent des prompts

**Problème :** Projet non dans system prompt

**Solution :** Vérifier ProjectContext.from_path()
```python
project = ProjectContext.from_path(path)
assert project.path == path
assert project.name != ""
```

### Mémoire projet non partagée

**Problème :** Agents ne voient pas mémoire partagée

**Solution :** Vérifier scope et scope_id
```python
await memory.remember(
    agent_id=1,
    content="...",
    scope="project",  # Pas "agent"
    scope_id=project_id,  # Important !
)
```

## Prochaines Fonctionnalités

- **Auto-assignment tasks** - Tâches assignées automatiquement selon compétences
- **Conflict detection** - Détection conflits entre agents (fichiers modifiés)
- **Review workflow** - Workflow review automatique entre agents
- **WebSocket updates** - Notifications temps réel des changements

## Voir Aussi

- [PHASE4_CHANGELOG.md](PHASE4_CHANGELOG.md) - Changelog détaillé Phase 4
- [CIRCLES.md](CIRCLES.md) - Documentation circles
- [ProjectContext](../gathering/agents/project_context.py) - Code source
- [CircleStore](../gathering/orchestration/circle_store.py) - Code source
