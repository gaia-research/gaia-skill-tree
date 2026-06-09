"""Interactive CLI helpers using questionary and prompt_toolkit.

Gracefully degrades when questionary/prompt_toolkit is not installed or when
running in a non-interactive context (piped stdin, CI, --yes flag).
"""

from __future__ import annotations

import os
import sys
from typing import Optional


def questionary_style():
    """Return a branded questionary Style for all interactive prompts."""
    import questionary
    return questionary.Style([
        ("pointer",     "fg:#fbbf24 bold"),
        ("highlighted", "fg:#fbbf24 bold"),
        ("selected",    "fg:#fbbf24 bold"),
        ("answer",      "fg:#fbbf24 bold"),
        ("separator",   "fg:#4b5563"),
        ("text",        ""),
    ])


def fuse_style():
    """Return a fuse-purple questionary Style for fuse command prompts."""
    import questionary
    return questionary.Style([
        ("pointer",     "fg:#c084fc bold"),
        ("highlighted", "fg:#c084fc bold"),
        ("selected",    "fg:#c084fc bold"),
        ("answer",      "fg:#c084fc bold"),
        ("separator",   "fg:#4b5563"),
        ("text",        ""),
    ])


def push_style():
    """Questionary style for gaia push — label badges invert on highlight."""
    import questionary
    return questionary.Style([
        ("pointer",     "fg:#86efac bold"),
        ("highlighted", "fg:#86efac"),
        ("selected",    "fg:#86efac bold"),
        ("answer",      "fg:#86efac bold"),
        ("separator",   "fg:#4b5563"),
        ("text",        ""),
        ("label-origin",   "fg:#fbbf24 bold"),
        ("label-named",    "fg:#ef4444 bold"),
        ("label-starless", "fg:#94a3b8"),
        ("label-custom",   "fg:#86efac bold"),
        ("label-fusion",   "fg:#c084fc bold"),
        ("highlighted label-origin",   "bg:#fbbf24 fg:#000000 bold"),
        ("highlighted label-named",    "bg:#ef4444 fg:#000000 bold"),
        ("highlighted label-starless", "bg:#94a3b8 fg:#000000"),
        ("highlighted label-custom",   "bg:#86efac fg:#000000 bold"),
        ("highlighted label-fusion",   "bg:#c084fc fg:#000000 bold"),
    ])


def _has_interactive() -> bool:
    """Check if interactive mode is available and appropriate."""
    if not sys.stdin.isatty():
        return False
    if os.environ.get("CI"):
        return False
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


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert RGB tuple to #rrggbb for prompt_toolkit style specs."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _fuse_sort_key(skill: dict):
    """Sort key for fuse pickers: Custom (0) → Starless (1) → Named (2) → Origin (3)."""
    is_local = skill.get("local", False)
    is_origin = skill.get("origin", False)
    sid = skill.get("id", "")
    named_ref = skill.get("named_ref")
    has_slash = "/" in (named_ref or "") or "/" in sid.lstrip("/")
    is_named = has_slash and not is_local

    if is_local:
        return (0, sid)
    elif is_origin:
        return (3, sid)
    elif is_named:
        return (2, sid)
    else:
        return (1, sid)


