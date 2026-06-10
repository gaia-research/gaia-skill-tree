import re

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    return ANSI_RE.sub("", text)
