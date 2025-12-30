# Guide de Tests - GatheRing

## Vue d'ensemble

GatheRing utilise **pytest** comme framework de tests avec une couverture minimale de **80%**.

```bash
# Lancer tous les tests
source venv/bin/activate && pytest

# Lancer avec rapport de couverture
pytest --cov=gathering --cov-report=term-missing

# Lancer un fichier de tests spécifique
pytest tests/test_core_schemas.py -v
```

## Structure des Tests

```
tests/
├── test_suite_initial.py       # Tests de base du framework
├── test_api.py                 # Tests des endpoints REST API
├── test_auth.py                # Tests d'authentification
├── test_middleware.py          # Tests des middlewares FastAPI
├── test_orchestration.py       # Tests d'orchestration des cercles
├── test_core_schemas.py        # Tests des schémas Pydantic
├── test_core_competencies.py   # Tests des compétences
├── test_core_exceptions.py     # Tests des exceptions personnalisées
├── test_agents_goals.py        # Tests de gestion des objectifs
├── test_agents_persistence.py  # Tests de persistance des agents
├── test_project_context.py     # Tests du contexte projet
├── test_orchestration_background.py  # Tests des tâches de fond
└── ...
```

## Configuration de la Couverture

La configuration se trouve dans `.coveragerc`:

```ini
[run]
source = gathering
omit =
    # Modules exclus car nécessitant des dépendances externes
    gathering/skills/*           # Services externes (LLM, etc.)
    gathering/db/*               # Connexion PostgreSQL
    gathering/rag/*              # Vector DB et embeddings
    gathering/llm/providers.py   # Clés API requises
    gathering/orchestration/scheduler.py  # croniter + async

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
    @abstractmethod
```

## Exécution des Tests

### Tests Unitaires

```bash
# Tous les tests
pytest tests/ -v

# Tests d'un module spécifique
pytest tests/test_core_schemas.py -v

# Tests avec pattern
pytest -k "test_agent" -v
```

### Tests avec Couverture

```bash
# Rapport terminal
pytest --cov=gathering --cov-report=term-missing

# Rapport HTML (généré dans htmlcov/)
pytest --cov=gathering --cov-report=html
open htmlcov/index.html

# Vérification du seuil (80%)
pytest --cov=gathering --cov-fail-under=80
```

### Tests Parallèles

```bash
# Installation de pytest-xdist
pip install pytest-xdist

# Exécution parallèle
pytest -n auto
```

## Écriture des Tests

### Convention de Nommage

- Fichiers: `test_<module>.py`
- Classes: `Test<Component>`
- Méthodes: `test_<comportement_attendu>`

### Exemple de Test

```python
"""Tests pour gathering/core/schemas.py"""

import pytest
from pydantic import ValidationError
from gathering.core.schemas import AgentConfig, LLMProviderType


class TestAgentConfig:
    """Tests pour AgentConfig."""

    def test_minimal_creation(self):
        """Test de création minimale."""
        config = AgentConfig(
            name="TestAgent",
            llm_provider=LLMProviderType.OPENAI,
            model="gpt-4",
        )
        assert config.name == "TestAgent"
        assert config.temperature == 0.7  # default

    def test_name_validation(self):
        """Test de validation du nom."""
        with pytest.raises(ValidationError):
            AgentConfig(
                name="",  # invalide
                llm_provider=LLMProviderType.OPENAI,
                model="gpt-4",
            )
```

### Fixtures Communes

```python
import pytest
from fastapi.testclient import TestClient
from gathering.api.main import create_app


@pytest.fixture
def app():
    """Application de test sans auth."""
    return create_app(
        enable_auth=False,
        enable_rate_limit=False,
    )


@pytest.fixture
def client(app):
    """Client HTTP de test."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_registries():
    """Nettoie les registres entre chaque test."""
    from gathering.api.dependencies import reset_registries
    reset_registries()
    yield
    reset_registries()
```

### Tests Async

```python
import pytest


@pytest.mark.asyncio
async def test_async_operation():
    """Test d'une opération asynchrone."""
    from gathering.orchestration.events import EventBus

    bus = EventBus()
    events = []

    async def handler(data):
        events.append(data)

    bus.subscribe("test", handler)
    await bus.emit("test", {"value": 42})

    assert len(events) == 1
    assert events[0]["value"] == 42
```

## Couverture par Module

| Module | Couverture | Description |
|--------|------------|-------------|
| `core/schemas.py` | 99% | Schémas de configuration Pydantic |
| `core/competencies.py` | 100% | Gestion des compétences |
| `core/exceptions.py` | 100% | Exceptions personnalisées |
| `core/implementations.py` | 75% | Implémentations de base |
| `agents/conversation.py` | 91% | Gestion des conversations |
| `agents/session.py` | 92% | Sessions d'agents |
| `agents/project_context.py` | 96% | Contexte projet |
| `orchestration/circle.py` | 92% | Orchestration des cercles |
| `api/schemas.py` | 98% | Schémas API |

## Modules Exclus de la Couverture

Ces modules sont exclus car ils nécessitent des services externes:

1. **`gathering/skills/*`** - Skills nécessitant des API externes (LLM, etc.)
2. **`gathering/db/*`** - Connexion PostgreSQL requise
3. **`gathering/rag/*`** - Vector store et service d'embeddings
4. **`gathering/llm/providers.py`** - Clés API LLM requises
5. **`gathering/orchestration/scheduler.py`** - Dépendance croniter + async runtime

## Bonnes Pratiques

### 1. Isolation des Tests

Chaque test doit être indépendant et ne pas dépendre de l'ordre d'exécution.

```python
@pytest.fixture(autouse=True)
def isolate_test():
    """Isole chaque test."""
    # Setup
    yield
    # Teardown
```

### 2. Tests de Validation

Tester les cas valides ET invalides:

```python
def test_valid_input(self):
    """Cas valide."""
    config = Config(value=42)
    assert config.value == 42

def test_invalid_input(self):
    """Cas invalide."""
    with pytest.raises(ValidationError):
        Config(value=-1)  # Doit être positif
```

### 3. Tests Paramétrés

Pour tester plusieurs cas similaires:

```python
@pytest.mark.parametrize("status_code,is_retryable", [
    (429, True),   # Rate limit
    (500, True),   # Server error
    (400, False),  # Bad request
    (401, False),  # Unauthorized
])
def test_is_retryable(self, status_code, is_retryable):
    err = LLMProviderError("Error", status_code=status_code)
    assert err.is_retryable == is_retryable
```

### 4. Mocking

Pour les dépendances externes:

```python
from unittest.mock import AsyncMock, patch

@patch("gathering.llm.providers.anthropic_client")
async def test_with_mock(mock_client):
    mock_client.messages.create = AsyncMock(return_value={"content": "Hello"})
    # Test logic here
```

## Intégration Continue

Le fichier `pytest.ini` configure l'exécution des tests:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
```

## Commandes Utiles

```bash
# Tests avec verbose
pytest -v

# Stopper au premier échec
pytest -x

# Afficher les prints
pytest -s

# Tests modifiés uniquement (avec pytest-picked)
pytest --picked

# Profiling des tests lents
pytest --durations=10

# Générer rapport JUnit (CI)
pytest --junitxml=report.xml
```