def _fuse_skill_title(skill: dict, username: str | None = None, selected: bool = False) -> list[tuple[str, str]]:
    """Return prompt_toolkit FormattedText fragments for a skill row in fuse pickers.

    Color roles:
      [CUSTOM]   → green label + green ID
      [STARLESS] → slate label + rank-colored ID + description
      [NAMED]    → honor-red label + red contrib / rank-colored nickname + description
      [ORIGIN]   → apex-gold label + red contrib / rank-colored nickname + description

    When selected=True the label badge inverts (bg:color fg:#000000).
    """
    from gaia_cli.formatting import (
        COLOR_CONTRIBUTOR, COLOR_LOCAL_USER, COLOR_GREY,
        RANK_COLORS, rank_hex,
    )

    sid = skill.get("id", "unknown")
    level = skill.get("level", "0★")
    desc = (skill.get("description", "") or "")[:50]
    is_local = skill.get("local", False)
    is_origin = skill.get("origin", False)
    named_ref = skill.get("named_ref")
    is_disabled = skill.get("_disabled", False)

    rank_color = rank_hex(level)
    red = _rgb_to_hex(COLOR_CONTRIBUTOR)       # #ef4444 honor red
    green = _rgb_to_hex(COLOR_LOCAL_USER)      # #86efac
    gold = _rgb_to_hex(RANK_COLORS["6★"])      # #fbbf24 apex gold
    slate = _rgb_to_hex(COLOR_GREY)            # #94a3b8
    dim = "#6b7280"

    def _badge(color: str, text: str, bold: bool = True) -> tuple[str, str]:
        if selected:
            return (f"bg:{color} fg:#000000" + (" bold" if bold else ""), text)
        return (f"fg:{color}" + (" bold" if bold else ""), text)

    contrib, nickname = "", ""
    if named_ref and "/" in named_ref:
        contrib, nickname = named_ref.split("/", 1)

    stripped = sid.lstrip("/")
    parts: list[tuple[str, str]] = []

    if is_disabled:
        label = "[CUSTOM]" if is_local else ("[ORIGIN]" if is_origin else ("[NAMED]" if contrib else "[STARLESS]"))
        return [(f"fg:{slate}", f"{label} /{stripped}  [{level}]  (prerequisite)")]

    if is_local:
        parts += [
            _badge(green, "[CUSTOM]"), ("", " "),
            (f"fg:{green}", f"/{stripped}"),
            ("", "  "),
            (f"fg:{rank_color}", f"[{level}]"),
        ]
        if desc:
            parts += [("", "  "), (f"fg:{dim}", desc)]

    elif is_origin and contrib:
        # Apex-gold label, honor-red contributor handle
        parts += [
            _badge(gold, "[ORIGIN]"), ("", " "),
            (f"fg:{red}", contrib), ("", "/"), (f"fg:{rank_color}", nickname),
            ("", "  "), (f"fg:{rank_color}", f"[{level}]"),
        ]
        if desc:
            parts += [("", "  "), (f"fg:{dim}", desc)]

    elif contrib:
        # Honor-red label, honor-red contributor handle
        parts += [
            _badge(red, "[NAMED]"), ("", " "),
            (f"fg:{red}", contrib), ("", "/"), (f"fg:{rank_color}", nickname),
            ("", "  "), (f"fg:{rank_color}", f"[{level}]"),
        ]
        if desc:
            parts += [("", "  "), (f"fg:{dim}", desc)]

    else:
        # Starless — show description prominently since the slug alone is opaque
        parts += [
            _badge(slate, "[STARLESS]", bold=False), ("", " "),
            (f"fg:{rank_color}", f"/{stripped}"),
            ("", "  "), (f"fg:{rank_color}", f"[{level}]"),
        ]
        if desc:
            parts += [("", "  "), (f"fg:{dim}", desc)]

    return parts


