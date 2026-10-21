"""`gaia dev timeline-resort <contributor/skill-id>` — re-sort a named skill's timeline.

Puts the frontmatter ``timeline`` list of one named skill into ascending UTC
order. It never adds, removes, or alters an event. The rewrite moves whole
YAML list items as byte blocks; every other byte of the file (other
frontmatter keys, quoting, wrapping, body) is left exactly as it was.

Verifier-gated (MUTATING_DEV_COMMANDS in commands/dev/__init__.py).
"""

import datetime
import json
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from gaia_cli.commands.dev.helpers import (
    _fail_dev_preflight,
    _run_dev_preflights,
    _run_docs_build,
)


timelineHeadPrefix = "timeline:"
topKeyRe = re.compile(r"^[A-Za-z_][^:]*:(\s|$)")


@dataclass
class ResortPlan:
    path: Path
    text: str
    lines: list
    closeIdx: int
    fmLines: list
    headIdx: int = 0
    endIdx: int = 0
    spans: list = field(default_factory=list)
    oldEvents: list = field(default_factory=list)
    instants: list = field(default_factory=list)
    order: list = field(default_factory=list)
    already: bool = True
    newText: str = ""


def canonicalJson(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def eventInstant(value):
    """Return the UTC instant for a timezone-aware ISO-8601 value, else None."""
    if isinstance(value, datetime.datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
        try:
            parsed = datetime.datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(datetime.timezone.utc)


def namedPathFor(skillId, registryPath):
    from gaia_cli.registry import named_skills_dir

    if "/" not in skillId:
        _fail_dev_preflight(
            f"Timeline re-sort target '{skillId}' is not a named skill id.",
            fix="Pass the id as contributor/skill-slug, for example gaiabot/repo-docs-before-pr.",
        )
    namedBase = Path(named_skills_dir(registryPath)).resolve()
    candidate = (namedBase / f"{skillId}.md").resolve()
    if not candidate.is_file() or not candidate.is_relative_to(namedBase):
        _fail_dev_preflight(
            f"Named skill file for '{skillId}' was not found under {namedBase}.",
            fix="Check the contributor/slug spelling; named skills live at registry/named/<contributor>/<slug>.md.",
        )
    return candidate


def splitDocument(lines, label):
    """Return the index of the closing frontmatter fence, or fail."""
    if not lines or lines[0].rstrip("\r\n") != "---":
        _fail_dev_preflight(
            f"{label} has no YAML frontmatter block.",
            fix="Named skill files must start with a '---' frontmatter fence.",
        )
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            return index
    _fail_dev_preflight(
        f"{label} frontmatter fence is not closed.",
        fix="Close the frontmatter with a '---' line before the body.",
    )
    return None


def splitTimelineItems(blockLines, timeline):
    """Split the timeline block into one line-span per list item, or fail."""
    firstContent = next((line for line in blockLines if line.strip()), None)
    if firstContent is None:
        _fail_dev_preflight(
            "timeline block has events in the parsed frontmatter but no item lines.",
            fix="Reformat timeline as a block list ('timeline:' then '- timestamp: ...' items).",
        )
    itemIndent = len(firstContent) - len(firstContent.lstrip(" "))
    spans = []
    for line in blockLines:
        stripped = line.rstrip("\r\n")
        indent = len(stripped) - len(stripped.lstrip(" "))
        body = stripped.lstrip(" ")
        if indent == itemIndent and (body == "-" or body.startswith("- ")):
            spans.append([line])
        elif indent > itemIndent or (not stripped.strip() and spans):
            if not spans:
                _fail_dev_preflight(
                    f"Unsupported timeline layout: stray line before the first item: {stripped!r}.",
                    fix="Keep the timeline block to '- ' items with their continuation lines.",
                )
            spans[-1].append(line)
        else:
            _fail_dev_preflight(
                f"Unsupported timeline layout: unexpected line in timeline block: {stripped!r}.",
                fix="Remove comments or irregular indentation inside timeline; re-sort moves items as whole blocks.",
            )
    if len(spans) != len(timeline):
        _fail_dev_preflight(
            f"timeline block has {len(spans)} list items but {len(timeline)} parsed events.",
            fix="Reformat timeline so every event is one top-level '- ' list item.",
        )
    for index, span in enumerate(spans):
        try:
            parsed = yaml.safe_load(textwrap.dedent("".join(span)))
        except yaml.YAMLError:
            parsed = None
        if (
            not isinstance(parsed, list)
            or len(parsed) != 1
            or canonicalJson(parsed[0]) != canonicalJson(timeline[index])
        ):
            _fail_dev_preflight(
                f"Could not map timeline item {index} to its source lines; refusing to reorder.",
                fix="Check the named file's timeline block for unusual YAML; re-sort never guesses.",
            )
    return spans


def buildResortPlan(skillId, registryPath):
    path = namedPathFor(skillId, registryPath)
    text = path.read_bytes().decode("utf-8")
    lines = text.splitlines(keepends=True)
    if "".join(lines) != text:
        _fail_dev_preflight(f"{path.name} could not be split into lines losslessly.")
    closeIdx = splitDocument(lines, path.name)
    fmLines = lines[1:closeIdx]
    try:
        meta = yaml.safe_load("".join(fmLines)) or {}
    except yaml.YAMLError as exc:
        _fail_dev_preflight(f"{path.name} frontmatter is not valid YAML: {exc}")
    if not isinstance(meta, dict):
        _fail_dev_preflight(f"{path.name} frontmatter is not a mapping.")
    if meta.get("id") != skillId:
        _fail_dev_preflight(
            f"Frontmatter id {meta.get('id')!r} in {path.name} does not match '{skillId}'.",
            fix="Point the command at the file whose frontmatter id matches the requested skill.",
        )

    plan = ResortPlan(path=path, text=text, lines=lines, closeIdx=closeIdx, fmLines=fmLines)
    timeline = meta.get("timeline")
    if timeline is None or timeline == []:
        return plan
    if not isinstance(timeline, list):
        _fail_dev_preflight(
            f"timeline in {path.name} must be a list of event mappings; got {type(timeline).__name__}.",
            fix="Repair the timeline shape through the owning CLI verb; re-sort only reorders.",
        )

    instants = []
    for index, event in enumerate(timeline):
        if not isinstance(event, dict):
            _fail_dev_preflight(
                f"timeline[{index}] in {path.name} is not a mapping (got {type(event).__name__}).",
                fix="Repair the malformed event through the owning CLI verb; re-sort never rewrites event contents.",
            )
        instant = eventInstant(event.get("timestamp"))
        if instant is None:
            _fail_dev_preflight(
                f"timeline[{index}] in {path.name} has no parseable timezone-aware timestamp "
                f"(got {event.get('timestamp')!r}).",
                fix="Give the event an ISO-8601 timestamp with a timezone, such as 2026-06-10T05:38:16Z. "
                    "Re-sort never rewrites timestamps.",
            )
        instants.append(instant)

    keyIdx = [i for i, line in enumerate(fmLines) if line.startswith(timelineHeadPrefix)]
    if len(keyIdx) != 1:
        _fail_dev_preflight(
            f"{path.name} must contain exactly one top-level timeline key; found {len(keyIdx)}.",
        )
    headIdx = keyIdx[0]
    headRest = fmLines[headIdx][len(timelineHeadPrefix):].strip()
    if headRest and not headRest.startswith("#"):
        _fail_dev_preflight(
            f"timeline in {path.name} uses inline (flow) style with events; re-sort needs block style.",
            fix="Reformat the key to block style ('timeline:' then '- ' items). Layout only; no event changes.",
        )

    endIdx = headIdx + 1
    while endIdx < len(fmLines) and not topKeyRe.match(fmLines[endIdx]):
        endIdx += 1
    while endIdx > headIdx + 1 and fmLines[endIdx - 1].strip() == "":
        endIdx -= 1
    spans = splitTimelineItems(fmLines[headIdx + 1:endIdx], timeline)

    order = sorted(range(len(instants)), key=lambda i: instants[i])
    plan.headIdx = headIdx
    plan.endIdx = endIdx
    plan.spans = spans
    plan.oldEvents = timeline
    plan.instants = instants
    plan.order = order
    plan.already = order == list(range(len(instants)))
    if not plan.already:
        newFmLines = (
            fmLines[:headIdx + 1]
            + [line for i in order for line in spans[i]]
            + fmLines[endIdx:]
        )
        plan.newText = "".join([lines[0]] + newFmLines + lines[closeIdx:])
    else:
        plan.newText = text
    return plan


def verifyResortPlan(plan):
    """Prove the planned rewrite preserves every event and every other byte, or fail."""
    if plan.already:
        return
    newLines = plan.newText.splitlines(keepends=True)
    newClose = splitDocument(newLines, plan.path.name)
    if "".join(newLines[newClose:]) != "".join(plan.lines[plan.closeIdx:]):
        _fail_dev_preflight("Re-sort would change the body; refusing to write.")
    if newLines[0] != plan.lines[0]:
        _fail_dev_preflight("Re-sort would change the opening fence; refusing to write.")

    oldMeta = yaml.safe_load("".join(plan.fmLines)) or {}
    newMeta = yaml.safe_load("".join(newLines[1:newClose])) or {}
    oldRest = {k: v for k, v in oldMeta.items() if k != "timeline"}
    newRest = {k: v for k, v in newMeta.items() if k != "timeline"}
    if canonicalJson(oldRest) != canonicalJson(newRest):
        _fail_dev_preflight("Re-sort would change non-timeline frontmatter; refusing to write.")

    newEvents = newMeta.get("timeline") or []
    if len(newEvents) != len(plan.oldEvents):
        _fail_dev_preflight(
            f"Event count changed ({len(plan.oldEvents)} -> {len(newEvents)}); refusing to write."
        )
    oldCanon = sorted(canonicalJson(e) for e in plan.oldEvents)
    newCanon = sorted(canonicalJson(e) for e in newEvents)
    if oldCanon != newCanon:
        _fail_dev_preflight("Event multiset changed during re-sort; refusing to write.")
    for position, sourceIdx in enumerate(plan.order):
        if canonicalJson(newEvents[position]) != canonicalJson(plan.oldEvents[sourceIdx]):
            _fail_dev_preflight(f"Event at new position {position} differs from its source; refusing to write.")

    newInstants = [eventInstant(e.get("timestamp")) for e in newEvents]
    if any(newInstants[i] > newInstants[i + 1] for i in range(len(newInstants) - 1)):
        _fail_dev_preflight("Re-sorted timeline is not chronological; refusing to write.")

    oldBlockBytes = sorted("".join(span) for span in plan.spans)
    newBlockBytes = sorted(
        "".join(plan.spans[i]) for i in plan.order
    )
    if oldBlockBytes != newBlockBytes:
        _fail_dev_preflight("Timeline item bytes changed during re-sort; refusing to write.")

    tailLen = len(plan.fmLines) - plan.endIdx
    newFmLines = newLines[1:newClose]
    if newFmLines[:plan.headIdx + 1] != plan.fmLines[:plan.headIdx + 1]:
        _fail_dev_preflight("Lines before the timeline key changed; refusing to write.")
    if tailLen and newFmLines[len(newFmLines) - tailLen:] != plan.fmLines[plan.endIdx:]:
        _fail_dev_preflight("Lines after the timeline block changed; refusing to write.")


def printResortPlan(plan, skillId):
    total = len(plan.oldEvents)
    if plan.already:
        print(f"Timeline for {skillId} is already chronological ({total} events); nothing written.")
        return
    print(f"Current order for {skillId}:")
    for index, event in enumerate(plan.oldEvents):
        print(f"  [{index}] {event.get('timestamp')}  {event.get('action', '-')}")
    print("Proposed order (new index <- old index):")
    for position, sourceIdx in enumerate(plan.order):
        event = plan.oldEvents[sourceIdx]
        print(f"  [{position}] <- [{sourceIdx}]  {event.get('timestamp')}  {event.get('action', '-')}")


def timelineResortCommand(args):
    skillId = args.skill_id.lstrip("/")
    registryPath = args.registry
    state = {}

    _run_dev_preflights([
        lambda: state.update(plan=buildResortPlan(skillId, registryPath)),
    ])
    plan = state["plan"]
    _run_dev_preflights([
        lambda: verifyResortPlan(plan),
    ])

    printResortPlan(plan, skillId)
    if plan.already:
        return
    if getattr(args, "dry_run", False):
        print("Dry run: nothing written.")
        return

    plan.path.write_bytes(plan.newText.encode("utf-8"))
    print(
        f"Re-sorted timeline for {skillId} ({len(plan.oldEvents)} events; "
        "no events added, removed, or changed)."
    )
    if not getattr(args, "no_build", True):
        print("Regenerating registry and documentation...")
        _run_docs_build(registryPath)
    else:
        print("Skipping documentation rebuild (default; pass --build to regenerate).")
