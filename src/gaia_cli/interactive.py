"""Interactive CLI helpers using questionary.

Gracefully degrades when questionary is not installed or when
running in a non-interactive context (piped stdin, CI, --yes flag).
"""

from __future__ import annotations

import os
import sys
from typing import Optional


def _has_interactive() -> bool:
    """Check if interactive mode is available and appropriate."""
    # Not a TTY (piped input, CI)
    if not sys.stdin.isatty():
        return False
    # CI environment
    if os.environ.get("CI"):
        return False
    # Check for questionary
    try:
        import questionary  # noqa: F401
        return True
    except ImportError:
        return False


def select_skill(skills: list[dict], prompt: str = "Select a skill:") -> Optional[str]:
    """Arrow-key skill picker. Returns skill ID or None if cancelled/unavailable.

    Args:
        skills: List of skill dicts with at least 'id', optionally 'type', 'level', 'description'
        prompt: The prompt message to display

    Returns:
        Selected skill ID string, or None if cancelled or non-interactive
    """
    if not _has_interactive():
        return None
    import questionary
    from gaia_cli.formatting import TYPE_SYMBOLS

    choices = []
    for s in skills:
        sid = s.get("id", "unknown")
        skill_type = s.get("type", "basic")
        level = s.get("level", "?")
        glyph = TYPE_SYMBOLS.get(skill_type, "○")
        desc = s.get("description", "")[:45]
        title = f"{glyph} /{sid}  [{level}]  {desc}"
        choices.append(questionary.Choice(title=title, value=sid))

    if not choices:
        return None

    result = questionary.select(
        prompt,
        choices=choices,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()
    return result


def select_fusion_candidate(candidates: list[dict], prompt: str = "Select fusion candidate:") -> Optional[str]:
    """Arrow-key picker for fusion candidates.

    Args:
        candidates: List of combo dicts with 'candidateResult' and 'detectedSkills'

    Returns:
        Selected candidate result skill ID, or None
    """
    if not _has_interactive():
        return None
    import questionary

    choices = []
    for c in candidates:
        result_id = c.get("candidateResult", "?")
        prereqs = c.get("detectedSkills", [])
        prereq_str = " + ".join(f"/{p}" for p in prereqs[:3])
        if len(prereqs) > 3:
            prereq_str += f" +{len(prereqs) - 3}"
        title = f"{prereq_str} → /{result_id}"
        choices.append(questionary.Choice(title=title, value=result_id))

    if not choices:
        return None

    result = questionary.select(
        prompt,
        choices=choices,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()
    return result


def select_multiple_skills(skills: list[dict], prompt: str = "Select skills to combine:") -> list[str]:
    """Multi-select checkbox skill picker. Returns list of selected skill IDs.

    Args:
        skills: List of skill dicts with at least 'id', optionally 'type', 'level', 'description'
        prompt: The prompt message to display

    Returns:
        List of selected skill ID strings, or empty list if cancelled or non-interactive
    """
    if not _has_interactive():
        return []
    import questionary
    from gaia_cli.formatting import TYPE_SYMBOLS

    choices = []
    for s in skills:
        sid = s.get("id", "unknown")
        skill_type = s.get("type", "basic")
        level = s.get("level", "?")
        glyph = TYPE_SYMBOLS.get(skill_type, "○")
        desc = s.get("description", "")[:45]
        title = f"{glyph} /{sid}  [{level}]  {desc}"
        choices.append(questionary.Choice(title=title, value=sid))

    if not choices:
        return []

    result = questionary.checkbox(
        prompt,
        choices=choices,
    ).ask()
    return result or []


def select_promotion_candidate(candidates: list[dict], prompt: str = "Select skill to promote:") -> Optional[str]:
    """Arrow-key picker for promotion candidates.

    Args:
        candidates: List of promotion candidate dicts with 'skillId', 'currentLevel', 'suggestedLevel'

    Returns:
        Selected skill ID, or None
    """
    if not _has_interactive():
        return None
    import questionary

    choices = []
    for c in candidates:
        sid = c.get("skillId", "?")
        current = c.get("currentLevel", "?")
        suggested = c.get("suggestedLevel", "?")
        title = f"/{sid}  {current} → {suggested}"
        choices.append(questionary.Choice(title=title, value=sid))

    if not choices:
        return None

    result = questionary.select(
        prompt,
        choices=choices,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()
    return result


def select_fusion_to_edit(fusions: dict[str, list[str]], prompt: str = "Select a custom fusion:") -> Optional[str]:
    """Arrow-key picker for existing custom fusions.

    Args:
        fusions: Map of target_id -> list of source_ids

    Returns:
        Selected target skill ID, or None
    """
    if not _has_interactive():
        return None
    import questionary

    choices = []
    for target, sources in fusions.items():
        prereq_str = " + ".join(f"/{p}" for p in sources[:3])
        if len(sources) > 3:
            prereq_str += f" +{len(sources) - 3}"
        title = f"{prereq_str} → /{target}"
        choices.append(questionary.Choice(title=title, value=target))

    if not choices:
        return None

    result = questionary.select(
        prompt,
        choices=choices,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()
    return result


def confirm(message: str, default: bool = True) -> bool:
    """Interactive yes/no confirmation.

    Falls back to the default value when non-interactive.
    """
    if not _has_interactive():
        return default
    import questionary
    return questionary.confirm(message, default=default).ask()
