# Circles - Documentation

## Vue d'ensemble

Les **Circles** (cercles) sont des équipes d'agents IA qui collaborent pour accomplir des tâches. Chaque cercle possède ses propres agents, tâches et règles de fonctionnement.

## Création d'un cercle

### Paramètres

| Paramètre | Type | Description |
|-----------|------|-------------|
| `name` | string | Nom unique du cercle |
| `require_review` | boolean | Exiger une revue par un pair avant validation (défaut: true) |
| `auto_route` | boolean | Router automatiquement les tâches vers l'agent le plus adapté (défaut: true) |
| `agents` | Agent[] | Agents membres du cercle (sélectionnés à la création) |

### Interface Dashboard

1. Cliquer sur le bouton **+** dans la page Circles
2. Entrer le nom du cercle
3. Configurer les options :
   - **Require Review** : Active la revue obligatoire des tâches
   - **Auto Route** : Active le routage intelligent des tâches
4. Sélectionner les agents à inclure dans le cercle
5. Cliquer sur **Create**

Les agents sélectionnés sont automatiquement ajoutés au cercle avec leurs compétences.

### Mode Démonstration

Lorsque le backend ne retourne aucun cercle, le dashboard affiche des cercles de démonstration (dev-team, code-review, documentation) avec des tâches fictives. Ces cercles de démo sont en **lecture seule** :

- Les tâches ne peuvent pas être créées
- Les actions start/stop/delete sont désactivées
- Un message "Demo circle - Create a real circle to add tasks" est affiché

Pour activer toutes les fonctionnalités, créez un vrai cercle via le bouton **+**.

## Gestion des tâches

### Création de tâche

Depuis la vue détaillée d'un cercle :

1. Entrer le **titre** de la tâche
2. Optionnel : Ajouter une **description**
3. Sélectionner la **priorité** (Low, Medium, High, Critical)
4. Cliquer sur **Required skills** pour spécifier les compétences requises
5. Soumettre avec le bouton **+**

### Compétences requises

Les compétences disponibles incluent :
- `python`, `typescript`, `javascript`, `react`
- `api`, `testing`, `code_review`
- `documentation`, `security`, `database`, `devops`

Ces compétences sont utilisées par le **Facilitator** pour router la tâche vers l'agent le plus adapté.

### Priorités

| Frontend | Backend (1-10) | Description |
|----------|----------------|-------------|
| `critical` | 1 | Priorité maximale, traitement immédiat |
| `high` | 3 | Priorité élevée |
| `medium` | 5 | Priorité normale (défaut) |
| `low` | 8 | Priorité basse |

### Feedback d'assignation

Après création d'une tâche, un message de confirmation s'affiche :
- **"Assigned to [Agent]"** : La tâche a été assignée immédiatement
- **"Routing to best agent..."** : Le routage automatique est en cours
- **"Pending assignment"** : En attente d'assignation manuelle

## Routage intelligent (Facilitator)

Le `Facilitator` est le composant qui route automatiquement les tâches vers les agents.

### Algorithme de scoring

Le score d'un agent pour une tâche est calculé ainsi :

```
Score = (Competency Match × 50%) + (Availability × 30%) + (Quality Bonus × 20%)
```

1. **Competency Match (50%)** : Correspondance entre les compétences requises et celles de l'agent
2. **Availability (30%)** : Charge de travail actuelle de l'agent
3. **Quality Bonus (20%)** : Taux d'approbation historique des tâches

### Priorité

Les tâches à haute priorité favorisent davantage la correspondance de compétences.

## Cycle de vie d'une tâche

```
pending → assigned → in_progress → [in_review] → completed
                                 ↘ failed
```

1. **pending** : Tâche créée, en attente d'assignation
2. **assigned** : Assignée à un agent
3. **in_progress** : Agent travaille sur la tâche
4. **in_review** : (Si require_review) En attente de revue par un pair
5. **completed** : Tâche terminée et validée
6. **failed** : Échec de la tâche

## API

### Créer un cercle

```bash
POST /api/circles
{
  "name": "dev-team",
  "require_review": true,
  "auto_route": true
}
```

### Ajouter un agent au cercle

```bash
POST /api/circles/{name}/agents?agent_id=1&agent_name=Sophie&provider=anthropic&model=claude-3&competencies=python,typescript&can_review=code
```

### Créer une tâche

```bash
POST /api/circles/{name}/tasks
{
  "title": "Implement authentication",
  "description": "Add JWT-based auth to the API",
  "required_competencies": ["python", "security"],
  "priority": "high"
}
```

Le champ `priority` accepte :
- Une string : `"low"`, `"medium"`, `"high"`, `"critical"`
- Un entier (1-10) : 1 = max priorité, 10 = min priorité

### Réponse

```json
{
  "id": 1,
  "title": "Implement authentication",
  "description": "Add JWT-based auth to the API",
  "status": "pending",
  "priority": 3,
  "assigned_agent_id": 1,
  "assigned_agent_name": "Sophie",
  "created_at": "2024-01-15T10:00:00Z"
}
```

## Implémentation technique

### Fichiers clés

| Fichier | Description |
|---------|-------------|
| `gathering/orchestration/circle.py` | Classe GatheringCircle |
| `gathering/orchestration/facilitator.py` | Algorithme de routage |
| `gathering/api/routers/circles.py` | Endpoints API |
| `gathering/api/schemas.py` | Schémas Pydantic |
| `dashboard/src/pages/Circles.tsx` | Interface utilisateur |
| `dashboard/src/pages/Circles.test.tsx` | Tests frontend |

### Classes principales

```python
@dataclass
class AgentHandle:
    id: int
    name: str
    provider: str
    model: str
    competencies: List[str]
    can_review: List[str]
    is_active: bool = True
    current_task_id: Optional[int] = None

@dataclass
class CircleTask:
    id: int
    title: str
    description: str
    required_competencies: List[str]
    priority: int = 5
    status: str = "pending"
    assigned_agent_id: Optional[int] = None
```

## Tests

### Backend
```bash
# Tests API et schémas
source venv/bin/activate
python -m pytest tests/ -v -k "circle"
```

### Dashboard
```bash
cd dashboard
npm test -- --run src/pages/Circles.test.tsx
```

Tests couverts :
- ✅ Rendu de la page et liste des cercles
- ✅ Affichage des indicateurs de statut
- ✅ Sélection et détail d'un cercle
- ✅ Modal de création avec sélection d'agents
- ✅ Options Require Review et Auto Route
- ✅ Création de cercle avec agents sélectionnés
- ✅ Affichage du sélecteur de compétences
- ✅ Création de tâche avec compétences
- ✅ Feedback de succès après création
