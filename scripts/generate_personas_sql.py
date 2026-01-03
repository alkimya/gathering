#!/usr/bin/env python3
"""Generate SQL migration for all personas from markdown files."""

import re
from pathlib import Path


def escape_sql(text: str) -> str:
    """Escape single quotes for SQL."""
    if text is None:
        return ""
    return text.replace("'", "''")


def extract_field(content: str, field_name: str, default: str = "") -> str:
    """Extract a field from markdown content (handles multiple formats)."""
    if not content:
        return default

    # Try multiple patterns
    patterns = [
        rf"\*\*{field_name}\*\*:\s*(.+?)(?:\n|$)",  # **Name**: value
        rf"- \*\*{field_name}\*\*:\s*(.+?)(?:\n|$)",  # - **Name**: value
        rf"\*{field_name}\*:\s*(.+?)(?:\n|$)",  # *Name*: value
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match and match.group(1):
            return match.group(1).strip()
    return default


def extract_languages(content: str) -> list[str]:
    """Extract languages from content."""
    lang_raw = extract_field(content, "Languages?")
    if not lang_raw:
        return ["English"]

    # Parse "French (native), English (fluent)" format
    lang_matches = re.findall(r"(\w+(?:\s+\w+)?)\s*(?:\([^)]+\))?", lang_raw)
    languages = [l.strip() for l in lang_matches if l.strip() and len(l.strip()) > 1]
    return languages[:5] if languages else ["English"]


def extract_traits(content: str) -> list[str]:
    """Extract personality traits."""
    traits = []

    # Look in Personal Traits section
    traits_match = re.search(r"\*\*Strengths?\*\*[:\s]*(.+?)(?:\n\*\*|\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if traits_match:
        raw = traits_match.group(1)
        # Handle comma-separated
        if "," in raw and len(raw) < 200:
            traits = [t.strip() for t in raw.split(",")]
        else:
            # Handle bullet points
            traits = re.findall(r"[-•]\s*(.+?)(?:\n|$)", raw)

    # Also look in Core Competencies box
    if not traits:
        box_match = re.search(r"```text.*?Expert Level.*?```", content, re.DOTALL | re.IGNORECASE)
        if box_match:
            items = re.findall(r"[•]\s*([^\n│]+)", box_match.group(0))
            traits = [item.strip() for item in items if item.strip()]

    # Clean up traits
    cleaned = []
    for t in traits:
        t = t.strip()
        if t and len(t) > 2:
            t = re.sub(r"\*\*", "", t)
            t = re.sub(r"\([^)]+\)", "", t).strip()
            if t and t not in cleaned:
                cleaned.append(t)

    return cleaned[:10]


def extract_competencies(content: str) -> list[str]:
    """Extract technical competencies."""
    competencies = []

    # Look for Technical Expertise section
    sections = ["Technical Expertise", "Skills", "Competencies", "Core Competencies"]
    for section in sections:
        pattern = rf"(?:##\s*)?{section}.*?(?=##\s+[A-Z]|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            section_text = match.group(0)
            # Get list items
            items = re.findall(r"^[-•]\s*(.+?)$", section_text, re.MULTILINE)
            competencies.extend([i.strip() for i in items if i.strip()])
            if competencies:
                break

    # Also look in box format
    if not competencies:
        box_match = re.search(r"```text.*?```", content, re.DOTALL)
        if box_match:
            items = re.findall(r"[•]\s*([^\n│]+)", box_match.group(0))
            competencies = [item.strip() for item in items if item.strip()]

    # Clean up
    cleaned = []
    for c in competencies:
        c = c.strip()
        if c and len(c) > 2:
            c = re.sub(r"\*\*", "", c)
            c = re.sub(r"\([^)]+\)", "", c).strip()
            if c and c not in cleaned:
                cleaned.append(c)

    return cleaned[:15]


def extract_work_ethic(content: str) -> list[str]:
    """Extract work ethic items."""
    ethics = []

    # Look for Work Ethic section
    match = re.search(r"\*\*Work Ethic\*\*[:\s]*(.+?)(?:\n\*\*|\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if match:
        raw = match.group(1)
        ethics = re.findall(r'[-•]\s*["\']?([^"\'\n]+)["\']?', raw)

    # Clean up
    cleaned = []
    for e in ethics:
        e = e.strip()
        if e and len(e) > 5:
            e = re.sub(r"^\*+|\*+$", "", e)  # Remove asterisks
            if e and e not in cleaned:
                cleaned.append(e)

    return cleaned[:5]


def extract_motto(content: str) -> str:
    """Extract motto."""
    patterns = [
        r'\*\*Motto\*\*:\s*\*?"?([^"\*\n]+)"?\*?',
        r'Motto:\s*\*?"?([^"\*\n]+)"?\*?',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match and match.group(1):
            motto = match.group(1).strip()
            motto = re.sub(r"^\*+|\*+$", "", motto)  # Remove asterisks
            return motto
    return ""


def extract_communication_style(content: str) -> str:
    """Extract or determine communication style."""
    # Look for explicit communication field
    comm = extract_field(content, "Communication")
    if comm:
        comm_lower = comm.lower()
        if "technical" in comm_lower or "formal" in comm_lower:
            return "technical"
        elif "casual" in comm_lower or "friendly" in comm_lower or "warm" in comm_lower:
            return "friendly"
        elif "direct" in comm_lower or "concise" in comm_lower:
            return "concise"
        elif "detail" in comm_lower:
            return "detailed"

    # Determine from content
    content_lower = content.lower()
    if "technical" in content_lower and "communication" in content_lower:
        return "technical"
    elif "friendly" in content_lower or "approachable" in content_lower:
        return "friendly"
    elif "direct" in content_lower or "concise" in content_lower:
        return "concise"

    return "professional"


def determine_category(content: str, role: str) -> str:
    """Determine persona category."""
    content_lower = content.lower()
    role_lower = role.lower()

    # Check role first
    if any(w in role_lower for w in ["architect", "engineer", "developer", "devops", "security"]):
        if any(w in content_lower for w in ["defi", "blockchain", "solana", "crypto", "web3"]):
            return "web3"
        return "tech"

    if any(w in role_lower for w in ["designer", "artist", "creative", "animator", "illustrator"]):
        return "creative"

    if any(w in role_lower for w in ["coach", "mentor", "advisor"]):
        return "coaching"

    if any(w in role_lower for w in ["lawyer", "attorney", "legal", "compliance"]):
        return "legal"

    if any(w in role_lower for w in ["product", "marketing", "business", "sales"]):
        return "business"

    if any(w in role_lower for w in ["trading", "quantitative", "analyst"]):
        return "web3"

    # Check content
    if any(w in content_lower for w in ["defi", "blockchain", "solana", "trading", "quantitative", "crypto", "nft", "gamefi"]):
        return "web3"
    if any(w in content_lower for w in ["lawyer", "legal", "compliance", "attorney", "privacy"]):
        return "legal"
    if any(w in content_lower for w in ["coach", "mentor", "leadership", "career", "agile"]):
        return "coaching"
    if any(w in content_lower for w in ["artist", "designer", "creative", "3d", "motion", "animation", "illustrat"]):
        return "creative"
    if any(w in content_lower for w in ["marketing", "business development", "product manager", "sales"]):
        return "business"

    return "tech"


def parse_persona(filepath: Path) -> dict:
    """Parse a persona markdown file."""
    content = filepath.read_text(encoding="utf-8")
    name = filepath.stem

    # Extract fields
    display_name = extract_field(content, "Name")
    if not display_name:
        # Try from title
        title_match = re.search(r"^#\s*(.+?)$", content, re.MULTILINE)
        if title_match:
            display_name = title_match.group(1).strip()
            display_name = re.sub(r"^👩‍💻|^👨‍💻|^🎨|^⚖️", "", display_name).strip()
            display_name = re.sub(r"^Persona\s*-?\s*", "", display_name).strip()

    role = extract_field(content, "Role")
    location = extract_field(content, "Location")
    languages = extract_languages(content)
    model_pref = extract_field(content, "Model")

    traits = extract_traits(content)
    competencies = extract_competencies(content)
    work_ethic = extract_work_ethic(content)
    motto = extract_motto(content)
    comm_style = extract_communication_style(content)
    category = determine_category(content, role)

    return {
        "name": name,
        "display_name": display_name or name.replace("_", " ").title(),
        "role": role or "AI Agent",
        "location": location,
        "languages": languages,
        "traits": traits,
        "communication_style": comm_style,
        "work_ethic": work_ethic,
        "motto": motto,
        "competencies": competencies,
        "specializations": [],
        "category": category,
        "model_pref": model_pref,
        "full_prompt": content,
    }


def format_array(items: list[str]) -> str:
    """Format a Python list as PostgreSQL array literal."""
    if not items:
        return "'{}'"
    escaped = [escape_sql(item) for item in items if item]
    if not escaped:
        return "'{}'"
    return "ARRAY[" + ", ".join(f"'{item}'" for item in escaped) + "]"


def generate_sql(personas: list[dict]) -> str:
    """Generate SQL INSERT statements for personas."""
    lines = [
        "-- GatheRing Database Migration",
        "-- Migration 003: Seed Personas",
        f"-- Description: Insert all {len(personas)} personas from markdown files",
        "-- Auto-generated by scripts/generate_personas_sql.py",
        "",
        "-- =============================================================================",
        "-- PERSONAS",
        "-- =============================================================================",
        "",
        "-- Get default model ID",
        "DO $$",
        "DECLARE",
        "    v_default_model_id BIGINT;",
        "    v_opus_model_id BIGINT;",
        "BEGIN",
        "    SELECT id INTO v_default_model_id FROM agent.models WHERE name = 'claude-sonnet-4' LIMIT 1;",
        "    SELECT id INTO v_opus_model_id FROM agent.models WHERE name = 'claude-opus-4-5' LIMIT 1;",
        "",
    ]

    for p in personas:
        # Determine model based on preference
        model_var = "v_default_model_id"
        if p.get("model_pref"):
            pref_lower = p["model_pref"].lower()
            if "opus" in pref_lower:
                model_var = "v_opus_model_id"

        loc_val = "NULL" if not p.get('location') else f"'{escape_sql(p['location'])}'"
        motto_val = "NULL" if not p.get('motto') else f"'{escape_sql(p['motto'])}'"

        lines.append(f"    -- {p['display_name']} ({p['category']})")
        lines.append("    INSERT INTO agent.personas (")
        lines.append("        name, display_name, role, location, languages,")
        lines.append("        traits, communication_style, work_ethic, motto,")
        lines.append("        competencies, specializations, category,")
        lines.append("        full_prompt, default_model_id, is_builtin")
        lines.append("    ) VALUES (")
        lines.append(f"        '{escape_sql(p['name'])}',")
        lines.append(f"        '{escape_sql(p['display_name'])}',")
        lines.append(f"        '{escape_sql(p['role'])}',")
        lines.append(f"        {loc_val},")
        lines.append(f"        {format_array(p['languages'])},")
        lines.append(f"        {format_array(p['traits'])},")
        lines.append(f"        '{escape_sql(p['communication_style'])}',")
        lines.append(f"        {format_array(p['work_ethic'])},")
        lines.append(f"        {motto_val},")
        lines.append(f"        {format_array(p['competencies'])},")
        lines.append(f"        {format_array(p['specializations'])},")
        lines.append(f"        '{escape_sql(p['category'])}',")
        lines.append(f"        '{escape_sql(p['full_prompt'])}',")
        lines.append(f"        {model_var},")
        lines.append("        TRUE")
        lines.append("    ) ON CONFLICT (name) DO UPDATE SET")
        lines.append("        display_name = EXCLUDED.display_name,")
        lines.append("        role = EXCLUDED.role,")
        lines.append("        traits = EXCLUDED.traits,")
        lines.append("        competencies = EXCLUDED.competencies,")
        lines.append("        full_prompt = EXCLUDED.full_prompt,")
        lines.append("        updated_at = NOW();")
        lines.append("")

    lines.append("END $$;")
    lines.append("")
    lines.append("-- =============================================================================")
    lines.append("-- SUMMARY")
    lines.append("-- =============================================================================")
    lines.append("")
    lines.append("-- Verify insertion")
    lines.append("-- SELECT name, display_name, role, category, array_length(traits, 1) as traits_count,")
    lines.append("--        array_length(competencies, 1) as comp_count FROM agent.personas ORDER BY category, name;")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main function."""
    personas_dir = Path("/home/loc/workspace/gathering/personas")
    output_file = Path("/home/loc/workspace/gathering/gathering/db/migrations/003_seed_personas.sql")

    # Parse all personas
    personas = []
    for md_file in sorted(personas_dir.glob("*.md")):
        try:
            persona = parse_persona(md_file)
            traits_count = len(persona['traits'])
            comp_count = len(persona['competencies'])
            print(f"✓ {persona['name']:25} | {persona['category']:10} | traits:{traits_count:2} | comp:{comp_count:2} | {persona['role'][:40]}")
            personas.append(persona)
        except Exception as e:
            print(f"✗ Error parsing {md_file.name}: {e}")

    print(f"\nTotal: {len(personas)} personas")

    # Generate SQL
    sql = generate_sql(personas)

    # Write output
    output_file.write_text(sql, encoding="utf-8")
    print(f"\n✓ Generated: {output_file}")

    # Category summary
    from collections import Counter
    categories = Counter(p["category"] for p in personas)
    print("\nBy category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
