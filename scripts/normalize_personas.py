#!/usr/bin/env python3
"""Normalize all personas to the same format, adding missing sections."""

import re
from pathlib import Path

# Mottos by category/role keywords
MOTTOS = {
    "architect": "Make it work, make it right, make it fast - in that order",
    "engineer": "Simplicity is the ultimate sophistication",
    "security": "Trust nothing, verify everything",
    "devops": "Automate everything that can be automated",
    "data": "In God we trust, all others bring data",
    "frontend": "Design is not just what it looks like, it's how it works",
    "backend": "Premature optimization is the root of all evil",
    "defi": "Code is law, but tests are the constitution",
    "blockchain": "Not your keys, not your coins",
    "trading": "The trend is your friend until it ends",
    "quantitative": "In mathematics we trust",
    "nft": "Value is in the eye of the beholder",
    "analyst": "Question everything, measure twice",
    "designer": "Less is more",
    "product": "Fall in love with the problem, not the solution",
    "marketing": "The best marketing doesn't feel like marketing",
    "writer": "Clear writing is clear thinking",
    "artist": "Art is not what you see, but what you make others see",
    "coach": "The only way to do great work is to love what you do",
    "leadership": "A leader is one who knows the way, goes the way, and shows the way",
    "agile": "Responding to change over following a plan",
    "career": "Your career is a marathon, not a sprint",
    "lawyer": "The law is reason, free from passion",
    "compliance": "Trust, but verify",
    "privacy": "Privacy is not secrecy",
    "tax": "The hardest thing to understand is the income tax",
    "startup": "Move fast and break things, but fix them faster",
    "3d": "Every pixel tells a story",
    "motion": "Animation is about creating the illusion of life",
    "sound": "Music is the space between the notes",
    "pixel": "Perfection is achieved not when there is nothing more to add, but nothing left to take away",
    "creative": "Creativity takes courage",
    "default": "Excellence is not a skill, it's an attitude"
}

# Work ethics by category
WORK_ETHICS = {
    "tech": [
        "Code is read 10x more than written",
        "Tests are documentation that never lies",
        "Premature optimization is evil, but no optimization is worse"
    ],
    "web3": [
        "Security first, features second",
        "Decentralization is not optional",
        "Smart contracts are immutable, so test thoroughly"
    ],
    "business": [
        "Data drives decisions",
        "Customer feedback is gold",
        "Ship early, iterate often"
    ],
    "creative": [
        "Inspiration exists, but it has to find you working",
        "Constraints breed creativity",
        "Done is better than perfect"
    ],
    "coaching": [
        "Lead by example",
        "Listen twice as much as you speak",
        "Growth mindset over fixed mindset"
    ],
    "legal": [
        "Precision in language prevents disputes",
        "Prevention is better than litigation",
        "Know the rules before you break them"
    ]
}


def get_motto_for_persona(content: str, name: str) -> str:
    """Determine the best motto based on persona content."""
    content_lower = content.lower()

    for keyword, motto in MOTTOS.items():
        if keyword in content_lower:
            return motto

    return MOTTOS["default"]


def get_work_ethic_for_persona(content: str) -> list[str]:
    """Determine work ethics based on persona category."""
    content_lower = content.lower()

    if any(w in content_lower for w in ["defi", "blockchain", "solana", "trading", "crypto"]):
        return WORK_ETHICS["web3"]
    elif any(w in content_lower for w in ["lawyer", "legal", "compliance"]):
        return WORK_ETHICS["legal"]
    elif any(w in content_lower for w in ["coach", "mentor", "leadership"]):
        return WORK_ETHICS["coaching"]
    elif any(w in content_lower for w in ["artist", "designer", "creative"]):
        return WORK_ETHICS["creative"]
    elif any(w in content_lower for w in ["marketing", "business", "product"]):
        return WORK_ETHICS["business"]
    else:
        return WORK_ETHICS["tech"]


def normalize_persona(filepath: Path) -> bool:
    """Normalize a persona file, adding missing sections."""
    content = filepath.read_text(encoding="utf-8")
    modified = False

    # Check if Personal Traits section exists
    if "## Personal Traits" not in content and "**Strengths**" not in content:
        # Find the end of the content or before --- if exists
        insert_pos = len(content)
        if "---" in content:
            insert_pos = content.rfind("---")

        # Generate sections
        motto = get_motto_for_persona(content, filepath.stem)
        work_ethic = get_work_ethic_for_persona(content)

        traits_section = f"""
## Personal Traits

**Strengths**:

- Attention to detail
- Clear technical communication
- Problem-solving mindset
- Team collaboration

**Work Ethic**:

{chr(10).join(f'- "{ethic}"' for ethic in work_ethic)}

**Motto**: *"{motto}"*

"""
        content = content[:insert_pos].rstrip() + "\n" + traits_section + content[insert_pos:]
        modified = True

    # Check if Motto exists but not in Personal Traits section
    elif "**Motto**" not in content:
        motto = get_motto_for_persona(content, filepath.stem)

        # Find where to insert - after Work Ethic if exists, or at end of Personal Traits
        work_ethic_match = re.search(r"\*\*Work Ethic\*\*:.*?(?=\n\n|\*\*Motto|\Z)", content, re.DOTALL)
        if work_ethic_match:
            insert_pos = work_ethic_match.end()
            content = content[:insert_pos] + f'\n\n**Motto**: *"{motto}"*\n' + content[insert_pos:]
            modified = True
        else:
            # Find Personal Traits section and add motto
            traits_match = re.search(r"## Personal Traits.*?(?=##|\Z)", content, re.DOTALL)
            if traits_match:
                section_end = traits_match.end()
                content = content[:section_end].rstrip() + f'\n\n**Motto**: *"{motto}"*\n\n' + content[section_end:]
                modified = True

    if modified:
        filepath.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    """Main function."""
    personas_dir = Path("/home/loc/workspace/gathering/personas")

    modified_count = 0
    for md_file in sorted(personas_dir.glob("*.md")):
        if normalize_persona(md_file):
            print(f"✓ Updated: {md_file.name}")
            modified_count += 1
        else:
            print(f"  Skipped: {md_file.name} (already complete)")

    print(f"\nTotal updated: {modified_count}")


if __name__ == "__main__":
    main()
