# GatheRing Skills Reference

Ce document décrit tous les skills disponibles pour les agents GatheRing.

## Table des matières

- [Skills GatheRing (Système)](#skills-gathering-système)
  - [goals](#goals)
  - [pipelines](#pipelines)
  - [tasks](#tasks)
  - [schedules](#schedules)
  - [circles](#circles)
- [Skills Développement](#skills-développement)
  - [git](#git)
  - [code](#code)
  - [filesystem](#filesystem)
  - [shell](#shell)
  - [test](#test)
  - [analysis](#analysis)
  - [docs](#docs)
  - [database](#database)
- [Skills IA & Web](#skills-ia--web)
  - [ai](#ai)
  - [web](#web)
  - [http](#http)
  - [scraper](#scraper)
- [Skills Déploiement](#skills-déploiement)
  - [deploy](#deploy)
  - [cloud](#cloud)
- [Skills Communication](#skills-communication)
  - [email](#email)
  - [notifications](#notifications)
  - [social](#social)
- [Skills Médias](#skills-médias)
  - [image](#image)
  - [pdf](#pdf)
- [Skills Productivité](#skills-productivité)
  - [calendar](#calendar)

---

## Skills GatheRing (Système)

Ces skills permettent aux agents de gérer les entités GatheRing et de suivre leur travail dans le dashboard.

### goals

Gestion des objectifs avec suivi de progression.

| Outil | Description |
|-------|-------------|
| `goal_create` | Créer un nouvel objectif |
| `goal_update` | Mettre à jour un objectif existant |
| `goal_list` | Lister les objectifs (filtrage par statut) |
| `goal_get` | Obtenir les détails d'un objectif |
| `goal_complete` | Marquer un objectif comme terminé |
| `goal_fail` | Marquer un objectif comme échoué |
| `goal_add_subgoal` | Ajouter un sous-objectif |

### pipelines

Définition et exécution de pipelines de travail.

| Outil | Description |
|-------|-------------|
| `pipeline_create` | Créer un nouveau pipeline |
| `pipeline_list` | Lister les pipelines disponibles |
| `pipeline_get` | Obtenir les détails d'un pipeline |
| `pipeline_run` | Exécuter un pipeline |
| `pipeline_update` | Mettre à jour un pipeline |
| `pipeline_runs` | Voir l'historique des exécutions |

### tasks

Gestion des tâches de fond autonomes.

| Outil | Description |
|-------|-------------|
| `task_start` | Démarrer une nouvelle tâche de fond |
| `task_list` | Lister les tâches en cours |
| `task_get` | Obtenir les détails d'une tâche |
| `task_steps` | Voir les étapes d'une tâche |
| `task_pause` | Mettre une tâche en pause |
| `task_resume` | Reprendre une tâche |
| `task_cancel` | Annuler une tâche |

### schedules

Planification d'actions pour exécution différée.

| Outil | Description |
|-------|-------------|
| `schedule_create` | Créer une action planifiée |
| `schedule_list` | Lister les actions planifiées |
| `schedule_get` | Obtenir les détails d'une action |
| `schedule_update` | Mettre à jour une action |
| `schedule_delete` | Supprimer une action planifiée |
| `schedule_run_now` | Exécuter immédiatement une action |

### circles

Collaboration entre agents dans des cercles.

| Outil | Description |
|-------|-------------|
| `circle_create` | Créer un nouveau cercle |
| `circle_list` | Lister les cercles |
| `circle_get` | Obtenir les détails d'un cercle |
| `circle_join` | Rejoindre un cercle |
| `circle_leave` | Quitter un cercle |
| `circle_members` | Lister les membres d'un cercle |
| `circle_message` | Envoyer un message au cercle |
| `circle_update` | Mettre à jour un cercle |

---

## Skills Développement

### git

Gestion de version Git complète.

| Outil | Description |
|-------|-------------|
| `git_status` | Afficher le statut du dépôt |
| `git_diff` | Voir les différences |
| `git_log` | Historique des commits |
| `git_add` | Ajouter des fichiers au staging |
| `git_commit` | Créer un commit |
| `git_push` | Pousser les commits |
| `git_pull` | Récupérer les changements |
| `git_branch` | Gestion des branches |
| `git_clone` | Cloner un dépôt |
| `git_create_pr` | Créer une Pull Request |
| `git_rebase` | Rebaser une branche |
| `git_stash` | Gérer le stash |
| `git_cherry_pick` | Cherry-pick un commit |

### code

Exécution et analyse de code.

| Outil | Description |
|-------|-------------|
| `python_exec` | Exécuter du code Python |
| `python_eval` | Évaluer une expression Python |
| `javascript_exec` | Exécuter du JavaScript |
| `bash_exec` | Exécuter des commandes Bash |
| `sql_exec` | Exécuter du SQL |
| `code_analyze` | Analyser du code |
| `code_format` | Formater du code |
| `repl_session` | Session REPL interactive |

### filesystem

Opérations sur le système de fichiers.

| Outil | Description |
|-------|-------------|
| `fs_read` | Lire un fichier |
| `fs_write` | Écrire dans un fichier |
| `fs_list` | Lister un répertoire |
| `fs_info` | Informations sur un fichier |
| `fs_mkdir` | Créer un répertoire |
| `fs_delete` | Supprimer un fichier/répertoire |
| `fs_copy` | Copier un fichier |
| `fs_move` | Déplacer un fichier |
| `fs_search` | Rechercher des fichiers |
| `fs_tree` | Afficher l'arborescence |

### shell

Commandes shell et recherche.

| Outil | Description |
|-------|-------------|
| `shell_exec` | Exécuter une commande shell |
| `file_read` | Lire un fichier |
| `file_list` | Lister des fichiers |
| `file_info` | Informations fichier |
| `find_files` | Trouver des fichiers |
| `grep_search` | Rechercher dans les fichiers |

### test

Exécution et analyse des tests.

| Outil | Description |
|-------|-------------|
| `test_run` | Exécuter les tests |
| `test_coverage` | Rapport de couverture |
| `test_discover` | Découvrir les tests |
| `test_last_failed` | Relancer les tests échoués |
| `test_watch` | Mode watch |
| `test_analyze_failures` | Analyser les échecs |
| `test_create` | Créer un test |

### analysis

Analyse statique du code.

| Outil | Description |
|-------|-------------|
| `analysis_lint` | Linting du code |
| `analysis_security` | Audit de sécurité |
| `analysis_complexity` | Complexité cyclomatique |
| `analysis_dependencies` | Analyse des dépendances |
| `analysis_type_check` | Vérification des types |
| `analysis_dead_code` | Détection du code mort |
| `analysis_duplicates` | Détection des duplications |
| `analysis_metrics` | Métriques de code |

### docs

Génération de documentation.

| Outil | Description |
|-------|-------------|
| `docs_analyze` | Analyser la documentation existante |
| `docs_generate_docstring` | Générer des docstrings |
| `docs_generate_readme` | Générer un README |
| `docs_extract` | Extraire la documentation |
| `docs_generate_api` | Générer doc API |
| `docs_lint` | Vérifier la documentation |
| `docs_changelog` | Générer un changelog |

### database

Opérations sur bases de données.

| Outil | Description |
|-------|-------------|
| `db_query` | Exécuter une requête SELECT |
| `db_execute` | Exécuter une requête SQL |
| `db_schema` | Afficher le schéma |
| `db_tables` | Lister les tables |
| `db_describe` | Décrire une table |
| `db_explain` | Expliquer un plan de requête |
| `db_migrate` | Exécuter les migrations |
| `db_backup` | Sauvegarder la base |

---

## Skills IA & Web

### ai

Accès aux modèles IA.

| Outil | Description |
|-------|-------------|
| `ai_complete` | Complétion de texte |
| `ai_chat` | Conversation |
| `ai_embed` | Générer des embeddings |
| `ai_vision` | Analyse d'images |
| `ai_transcribe` | Transcription audio |
| `ai_speak` | Synthèse vocale |
| `ai_summarize` | Résumer du texte |
| `ai_translate` | Traduire |
| `ai_extract` | Extraction d'informations |
| `ai_compare` | Comparer des textes |
| `ai_models` | Lister les modèles |

### web

Recherche web et Wikipedia.

| Outil | Description |
|-------|-------------|
| `web_search` | Recherche web |
| `wikipedia_search` | Recherche Wikipedia |
| `wikipedia_article` | Lire un article |
| `fetch_url` | Récupérer une URL |
| `news_search` | Recherche d'actualités |

### http

Client HTTP complet.

| Outil | Description |
|-------|-------------|
| `http_get` | Requête GET |
| `http_post` | Requête POST |
| `http_put` | Requête PUT |
| `http_delete` | Requête DELETE |
| `http_request` | Requête personnalisée |
| `api_call` | Appel API avec auth |
| `parse_json` | Parser du JSON |
| `build_url` | Construire une URL |

### scraper

Extraction de données web.

| Outil | Description |
|-------|-------------|
| `extract_links` | Extraire les liens |
| `extract_images` | Extraire les images |
| `extract_metadata` | Extraire les métadonnées |
| `extract_structured` | Extraction structurée |
| `extract_tables` | Extraire les tableaux |

---

## Skills Déploiement

### deploy

Déploiement d'applications.

| Outil | Description |
|-------|-------------|
| `deploy_docker_build` | Build Docker |
| `deploy_docker_push` | Push image |
| `deploy_docker_run` | Lancer un conteneur |
| `deploy_docker_compose` | Docker Compose |
| `deploy_status` | Statut du déploiement |
| `deploy_health_check` | Vérification santé |
| `deploy_rollback` | Rollback |
| `deploy_env_config` | Configuration env |
| `deploy_ci_trigger` | Déclencher CI/CD |
| `deploy_logs` | Logs de déploiement |

### cloud

Opérations cloud (AWS, GCP, Azure).

| Outil | Description |
|-------|-------------|
| `cloud_list_instances` | Lister les instances |
| `cloud_get_instance` | Détails d'une instance |
| `cloud_start_instance` | Démarrer une instance |
| `cloud_stop_instance` | Arrêter une instance |
| `cloud_list_buckets` | Lister les buckets |
| `cloud_list_objects` | Lister les objets |
| `cloud_upload` | Upload vers le cloud |
| `cloud_download` | Download depuis le cloud |
| `cloud_delete_object` | Supprimer un objet |
| `cloud_providers` | Providers disponibles |

---

## Skills Communication

### email

Gestion des emails.

| Outil | Description |
|-------|-------------|
| `email_send` | Envoyer un email |
| `email_read` | Lire les emails |
| `email_search` | Rechercher |
| `email_get` | Obtenir un email |
| `email_folders` | Lister les dossiers |
| `email_move` | Déplacer un email |
| `email_delete` | Supprimer |
| `email_mark` | Marquer lu/non-lu |
| `email_reply` | Répondre |
| `email_draft` | Créer un brouillon |

### notifications

Envoi de notifications.

| Outil | Description |
|-------|-------------|
| `notify_webhook` | Webhook générique |
| `notify_slack` | Message Slack |
| `notify_discord` | Message Discord |
| `notify_teams` | Message Teams |
| `notify_push_firebase` | Push Firebase |
| `notify_push_onesignal` | Push OneSignal |
| `notify_sms` | SMS |
| `notify_desktop` | Notification desktop |
| `notify_batch` | Notifications en lot |

### social

Réseaux sociaux.

| Outil | Description |
|-------|-------------|
| `twitter_search` | Recherche Twitter |
| `twitter_user_timeline` | Timeline utilisateur |
| `reddit_search` | Recherche Reddit |
| `reddit_subreddit` | Posts d'un subreddit |
| `reddit_post` | Détails d'un post |
| `github_search_repos` | Recherche GitHub |
| `github_repo_info` | Infos d'un dépôt |
| `github_issues` | Issues d'un dépôt |
| `github_trending` | Dépôts trending |
| `discord_send` | Message Discord |
| `slack_send` | Message Slack |
| `mastodon_search` | Recherche Mastodon |
| `mastodon_timeline` | Timeline Mastodon |
| `mastodon_post` | Poster sur Mastodon |
| `hackernews_top` | Top HackerNews |
| `hackernews_item` | Détails d'un item |

---

## Skills Médias

### image

Traitement d'images.

| Outil | Description |
|-------|-------------|
| `image_info` | Informations image |
| `image_resize` | Redimensionner |
| `image_crop` | Recadrer |
| `image_rotate` | Rotation |
| `image_convert` | Convertir le format |
| `image_filter` | Appliquer un filtre |
| `image_adjust` | Ajuster luminosité/contraste |
| `image_thumbnail` | Créer une miniature |
| `image_watermark` | Ajouter un watermark |
| `image_compose` | Composer des images |
| `image_to_base64` | Convertir en base64 |

### pdf

Manipulation de PDF.

| Outil | Description |
|-------|-------------|
| `pdf_read` | Lire un PDF |
| `pdf_info` | Métadonnées PDF |
| `pdf_create` | Créer un PDF |
| `pdf_merge` | Fusionner des PDFs |
| `pdf_split` | Diviser un PDF |
| `pdf_watermark` | Watermark |
| `pdf_to_images` | PDF vers images |
| `pdf_from_images` | Images vers PDF |
| `pdf_extract_images` | Extraire les images |
| `pdf_search` | Rechercher dans un PDF |

---

## Skills Productivité

### calendar

Gestion de calendrier.

| Outil | Description |
|-------|-------------|
| `calendar_list` | Lister les calendriers |
| `calendar_events` | Lister les événements |
| `calendar_get_event` | Détails d'un événement |
| `calendar_create_event` | Créer un événement |
| `calendar_update_event` | Modifier un événement |
| `calendar_delete_event` | Supprimer un événement |
| `calendar_free_slots` | Créneaux disponibles |
| `calendar_today` | Événements du jour |

---

## Configuration des Skills

Les skills sont assignés aux agents via la colonne `skill_names` dans la table `agent.agents`.

### Exemple: Assigner des skills à un agent

```sql
UPDATE agent.agents
SET skill_names = ARRAY['git', 'filesystem', 'code', 'goals', 'tasks']
WHERE id = 1;
```

### Agents actuels

| Agent | Skills |
|-------|--------|
| Dr. Sophie Chen | git, filesystem, shell, code, goals, pipelines, tasks, schedules, circles, ai, analysis, docs, deploy, http, database, test, web |
| Olivia Nakamoto | git, filesystem, shell, code, goals, pipelines, tasks, schedules, circles, ai, analysis, docs, deploy, http, database, test, web |

---

## Créer un nouveau Skill

Voir [gathering/skills/base.py](../gathering/skills/base.py) pour la classe de base.

```python
from gathering.skills.base import BaseSkill, SkillResponse
from typing import Dict, Any, List

class MonSkill(BaseSkill):
    """Description du skill."""

    name = "mon_skill"
    description = "Ce que fait ce skill"

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mon_outil",
                "description": "Description de l'outil",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "..."},
                    },
                    "required": ["param1"]
                }
            }
        ]

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> SkillResponse:
        if tool_name == "mon_outil":
            return self._mon_outil(arguments)
        return SkillResponse(success=False, error=f"Unknown tool: {tool_name}")

    def _mon_outil(self, args: Dict[str, Any]) -> SkillResponse:
        # Implémentation
        return SkillResponse(success=True, data={"result": "..."})
```

Puis enregistrer dans `gathering/skills/registry.py`:

```python
_builtin_skills = {
    # ...
    "mon_skill": "gathering.skills.mon_module:MonSkill",
}
```
