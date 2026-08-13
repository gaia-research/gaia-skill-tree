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
VERIFIER_PROMPT_SCHEMA = "steward-verifier-prompt-v1"

_ROLE = """You are **Tree Keeper**, executing exactly one Gaia Steward maintenance dispatch.

You were not asked to maintain Gaia Skill Tree. You were asked to resolve the one
finding below, inside the authority envelope below, and to stop when that is done
or when a stop condition fires — whichever comes first.

You may not widen your own authority. If the work turns out to need a path,
command, or decision that is not granted here, that is a finding to report, not a
permission to assume.

The allowed commands are the only mutation interface you have. Anything this
envelope grants you no command for, you **describe** — you do not reach around
the missing command and do it by hand. A repository that routes changes through
a tool routes them through that tool for reasons the tool enforces and you
cannot see: audit trails, validation, provenance."""

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
        "Steward grants zero of all three: it is not commissioning this work "
        "and has authorized no spend for it. That is a statement about "
        "Steward's authority, not permission for you to set your own — "
        "whoever pasted this prompt decides the ceiling, and every other "
        "bound in this dispatch still holds exactly as written.",
        "## Reporting\n\n" + _REPORTING,
    ]
    return "\n\n".join(sections).strip() + "\n"


_VERIFIER_ROLE = """You are the **independent verifier** for one Gaia Steward Class B dispatch.

You did not do this work and you are not being asked to improve it. You are being
asked whether it should be integrated.

Everything below reached you from Steward, not from the builder. The finding is
quoted as a **sensor** recorded it. The envelope is quoted from the policy that
authorized the work. You have deliberately not been given the builder's account
of what they did or why — an explanation is exactly the thing you would be
verifying against, and reading it first is how verification turns into agreement.

Do not redesign the patch. If it is wrong, say it is wrong; a corrected patch is
a new dispatch, not part of this one."""

_VERIFIER_REPORTING = """Answer in exactly this shape:

```yaml
findingConfirmed:      # did the finding this patch claims to fix actually exist?
scopeValid:            # did the change stay inside what was authorized?
proofValid:            # does the proof genuinely demonstrate the contract items?
authorityStillValid:   # is Class B still the right authority for what this turned out to be?
guardsWeakened:        # were tests, validators, or checks made less strict?
newDebt:               # conditions you noticed that are outside this dispatch
verdict:               # accept | reject | escalate
reasons:               # one line per finding that drove the verdict
```

`accept` means: integrate this as it stands.
`reject` means: this should not be integrated, and the reason is the builder's to fix.
`escalate` means: the decision is not yours — the work turned out to need
governance, or the authority envelope itself was wrong.

If you are unsure, escalate. An escalation costs a message. A wrong accept costs
the property that makes autonomous repair defensible at all."""


def render_verifier_prompt(
    packet: DispatchPacket,
    verdict: Any,
    *,
    prompt_guide: str,
    diff_text: str,
    proof_outputs: Mapping[int, tuple[str, ...]],
    receipt: Mapping[str, Any] | None = None,
) -> str:
    """Render the independent verifier's prompt for one pending verification.

    This is only ever rendered for a ``pending`` mechanical verdict. When
    machinery already reached ``reject`` or ``escalate``, there is nothing left
    to judge and spending a model on it would be spending it to re-derive a
    fact that a path comparison already established.
    """

    if getattr(verdict, "decided", False):
        raise ValueError(
            "machinery already decided this verification; no judgment is required"
        )

    debt = dict(packet.debt)
    receipt_id = (receipt or {}).get("runId", "unrecorded")
    proof_sections = []
    for index, item in enumerate(packet.proof, start=1):
        outputs = proof_outputs.get(index, ())
        body = "\n\n".join(f"```text\n{text.strip()}\n```" for text in outputs if text.strip())
        proof_sections.append(
            f"**{index}. {item}**\n\n{body or '_No output was supplied for this item._'}"
        )

    sections = [
        f"# Independent verification — `{packet.dispatch_id}`",
        _VERIFIER_ROLE,
        "## What Steward already established\n\n"
        "These were settled mechanically, so do not spend effort re-deriving them:\n\n"
        f"- The diff writes only inside the authorized paths, and none of the forbidden ones.\n"
        f"- Every one of the {len(packet.proof)} proof-contract items has evidence, and every "
        "proof command exited zero.\n"
        f"- `{debt.get('source', 'unknown')}` is a registered sensor, so the finding was "
        "observed rather than asserted.\n"
        "- The debt is still classified Class B under current policy.\n"
        "- No guard file was deleted and no net guard assertion was removed.\n"
        "- No unrelated debt appeared between dispatch and now.\n\n"
        "**What is left is the part machinery cannot reach:** whether this patch "
        "actually resolves the finding, and whether the proof demonstrates that "
        "rather than merely exiting zero.",
        "## Authority the work was done under\n\n"
        f"**Class {packet.authority.value}** — routine `{packet.routine}` under rule "
        f"`{packet.rule}`.\n\n"
        f"Human contract: `{prompt_guide}`\n\n"
        f"Steward receipt: `{receipt_id}`\n\n"
        "Allowed paths:\n\n" + _bullets(packet.allowed_paths) + "\n\n"
        "Forbidden paths:\n\n" + _bullets(packet.forbidden_paths),
        "## The finding, as a sensor recorded it\n\n"
        f"- Debt: `{debt.get('id', 'unknown')}`\n"
        f"- Kind: `{debt.get('kind', 'unknown')}`\n"
        f"- Observed by: `{debt.get('source', 'unknown')}` at `{debt.get('lastObservedAt', 'unknown')}`\n\n"
        + _fenced_json(dict(packet.evidence)),
        f"## The objective it was dispatched against\n\n{packet.objective.strip()}",
        "## The candidate change\n\n"
        f"```diff\n{diff_text.rstrip()}\n```",
        "## The proof contract, and the evidence offered for each item\n\n"
        + "\n\n".join(proof_sections),
        "## Your verdict\n\n" + _VERIFIER_REPORTING,
    ]
    return "\n\n".join(sections).strip() + "\n"
