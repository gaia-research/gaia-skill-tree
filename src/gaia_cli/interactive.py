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
    from gaia_cli.formatting import TYPE_SYMBOLS, _fg, _reset, RANK_COLORS

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    choices = []
    for s in skills:
        sid = s.get("id", "unknown")
        skill_type = s.get("type", "basic")
        level = s.get("level", "?")
        is_local = s.get("local", False)
        glyph = TYPE_SYMBOLS.get(skill_type, "○")
        desc = s.get("description", "")[:45]
        
        # Follow gaia scan rules: local is grey
        id_color = _fg(*RANK_COLORS["0★"]) if is_local else ""
        r_col = _reset() if is_local else ""
        
        title = f"{glyph} {id_color}/{sid}{r_col}  [{level}]  {desc}"
        choices.append(questionary.Choice(title=title, value=sid))

    if not choices:
        return None

    result = questionary.select(
        full_prompt,
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

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

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
        full_prompt,
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
    from gaia_cli.formatting import TYPE_SYMBOLS, _fg, _reset, RANK_COLORS

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    choices = []
    for s in skills:
        sid = s.get("id", "unknown")
        skill_type = s.get("type", "basic")
        level = s.get("level", "?")
        is_local = s.get("local", False)
        glyph = TYPE_SYMBOLS.get(skill_type, "○")
        desc = s.get("description", "")[:45]
        
        # Follow gaia scan rules: local is grey
        id_color = _fg(*RANK_COLORS["0★"]) if is_local else ""
        r_col = _reset() if is_local else ""
        
        title = f"{glyph} {id_color}/{sid}{r_col}  [{level}]  {desc}"
        choices.append(questionary.Choice(title=title, value=sid))

    if not choices:
        return []

    result = questionary.checkbox(
        full_prompt,
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

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

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
        full_prompt,
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

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

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
        full_prompt,
        choices=choices,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()
    return result


def select_push_batch(batch: dict, prompt: str = "Select items to push to registry:") -> list[str]:
    """Multi-select checkbox for items in a push batch.
    
    Choices are grouped by:
    1. Fusions (proposedCombinations)
    2. Starless (knownSkills)
    3. Custom (proposedSkills)
    
    All items are selected by default.
    Returns a list of 'type:id' strings of selected items.
    """
    if not _has_interactive():
        return []
    import questionary

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    choices = []
    
    # 1. Fusions
    fusions = batch.get("proposedCombinations", [])
    if fusions:
        choices.append(questionary.Separator("--- Fused skill paths ---"))
        for f in fusions:
            res = f.get("candidateResult", "?")
            srcs = f.get("detectedSkills", [])
            title = f"◇ {' + '.join('/' + s for s in srcs)} → /{res}"
            choices.append(questionary.Choice(title=title, value=f"fusion:{res}", checked=True))
            
    # 2. Starless
    known = batch.get("knownSkills", [])
    if known:
        choices.append(questionary.Separator("--- Starless (Generic) ---"))
        for k in known:
            sid = k.get("skillId", "?")
            choices.append(questionary.Choice(title=f"○ /{sid}", value=f"known:{sid}", checked=True))
            
    # 3. Custom
    proposed = batch.get("proposedSkills", [])
    if proposed:
        choices.append(questionary.Separator("--- Custom Skills ---"))
        for p in proposed:
            sid = p.get("id", "?")
            choices.append(questionary.Choice(title=f"○ /{sid}", value=f"proposed:{sid}", checked=True))

    if not choices:
        return []

    result = questionary.checkbox(
        full_prompt,
        choices=choices,
    ).ask()
    return result or []


def select_text_input(prompt: str, default: str = "") -> Optional[str]:
    """Interactive text input."""
    if not _has_interactive():
        return None
    import questionary

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    return questionary.text(
        full_prompt,
        default=default,
    ).ask()


def confirm(message: str, default: bool = True) -> bool:
    """Interactive yes/no confirmation.

    Falls back to the default value when non-interactive.
    """
    if not _has_interactive():
        return default
    import questionary
    return questionary.confirm(message, default=default).ask()
