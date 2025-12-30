"""
Demo: Agent analysant le projet GatheRing
==========================================

Cet exemple montre un agent qui :
1. Charge le projet GatheRing
2. Analyse la structure du projet
3. Lit le README
4. Identifie les technologies utilisées
5. Propose des améliorations
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gathering.agents.wrapper import AgentWrapper, AgentConfig
from gathering.agents.persona import AgentPersona
from gathering.llm.providers import LLMProviderFactory


async def demo_agent_on_gathering_project():
    """Démo d'un agent analysant le projet GatheRing."""

    print("=" * 80)
    print("DEMO: Agent Analysant le Projet GatheRing")
    print("=" * 80)
    print()

    # 1. Créer persona
    print("📝 Création de l'agent Sophie (AI Researcher)...")
    sophie_persona = AgentPersona(
        name="Dr. Sophie Chen",
        role="Lead AI Researcher & Python Expert",
        traits=["analytical", "thorough", "pragmatic"],
        specializations=["python", "architecture", "llm", "postgresql"],
        communication_style="professional and detailed",
    )

    # 2. Créer LLM provider (Anthropic Claude)
    print("🤖 Initialisation du LLM (Claude Sonnet 4)...")

    # Vérifier API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY non trouvée dans l'environnement")
        print("   Définissez-la avec: export ANTHROPIC_API_KEY='your-key'")
        return

    llm = LLMProviderFactory.create(
        provider_name="anthropic",
        config={
            "model": "claude-sonnet-4-20250514",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        },
    )

    # 3. Créer agent wrapper
    print("🎭 Création de AgentWrapper...")
    agent = AgentWrapper(
        agent_id=1,
        persona=sophie_persona,
        llm=llm,
        config=AgentConfig(
            allow_tools=True,
            max_iterations=5,
            temperature=0.3,  # Plus déterministe pour l'analyse
        ),
    )

    # 4. Charger le projet GatheRing
    print("📁 Chargement du projet GatheRing...")
    project_path = str(project_root)
    print(f"   Chemin: {project_path}")

    project = agent.load_project_context(project_path, project_id=1)

    print(f"   ✅ Projet chargé: {project.name}")
    print(f"   - Python: {project.python_version}")
    print(f"   - venv: {project.venv_path}")
    print(f"   - Outils: {', '.join(f'{k}={v}' for k, v in list(project.tools.items())[:5])}")
    print()

    # 5. Questions à l'agent
    questions = [
        {
            "title": "📖 Analyse du README",
            "question": "Lis le README.md et résume en 3-4 phrases ce que fait GatheRing.",
        },
        {
            "title": "🏗️ Architecture du Projet",
            "question": """Analyse la structure du projet (dossiers gathering/, tests/, docs/).
Quels sont les modules principaux et leur rôle ?""",
        },
        {
            "title": "🔧 Technologies Détectées",
            "question": """D'après les fichiers du projet, quelles sont les technologies principales utilisées ?
Liste : framework web, base de données, LLM providers, outils de test.""",
        },
        {
            "title": "📊 Analyse du Code",
            "question": """Lis le fichier gathering/agents/wrapper.py et explique :
1. Quel est le rôle de la classe AgentWrapper ?
2. Comment gère-t-elle le contexte projet ?""",
        },
    ]

    # 6. Poser les questions
    for i, item in enumerate(questions, 1):
        print("=" * 80)
        print(f"{item['title']}")
        print("=" * 80)
        print(f"Question: {item['question']}")
        print()
        print("🤔 Sophie réfléchit...")

        try:
            response = await agent.chat(
                item['question'],
                include_memories=False,  # Pas de RAG pour cette démo
                allow_tools=True,
            )

            print("💬 Réponse de Sophie:")
            print("-" * 80)
            print(response.content)
            print("-" * 80)

            if response.tool_calls:
                print(f"\n🔨 Outils utilisés: {len(response.tool_calls)}")
                for tc in response.tool_calls[:3]:  # Afficher max 3
                    print(f"   - {tc.get('name', 'unknown')}")

            print()

        except Exception as e:
            print(f"❌ Erreur: {e}")
            print()
            continue

    # 7. Question bonus avec mémoire du contexte
    print("=" * 80)
    print("🎯 Question Synthèse")
    print("=" * 80)
    print()

    synthesis_question = """D'après ton analyse du projet GatheRing, propose 3 améliorations concrètes
que l'on pourrait apporter au code ou à l'architecture."""

    print(f"Question: {synthesis_question}")
    print()
    print("🤔 Sophie synthétise...")

    try:
        response = await agent.chat(synthesis_question, include_memories=False)

        print("💡 Suggestions de Sophie:")
        print("-" * 80)
        print(response.content)
        print("-" * 80)
        print()

    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()

    # 8. Résumé
    print("=" * 80)
    print("✅ DEMO TERMINÉE")
    print("=" * 80)
    print()
    print("Résumé de ce qui a été démontré:")
    print("  ✅ Agent a chargé le projet GatheRing avec contexte auto-détecté")
    print("  ✅ Agent a lu README.md en utilisant chemin relatif")
    print("  ✅ Agent a analysé la structure du projet")
    print("  ✅ Agent a lu du code source (wrapper.py)")
    print("  ✅ Agent a proposé des améliorations")
    print()
    print("L'agent peut maintenant travailler sur N'IMPORTE QUEL projet Python ! 🚀")
    print()


if __name__ == "__main__":
    # Load .env
    from dotenv import load_dotenv
    load_dotenv()

    # Run demo
    asyncio.run(demo_agent_on_gathering_project())
