"""
Agent Persona - Persistent identity for agents.
Defines who the agent is, how it behaves, and its expertise.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class AgentPersona:
    """
    Persistent identity of an agent.

    The persona defines:
    - Who the agent is (name, role)
    - How it communicates (style, traits)
    - What it's good at (specializations)
    - Its preferences (coding style, etc.)
    """

    id: Optional[int] = None
    name: str = ""
    role: str = ""  # "Architecte", "Développeur Senior", "Code Reviewer"

    # Base system prompt
    base_prompt: str = ""

    # Personality traits
    traits: List[str] = field(default_factory=list)
    # e.g., ["rigoureux", "pragmatique", "pédagogue"]

    # Communication style
    communication_style: str = "balanced"
    # "formal", "concise", "detailed", "technical", "friendly"

    # Technical preferences
    preferences: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"indent": 4, "quotes": "double", "max_line_length": 100}

    # Areas of expertise
    specializations: List[str] = field(default_factory=list)
    # e.g., ["python", "architecture", "security", "testing"]

    # Languages the agent speaks
    languages: List[str] = field(default_factory=lambda: ["en", "fr"])

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def build_system_prompt(
        self,
        project_context: Optional["ProjectContext"] = None,
        additional_context: str = "",
    ) -> str:
        """
        Build the complete system prompt with persona and context.

        Args:
            project_context: Project-specific context to include
            additional_context: Any additional context to append

        Returns:
            Complete system prompt for the LLM
        """
        sections = []

        # Base prompt
        if self.base_prompt:
            sections.append(self.base_prompt)

        # Role and identity
        role_section = self._build_role_section()
        if role_section:
            sections.append(role_section)

        # Project context
        if project_context:
            sections.append(f"## Contexte Projet\n{project_context.to_prompt()}")

        # Specializations
        if self.specializations:
            sections.append(
                f"## Tes Spécialisations\n{', '.join(self.specializations)}"
            )

        # Additional context
        if additional_context:
            sections.append(additional_context)

        return "\n\n".join(sections)

    def _build_role_section(self) -> str:
        """Build the role/identity section of the prompt."""
        lines = ["## Ton Rôle"]

        if self.name and self.role:
            lines.append(f"Tu es {self.name}, {self.role}.")
        elif self.name:
            lines.append(f"Tu es {self.name}.")

        if self.traits:
            lines.append(f"Traits: {', '.join(self.traits)}")

        if self.communication_style:
            style_descriptions = {
                "formal": "Tu communiques de manière formelle et professionnelle.",
                "concise": "Tu es concis et vas droit au but.",
                "detailed": "Tu donnes des explications détaillées.",
                "technical": "Tu utilises un vocabulaire technique précis.",
                "friendly": "Tu es amical et accessible.",
                "balanced": "Tu adaptes ton style au contexte.",
            }
            desc = style_descriptions.get(self.communication_style, "")
            if desc:
                lines.append(f"Style: {desc}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "base_prompt": self.base_prompt,
            "traits": self.traits,
            "communication_style": self.communication_style,
            "preferences": self.preferences,
            "specializations": self.specializations,
            "languages": self.languages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPersona":
        """Create persona from dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            role=data.get("role", ""),
            base_prompt=data.get("base_prompt", ""),
            traits=data.get("traits", []),
            communication_style=data.get("communication_style", "balanced"),
            preferences=data.get("preferences", {}),
            specializations=data.get("specializations", []),
            languages=data.get("languages", ["en", "fr"]),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )


# Pre-defined personas for common roles

ARCHITECT_PERSONA = AgentPersona(
    name="Architecte",
    role="Architecte Principal",
    base_prompt="""Tu es l'architecte principal du projet.
Tu supervises la qualité globale, fais les code reviews, et t'assures que l'architecture reste cohérente.
Tu prends des décisions techniques importantes et guides l'équipe.""",
    traits=["rigoureux", "pédagogue", "visionnaire"],
    communication_style="detailed",
    specializations=["architecture", "security", "review", "python", "design-patterns"],
)

SENIOR_DEV_PERSONA = AgentPersona(
    name="Dev Senior",
    role="Développeur Senior",
    base_prompt="""Tu es développeur senior.
Tu implémentes les features, écris les tests, et documentes ton travail.
Tu mentores les autres développeurs et partages tes connaissances.""",
    traits=["efficace", "pragmatique", "collaboratif"],
    communication_style="concise",
    specializations=["python", "testing", "api", "documentation"],
)

CODE_SPECIALIST_PERSONA = AgentPersona(
    name="Spécialiste Code",
    role="Spécialiste Code & Optimisation",
    base_prompt="""Tu es spécialiste du code.
Tu optimises les performances, debug les problèmes complexes, et t'assures de la qualité du code.
Tu analyses le code en profondeur.""",
    traits=["méticuleux", "analytique", "performant"],
    communication_style="technical",
    specializations=["python", "optimization", "debugging", "algorithms", "profiling"],
)

QA_PERSONA = AgentPersona(
    name="QA Engineer",
    role="Ingénieur Qualité",
    base_prompt="""Tu es ingénieur qualité.
Tu écris et maintiens les tests, t'assures de la couverture, et valides les fonctionnalités.
Tu traques les bugs et t'assures que le code est robuste.""",
    traits=["minutieux", "systématique", "exigeant"],
    communication_style="detailed",
    specializations=["testing", "bdd", "tdd", "qa", "automation"],
)
