"""The two different things a routine pull-request founder card can say, kept apart on every surface that renders one.

A held pull request raises two questions that must never be blurred:

* the **procedural** one: what Steward itself does while a founder decision is open. That is derivable from policy, so
  Steward states it plainly: it retains the hold and takes no merge or closure action;
* the **substantive** one: whether the change should land at all. That turns on the content, on documentation accuracy and
  on the design gate. Steward has no basis to hold an opinion, so it offers none.

The desk, the founder digest, the sensor's state and the GitHub receipt all take their wording from this module. Nothing
else composes it, so the surfaces cannot drift apart. The module imports nothing, and its text is built only from this
file's own constants and from gate names matched against a fixed set, never from anything a pull request controls.
"""

from __future__ import annotations

from typing import Iterable

PROCEDURAL_LABEL = "Procedural recommendation (Steward's own action)"
SUBSTANTIVE_LABEL = "Substantive decision (yours)"

PROCEDURAL = (
    "Retain the hold. Steward leaves the pull request open and untouched and takes no merge or closure action until you "
    "rule. This is a statement about what Steward will do, not a judgment of the content."
)

# Gate names that mark a question only a person can answer, and the question each one raises.
HUMAN = (
    ("docs-accuracy", "whether the documentation is accurate against what the commands actually do"),
    ("rendered-surface", "whether the visible copy and design changes should ship"),
)
FALLBACK = "whether the change itself should land"
NOOPINION = "Steward has no basis to hold an opinion on this and offers none."


def substantive(gateNames: Iterable[str]) -> str:
    """The substantive question for a pull request whose gates carry these names. Only the fixed set above is read."""

    present = {str(name) for name in gateNames}
    topics = [question for name, question in HUMAN if name in present]
    return f"{'; and '.join(topics) or FALLBACK}. {NOOPINION}"


def pair(gateNames: Iterable[str]) -> tuple[str, str]:
    return PROCEDURAL, substantive(gateNames)


def combined(procedural: str, substantiveText: str) -> str:
    """The two statements as labelled paragraphs, procedural first, for a desk card or a digest."""

    return f"{PROCEDURAL_LABEL}: {procedural}\n\n{SUBSTANTIVE_LABEL}: {substantiveText}"
