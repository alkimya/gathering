#!/usr/bin/env python3
"""
Import personas from markdown files into the database.

Usage:
    python scripts/import_personas.py
"""

import re
import sys
from pathlib import Path

# Add pycopg to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pycopg"))

from pycopg import Database


def parse_persona_markdown(filepath: Path) -> dict:
    """Parse a persona markdown file and extract structured data."""
    content = filepath.read_text(encoding="utf-8")

    persona = {
        "name": filepath.stem,  # filename without extension (slug)
        "display_name": None,
        "role": None,
        "location": None,
        "languages": [],
        "base_prompt": None,
        "full_prompt": content,
        "traits": [],
        "communication_style": "professional",
        "work_ethic": [],
        "motto": None,
        "collaboration_notes": None,
        "competencies": [],
        "specializations": [],
        "default_model_id": None,
        "default_temperature": 0.7,
        "description": None,
        "icon": None,
        "is_builtin": False,
        "category": "tech",  # default
    }

    # Extract display name - prefer **Name**: field over # header
    explicit_name = re.search(r"\*\*Name\*\*:\s*(.+?)(?:\n|$)", content)
    if explicit_name:
        persona["display_name"] = explicit_name.group(1).strip()
    else:
        # Fallback to first # header
        name_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if name_match:
            persona["display_name"] = name_match.group(1).strip()

    # Extract role from Identity section
    role_match = re.search(r"\*\*Role\*\*:\s*(.+?)(?:\n|$)", content)
    if role_match:
        persona["role"] = role_match.group(1).strip()

    # Extract location
    location_match = re.search(r"\*\*Location\*\*:\s*(.+?)(?:\n|$)", content)
    if location_match:
        persona["location"] = location_match.group(1).strip()

    # Extract languages
    lang_match = re.search(r"\*\*Languages?\*\*:\s*(.+?)(?:\n|$)", content)
    if lang_match:
        langs_str = lang_match.group(1).strip()
        # Parse languages like "Arabic (native), English (fluent)"
        langs = re.findall(r"([A-Za-z]+)\s*\([^)]+\)", langs_str)
        if not langs:
            # Try simpler format
            langs = [l.strip() for l in langs_str.split(",")]
        persona["languages"] = langs

    # Extract model preference
    model_match = re.search(r"\*\*Model\*\*:\s*(\w+)", content, re.IGNORECASE)
    if model_match:
        model_name = model_match.group(1).lower()
        # Map model names to IDs (from database)
        model_map = {
            "sonnet": 2,  # claude-sonnet-4-20250514
            "opus": 1,    # claude-opus-4-20250514
            "haiku": 3,   # claude-3-5-haiku-20241022
        }
        persona["default_model_id"] = model_map.get(model_name, 2)  # default to sonnet

    # Extract motto
    motto_match = re.search(r"\*\*Motto\*\*:\s*\*?[\"']?(.+?)[\"']?\*?\s*$", content, re.MULTILINE)
    if motto_match:
        persona["motto"] = motto_match.group(1).strip().strip('"\'*')

    # Extract traits from Personal Traits section
    traits_section = re.search(r"Personal Traits.*?(?=##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if traits_section:
        traits_text = traits_section.group(0)
        strengths_match = re.search(r"\*\*Strengths?\*\*:\s*(.+?)(?:\n\*\*|\n-|\Z)", traits_text, re.DOTALL)
        if strengths_match:
            traits_str = strengths_match.group(1).strip()
            traits = [t.strip() for t in re.split(r"[,\n]", traits_str) if t.strip()]
            persona["traits"] = traits[:10]  # Limit to 10 traits

    # Extract communication style
    comm_match = re.search(r"\*\*Communication\*\*:\s*(.+?)(?:\n|$)", content)
    if comm_match:
        comm = comm_match.group(1).strip().lower()
        if "technical" in comm or "precise" in comm:
            persona["communication_style"] = "technical"
        elif "detail" in comm:
            persona["communication_style"] = "detailed"
        elif "enthousiast" in comm or "enthusiast" in comm:
            persona["communication_style"] = "enthusiastic"
        elif "friendly" in comm:
            persona["communication_style"] = "friendly"
        else:
            persona["communication_style"] = "professional"

    # Extract specializations from Technical Expertise section
    tech_section = re.search(r"Technical Expertise.*?(?=##\s+[A-Z]|\Z)", content, re.DOTALL | re.IGNORECASE)
    if tech_section:
        tech_text = tech_section.group(0)
        # Look for subsection headers and bullet points
        specs = re.findall(r"###\s+(.+?)(?:\n|$)", tech_text)
        if not specs:
            # Try to extract from bullet points
            specs = re.findall(r"[-*]\s+([A-Za-z0-9/&+ ]+)\s*(?:\(|:|\n)", tech_text)
        persona["specializations"] = [s.strip().lower().replace(" ", "-") for s in specs[:10]]

    # Extract work ethic
    work_ethic_match = re.search(r"\*\*Work Ethic\*\*:\s*\n((?:[-*].*\n)+)", content)
    if work_ethic_match:
        work_lines = work_ethic_match.group(1).strip().split("\n")
        persona["work_ethic"] = [
            line.strip().lstrip("-* ").strip('"\'')
            for line in work_lines
            if line.strip()
        ][:5]

    # Create base_prompt (short description)
    if persona["role"] and persona["location"]:
        persona["base_prompt"] = f"{persona['role']} based in {persona['location']}."
    elif persona["role"]:
        persona["base_prompt"] = persona["role"]

    # Create description
    background_match = re.search(r"##\s*Background\s*\n(.+?)(?=##|\Z)", content, re.DOTALL)
    if background_match:
        desc = background_match.group(1).strip()
        # Get first 2 sentences
        sentences = re.split(r"(?<=[.!?])\s+", desc)
        persona["description"] = " ".join(sentences[:2]).strip()

    # Determine category based on role/specializations
    role_lower = (persona["role"] or "").lower()
    if any(k in role_lower for k in ["game", "creative", "design", "art", "music"]):
        persona["category"] = "creative"
    elif any(k in role_lower for k in ["business", "product", "manager", "lead"]):
        persona["category"] = "business"
    elif any(k in role_lower for k in ["coach", "mentor", "advisor"]):
        persona["category"] = "coaching"
    elif any(k in role_lower for k in ["legal", "compliance", "audit"]):
        persona["category"] = "legal"
    else:
        persona["category"] = "tech"

    return persona


def insert_persona(db: Database, persona: dict) -> int | None:
    """Insert a persona into the database. Returns the id or None on error."""
    try:
        # Check if persona already exists by display_name
        existing = db.fetch_one(
            "SELECT id FROM agent.personas WHERE display_name = %s",
            [persona["display_name"]]
        )

        if existing:
            # Update existing
            db.execute(
                """
                UPDATE agent.personas SET
                    role = %s,
                    languages = %s,
                    base_prompt = %s,
                    full_prompt = %s,
                    traits = %s,
                    communication_style = %s,
                    work_ethic = %s,
                    motto = %s,
                    collaboration_notes = %s,
                    specializations = %s,
                    default_model_id = %s,
                    description = %s,
                    icon = %s,
                    is_builtin = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                [
                    persona["role"],
                    persona["languages"],
                    persona["base_prompt"],
                    persona["full_prompt"],
                    persona["traits"],
                    persona["communication_style"],
                    persona["work_ethic"],
                    persona["motto"],
                    persona["collaboration_notes"],
                    persona["specializations"],
                    persona["default_model_id"],
                    persona["description"],
                    persona["icon"],
                    persona["is_builtin"],
                    existing["id"],
                ],
            )
            return existing["id"]
        else:
            # Insert new
            result = db.execute(
                """
                INSERT INTO agent.personas (
                    display_name, role, languages,
                    base_prompt, full_prompt, traits, communication_style,
                    work_ethic, motto, collaboration_notes,
                    specializations, default_model_id,
                    description, icon, is_builtin
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s
                )
                RETURNING id
                """,
                [
                    persona["display_name"],
                    persona["role"],
                    persona["languages"],
                    persona["base_prompt"],
                    persona["full_prompt"],
                    persona["traits"],
                    persona["communication_style"],
                    persona["work_ethic"],
                    persona["motto"],
                    persona["collaboration_notes"],
                    persona["specializations"],
                    persona["default_model_id"],
                    persona["description"],
                    persona["icon"],
                    persona["is_builtin"],
                ],
            )
            return result[0]["id"] if result else None
    except Exception as e:
        print(f"Error inserting {persona['display_name']}: {e}")
        return None


def main():
    """Main function to import all personas."""
    # Find personas directory
    base_dir = Path(__file__).parent.parent
    personas_dir = base_dir / "personas"

    if not personas_dir.exists():
        print(f"Personas directory not found: {personas_dir}")
        return 1

    # Connect to database
    env_path = base_dir / ".env"
    db = Database.from_env(str(env_path))

    # Get existing personas
    existing = db.execute("SELECT id, display_name FROM agent.personas")
    existing_names = {row["display_name"] for row in existing}

    # Skip Sophie and Olivia (already in database with custom data)
    skip_display_names = {"Dr. Sophie Chen", "Olivia Nakamoto"}

    # Find all markdown files
    persona_files = sorted(personas_dir.glob("*.md"))
    print(f"Found {len(persona_files)} persona files")

    imported = 0
    skipped = 0
    errors = 0

    for filepath in persona_files:
        try:
            persona = parse_persona_markdown(filepath)
            display_name = persona["display_name"]

            if display_name in skip_display_names:
                print(f"Skipping {display_name} (manual entry)")
                skipped += 1
                continue

            result_id = insert_persona(db, persona)
            if result_id is not None:
                status = "updated" if display_name in existing_names else "imported"
                print(f"✓ {display_name} (id={result_id}) - {status}")
                imported += 1
            else:
                errors += 1
        except Exception as e:
            print(f"✗ Error processing {filepath}: {e}")
            errors += 1

    print(f"\nSummary: {imported} imported, {skipped} skipped, {errors} errors")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
