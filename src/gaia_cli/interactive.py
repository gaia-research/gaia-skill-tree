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


def _format_id(sid: str) -> str:
    """Format ID without leading slash if it contains a contributor (slash in middle),
    otherwise ensure it has a leading slash for generic skills.
    """
    sid = sid.lstrip('/')
    if '/' in sid:
        return sid
    return f"/{sid}"


def select_skill(skills: list[dict], prompt: str = "Select a skill:", disabled_ids: list[str] | None = None) -> Optional[str]:
    """Arrow-key skill picker. Returns skill ID or None if cancelled/unavailable.

    Args:
        skills: List of skill dicts with at least 'id', optionally 'type', 'level', 'description'
        prompt: The prompt message to display
        disabled_ids: List of skill IDs to grey out and disable

    Returns:
        Selected skill ID string, or None if cancelled or non-interactive
    """
    if not _has_interactive():
        return None
    import questionary

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"
    disabled_set = set(disabled_ids or [])

    choices = []
    for s in skills:
        sid = s.get("id", "unknown")
        level = s.get("level", "?")
        desc = s.get("description", "")[:45]
        
        # Determine prefix
        skill_type = s.get("type", "basic")
        is_local = s.get("local", False)
        is_origin = s.get("origin", False)
        
        prefix = "[CUSTOM]" if is_local else "[STARLESS]"
        if is_origin:
            prefix = "[ORIGIN]"
        elif skill_type in ("basic", "extra", "ultimate"):
            # If it has a contributor or is named
            if '/' in sid.lstrip('/'):
                 prefix = "[NAMED]"
        
        display_id = _format_id(sid)
        title = f"{prefix} {display_id}  [{level}]  {desc}"
        
        is_disabled = sid in disabled_set
        choices.append(questionary.Choice(
            title=title, 
            value=sid,
            disabled=" (prerequisite)" if is_disabled else None
        ))

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
        prereq_str = " + ".join(_format_id(p) for p in prereqs[:3])
        if len(prereqs) > 3:
            prereq_str += f" +{len(prereqs) - 3}"
        
        display_res = _format_id(result_id)
        title = f"[FUSION] {prereq_str} → {display_res}"
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

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    choices = []
    for s in skills:
        sid = s.get("id", "unknown")
        level = s.get("level", "?")
        desc = s.get("description", "")[:45]
        
        skill_type = s.get("type", "basic")
        is_local = s.get("local", False)
        is_origin = s.get("origin", False)
        
        prefix = "[CUSTOM]" if is_local else "[STARLESS]"
        if is_origin:
            prefix = "[ORIGIN]"
        elif skill_type in ("basic", "extra", "ultimate"):
            if '/' in sid.lstrip('/'):
                 prefix = "[NAMED]"

        display_id = _format_id(sid)
        title = f"{prefix} {display_id}  [{level}]  {desc}"
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
        
        display_id = _format_id(sid)
        title = f"[PROMOTE] {display_id}  {current} → {suggested}"
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


def select_fusion_to_edit(fusions: dict, prompt: str = "Select a custom fusion:") -> Optional[str]:
    """Arrow-key picker for existing custom fusions.

    Args:
        fusions: Map of target_id -> list of source_ids OR Map of target_id -> dict with sources

    Returns:
        Selected target skill ID, or None
    """
    if not _has_interactive():
        return None
    import questionary

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    choices = []
    for target, data in fusions.items():
        if isinstance(data, dict):
            sources = data.get("sources", [])
        else:
            sources = data
            
        prereq_str = " + ".join(_format_id(p) for p in sources[:3])
        if len(sources) > 3:
            prereq_str += f" +{len(sources) - 3}"
        
        display_target = _format_id(target)
        title = f"[EDIT] {prereq_str} → {display_target}"
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
    1. Fuses -> Review (proposedCombinations)
    2. Custom skills -> Review (proposedSkills)
    3. Starless skills -> Named proposal (knownSkills)
    
    All items are selected by default.
    Returns a list of 'type:id' strings of selected items.
    """
    if not _has_interactive():
        return []
    import questionary

    full_prompt = f"{prompt}  (Ctrl+C to cancel)"

    choices = []
    
    # 1. Fusions (Fuses)
    fusions = batch.get("proposedCombinations", [])
    if fusions:
        choices.append(questionary.Separator("--- Fuses -> Review ---"))
        for f in fusions:
            res = f.get("candidateResult", "?")
            srcs = f.get("detectedSkills", [])
            
            prereq_str = " + ".join(_format_id(s) for s in srcs)
            display_res = _format_id(res)
            title = f"[FUSION] {prereq_str} → {display_res}"
            choices.append(questionary.Choice(title=title, value=f"fusion:{res}", checked=True))
            
    # 2. Custom Skills
    proposed = batch.get("proposedSkills", [])
    if proposed:
        choices.append(questionary.Separator("--- Custom skills -> Review ---"))
        for p in proposed:
            sid = p.get("id", "?")
            title = f"[CUSTOM] {_format_id(sid)}"
            choices.append(questionary.Choice(title=title, value=f"proposed:{sid}", checked=True))

    # 3. Starless (Known/Generic)
    known = batch.get("knownSkills", [])
    if known:
        choices.append(questionary.Separator("--- Starless skills -> Named proposal ---"))
        for k in known:
            sid = k.get("skillId", "?")
            local_id = k.get("localId")
            if local_id and local_id != sid:
                title = f"[STARLESS] {_format_id(local_id)} -> {_format_id(sid)}"
            else:
                title = f"[STARLESS] {_format_id(sid)}"
            choices.append(questionary.Choice(title=title, value=f"known:{sid}", checked=True))

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
