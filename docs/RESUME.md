# GatheRing ䷬ - Résumé du Projet

## Qu'est-ce que GatheRing ?

Un framework multi-agents IA permettant de créer des agents autonomes avec personnalités, mémoire et compétences, qui peuvent collaborer en équipes ("Circles").

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        DASHBOARD                             │
│                   React + TypeScript                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                         │
├──────────────┬───────────────┬───────────────┬──────────────┤
│   Agents     │  Orchestration │     RAG       │    Skills    │
│  (Persona,   │   (Circles,    │  (Embeddings, │  (Web, Shell,│
│   Memory,    │   Facilitator, │   VectorStore,│   HTTP, Code,│
│   Session)   │   Events)      │   Knowledge)  │   Social)    │
└──────────────┴───────────────┴───────────────┴──────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              PostgreSQL + pgvector                           │
│         (Agents, Circles, Memories, Embeddings)              │
└─────────────────────────────────────────────────────────────┘
```

## Fonctionnalités Clés

Module | Description
-------|------------
Agents | Persona, mémoire persistante, sessions, objectifs
Circles | Équipes d'agents avec facilitateur et routage de tâches
LLM | Anthropic, OpenAI, DeepSeek, Ollama (local)
RAG | Recherche sémantique via pgvector (1536 dims)
Skills | Web, Shell, HTTP, Social, Code execution (sandboxed)
Dashboard |UI React pour gérer agents, tâches, schedules, goals

## Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/alkimya/gathering.git
cd gathering
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Éditer .env avec vos clés API (ANTHROPIC_API_KEY, OPENAI_API_KEY, DATABASE_URL)

# 3. Database
python -m gathering.db.setup

# 4. Lancer
uvicorn gathering.api:app --reload        # Backend :8000
cd dashboard && npm install && npm run dev # Frontend :5173
```

## Cas d'Usage

- Équipe de dev virtuelle : Agents spécialisés (architecte, dev, reviewer) collaborant sur du code
- Assistants autonomes : Agents avec mémoire long-terme et objectifs auto-gérés
- Automatisation : Tâches planifiées, webhooks, intégration API
- Recherche & analyse : RAG sur documentation, web scraping, social media monitoring

## État Actuel

- Phases 1-10 : Core, Security, LLM, Skills, Orchestration, API, Dashboard, RAG, Autonomy
- Phase 11 : Advanced Skills (Web, Shell, HTTP, Social, Code) - terminée
- Phase 12 : Production (Auth, Rate limiting, Docker) - à venir