def _pt_select(choices: list[dict], prompt: str) -> Optional[str]:
    """prompt_toolkit single-select with ↑↓←→ navigation.

    choices: list of {"title_frags": [...FormattedText tuples...], "value": str, "_disabled": bool}
    Right/Enter = select, Left/Escape/Ctrl-C = cancel.
    Returns selected value or None.
    """
    try:
        from prompt_toolkit import Application
        from prompt_toolkit.data_structures import Point
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.output import ColorDepth
    except ImportError:
        return None

    PURPLE = "#c084fc"
    DIM = "#4b5563"
    HEADER_LINES = 3  # prompt + hint + blank

    navigable = [i for i, c in enumerate(choices) if not c.get("_disabled")]
    if not navigable:
        return None

    cursor_nav = [navigable[0]]

    def get_frags():
        frags: list[tuple[str, str]] = [
            (f"fg:{PURPLE} bold", f" {prompt}\n"),
            (f"fg:{DIM}", "  ↑↓ navigate  → select  ← cancel\n"),
            ("", "\n"),
        ]
        for i, c in enumerate(choices):
            if i == cursor_nav[0]:
                frags.append((f"fg:{PURPLE} bold", " › "))
                frags.extend(c.get("title_frags_selected", c["title_frags"]))
            else:
                frags.append(("", "   "))
                frags.extend(c["title_frags"])
            frags.append(("", "\n"))
        return frags

    def get_cursor_position():
        return Point(x=0, y=HEADER_LINES + cursor_nav[0])

    result: list[Optional[str]] = [None]
    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        pos = navigable.index(cursor_nav[0]) if cursor_nav[0] in navigable else 0
        if pos > 0:
            cursor_nav[0] = navigable[pos - 1]

    @kb.add("down")
    def _down(event):
        pos = navigable.index(cursor_nav[0]) if cursor_nav[0] in navigable else 0
        if pos < len(navigable) - 1:
            cursor_nav[0] = navigable[pos + 1]

    @kb.add("right")
    @kb.add("enter")
    def _select(event):
        result[0] = choices[cursor_nav[0]]["value"]
        event.app.exit()

    @kb.add("left")
    @kb.add("escape")
    @kb.add("c-c")
    def _cancel(event):
        event.app.exit()

    no_color = bool(os.environ.get("NO_COLOR"))
    color_depth = ColorDepth.DEPTH_8_BIT if no_color else ColorDepth.DEPTH_24_BIT

    ctrl = FormattedTextControl(
        text=get_frags,
        focusable=True,
        get_cursor_position=get_cursor_position,
    )
    app = Application(
        layout=Layout(Window(content=ctrl)),
        key_bindings=kb,
        full_screen=False,
        mouse_support=False,
        color_depth=color_depth,
    )
    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        pass
    return result[0]


def _pt_multiselect(choices: list[dict], prompt: str) -> list[str]:
    """prompt_toolkit multi-select with ↑↓←→ + Space navigation.

    choices: list of {"title_frags": [...], "value": str}
    Space = toggle, Right/Enter = confirm, Left/Escape/Ctrl-C = cancel.
    Returns list of selected values, or [] if cancelled.
    """
    try:
        from prompt_toolkit import Application
        from prompt_toolkit.data_structures import Point
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.output import ColorDepth
    except ImportError:
        return []

    if not choices:
        return []

    PURPLE = "#c084fc"
    DIM = "#4b5563"
    HEADER_LINES = 3  # prompt + hint + blank

    cursor = [0]
    checked: set[int] = set()

    def get_frags():
        frags: list[tuple[str, str]] = [
            (f"fg:{PURPLE} bold", f" {prompt}\n"),
            (f"fg:{DIM}", "  ↑↓ move  space toggle  → confirm  ← cancel\n"),
            ("", "\n"),
        ]
        for i, c in enumerate(choices):
            is_cursor = i == cursor[0]
            arrow = " › " if is_cursor else "   "
            pointer_style = f"fg:{PURPLE} bold" if is_cursor else ""
            check_style = f"fg:{PURPLE}" if i in checked else f"fg:{DIM}"
            check_sym = "◉ " if i in checked else "○ "
            frags.append((pointer_style, arrow))
            frags.append((check_style, check_sym))
            if is_cursor:
                frags.extend(c.get("title_frags_selected", c["title_frags"]))
            else:
                frags.extend(c["title_frags"])
            frags.append(("", "\n"))
        return frags

    def get_cursor_position():
        return Point(x=0, y=HEADER_LINES + cursor[0])

    result: list[list[str]] = [[]]
    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        if cursor[0] > 0:
            cursor[0] -= 1

    @kb.add("down")
    def _down(event):
        if cursor[0] < len(choices) - 1:
            cursor[0] += 1

    @kb.add("space")
    def _toggle(event):
        if cursor[0] in checked:
            checked.discard(cursor[0])
        else:
            checked.add(cursor[0])

    @kb.add("right")
    @kb.add("enter")
    def _confirm(event):
        result[0] = [choices[i]["value"] for i in sorted(checked)]
        event.app.exit()

    @kb.add("left")
    @kb.add("escape")
    @kb.add("c-c")
    def _cancel(event):
        event.app.exit()

    no_color = bool(os.environ.get("NO_COLOR"))
    color_depth = ColorDepth.DEPTH_8_BIT if no_color else ColorDepth.DEPTH_24_BIT

    ctrl = FormattedTextControl(
        text=get_frags,
        focusable=True,
        get_cursor_position=get_cursor_position,
    )
    app = Application(
        layout=Layout(Window(content=ctrl)),
        key_bindings=kb,
        full_screen=False,
        mouse_support=False,
        color_depth=color_depth,
    )
    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        pass
    return result[0]


