"""Render a Tree Keeper dispatch as a harness-neutral prompt.

Steward decides *what* work exists and *how much authority* it carries. This
module decides nothing.  It is a deterministic projection of an already-rendered
Class B packet into text a human can paste into whichever harness they are
holding — Hermes, Claude, Codex, anything else — without the packet's meaning
changing on the way.

The prompt therefore names no model, no provider, and no tool surface.  It
carries the finding, the authority envelope, the stop conditions, and the proof
contract, because those are what bound the work.  Harness choice is a scheduling
decision the founder makes at dispatch time; see `founder/steward/routines/`.

Rendering is report-only.  It executes nothing, spends no tokens, and reuses the
receipt written when the packet was rendered.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from gaia_cli.steward.models import DispatchPacket


PROMPT_SCHEMA = "steward-tree-keeper-prompt-v1"

_ROLE = """You are **Tree Keeper**, executing exactly one Gaia Steward maintenance dispatch.

You were not asked to maintain Gaia Skill Tree. You were asked to resolve the one
finding below, inside the authority envelope below, and to stop when that is done
or when a stop condition fires — whichever comes first.

You may not widen your own authority. If the work turns out to need a path,
command, or decision that is not granted here, that is a finding to report, not a
permission to assume."""

_REPORTING = """Report back in this shape, and nothing more:

- **Verdict** — `resolved`, `blocked`, or `escalate`
- **What you changed** — the diff, confined to the allowed paths
- **Proof** — the exact command output satisfying each item of the proof contract
- **What you did not change** — anything you noticed but left alone, and why
- **New debt** — conditions you observed that are outside this dispatch

If the finding does not reproduce from current repository state, stop and say so.
A dispatch that reports "the finding was not real" is a successful dispatch. Do
not manufacture a change to justify the run."""


def _fenced_json(value: Any) -> str:
    body = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    return f"```json\n{body}\n```"


def _bullets(values: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in values)


def _numbered(values: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(values, start=1))


def render_tree_keeper_prompt(
    packet: DispatchPacket,
    *,
    prompt_guide: str,
    receipt: Mapping[str, Any] | None = None,
) -> str:
    """Return the complete, standalone prompt text for one Class B packet."""

    debt = dict(packet.debt)
    subject = debt.get("subject", {})
    budget = packet.budget.to_dict()
    receipt_id = (receipt or {}).get("runId", "unrecorded")

    sections = [
        f"# Tree Keeper dispatch — `{packet.dispatch_id}`",
        _ROLE,
        "## Authority\n\n"
        f"**Class {packet.authority.value} — bounded autonomous repair.**\n\n"
        f"Routine `{packet.routine}` under policy rule `{packet.rule}`. "
        "Authority is a ceiling, not a target: it may narrow while you work "
        "(an ambiguity turns Class B into a Class C question), and it never "
        "widens because you became confident.\n\n"
        f"Human contract for this routine: `{prompt_guide}`\n\n"
        f"Steward receipt for this dispatch: `{receipt_id}`",
        f"## Objective\n\n{packet.objective.strip()}",
        "## Finding\n\n"
        f"- Debt: `{debt.get('id', 'unknown')}`\n"
        f"- Kind: `{debt.get('kind', 'unknown')}`\n"
        f"- Subject: `{subject.get('type', 'unknown')}` / `{subject.get('id', 'unknown')}`\n"
        f"- Observed by: `{debt.get('source', 'unknown')}` at `{debt.get('lastObservedAt', 'unknown')}`\n"
        f"- Observed {debt.get('observationCount', 1)} time(s), confidence "
        f"{debt.get('confidence', 'unknown')}\n\n"
        "Evidence, verbatim from the scan that produced this packet:\n\n"
        + _fenced_json(dict(packet.evidence)),
        "## Allowed paths\n\nYou may write only inside these:\n\n"
        + _bullets(packet.allowed_paths),
        "## Allowed commands\n\nYou may run only these:\n\n"
        + _bullets(packet.allowed_commands),
        "## Forbidden paths\n\nNever write here, for any reason:\n\n"
        + _bullets(packet.forbidden_paths),
        "## Stop conditions\n\nStop immediately and escalate if any of these becomes true:\n\n"
        + _numbered(packet.stop_conditions),
        "## Proof contract\n\nThe work is not done until every one of these holds:\n\n"
        + _numbered(packet.proof),
        "## Budget\n\n"
        f"- Model calls granted by Steward: **{budget['modelCalls']}**\n"
        f"- Token ceiling: **{budget['maxTokens']}**\n"
        f"- Wall-clock ceiling: **{budget['maxMinutes']} minutes**\n\n"
        "A zero budget means Steward is not paying for this dispatch — it is "
        "report-only, and the operator who pastes this prompt owns the spend "
        "and the ceiling.",
        "## Reporting\n\n" + _REPORTING,
    ]
    return "\n\n".join(sections).strip() + "\n"