def select_skill(skills: list[dict], prompt: str = "Select a skill:", disabled_ids: list[str] | None = None, username: str | None = None) -> Optional[str]:
    """Arrow-key skill picker with ↑↓←→ navigation. Returns skill ID or None if cancelled.

    Args:
        skills: List of skill dicts with 'id'; optionally 'type', 'level', 'description',
                'local', 'origin', 'named_ref'
        prompt: The prompt message to display
        disabled_ids: List of skill IDs to grey out and disable (shown as prerequisites)
        username: The current gaia user

    Returns:
        Selected skill ID string, or None if cancelled or non-interactive
    """
    if not _has_interactive():
        return None

    disabled_set = set(disabled_ids or [])
    skills_sorted = sorted(skills, key=_fuse_sort_key)

    choices = []
    for s in skills_sorted:
        sid = s.get("id", "unknown")
        s_copy = dict(s)
        s_copy["_disabled"] = sid in disabled_set
        choices.append({
            "title_frags": _fuse_skill_title(s_copy, username, selected=False),
            "title_frags_selected": _fuse_skill_title(s_copy, username, selected=True),
            "value": sid,
            "_disabled": sid in disabled_set,
        })

    if not choices:
        return None

    return _pt_select(choices, prompt)


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
        style=fuse_style(),
    ).ask()
    return result


def select_multiple_skills(skills: list[dict], prompt: str = "Select skills to combine:", username: str | None = None) -> list[str]:
    """Multi-select skill picker with ↑↓←→ + Space navigation. Returns list of selected skill IDs.

    Args:
        skills: List of skill dicts with 'id'; optionally 'type', 'level', 'description',
                'local', 'origin', 'named_ref'
        prompt: The prompt message to display
        username: The current gaia user

    Returns:
        List of selected skill ID strings, or empty list if cancelled or non-interactive
    """
    if not _has_interactive():
        return []

    skills_sorted = sorted(skills, key=_fuse_sort_key)

    choices = []
    for s in skills_sorted:
        sid = s.get("id", "unknown")
        choices.append({
            "title_frags": _fuse_skill_title(s, username, selected=False),
            "title_frags_selected": _fuse_skill_title(s, username, selected=True),
            "value": sid,
        })

    if not choices:
        return []

    return _pt_multiselect(choices, prompt)


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
        style=fuse_style(),
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
        style=fuse_style(),
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
            title = [("class:label-fusion", "[FUSION]"), ("", f" {prereq_str} → {display_res}")]
            choices.append(questionary.Choice(title=title, value=f"fusion:{res}", checked=True))

    # 2. Custom Skills
    proposed = batch.get("proposedSkills", [])
    if proposed:
        choices.append(questionary.Separator("--- Custom skills -> Review ---"))
        for p in proposed:
            sid = p.get("id", "?")
            title = [("class:label-custom", "[CUSTOM]"), ("", f" {_format_id(sid)}")]
            choices.append(questionary.Choice(title=title, value=f"proposed:{sid}", checked=True))

    # 3. Starless (Known/Generic)
    known = batch.get("knownSkills", [])
    if known:
        choices.append(questionary.Separator("--- Starless skills -> Named proposal ---"))
        for k in known:
            sid = k.get("skillId", "?")
            local_id = k.get("localId")
            if local_id and local_id != sid:
                rest = f" {_format_id(local_id)} -> {_format_id(sid)}"
            else:
                rest = f" {_format_id(sid)}"
            title = [("class:label-starless", "[STARLESS]"), ("", rest)]
            choices.append(questionary.Choice(title=title, value=f"known:{sid}", checked=True))

    if not choices:
        return []

    result = questionary.checkbox(
        full_prompt,
        choices=choices,
        style=push_style(),
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
        style=questionary_style(),
    ).ask()


def confirm(message: str, default: bool = True) -> bool:
    """Interactive yes/no confirmation.

    Falls back to the default value when non-interactive.
    """
    if not _has_interactive():
        return default
    import questionary
    return questionary.confirm(message, default=default, style=questionary_style()).ask()
