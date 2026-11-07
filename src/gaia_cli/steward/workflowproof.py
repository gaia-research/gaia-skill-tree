"""Structural proof that a workflow edit only adds job-level timeouts (founder ruling #14).

The workflow-timeout route is the one Steward write into ``.github/``. Two gates, both
required, and the first one is the primary:

1. **Byte preservation.** The diff must be pure line insertions: no removed or modified
   line, no no-newline marker, so every existing byte (whitespace, CRLF, BOM, trailing
   newline, comments, quoting) is untouched. A YAML loader's notion of "equal" is not
   proof (``on`` and ``yes`` both load as ``True`` in YAML 1.1 and are different strings
   to GitHub Actions; ``012`` and ``10`` collide too), so equality is never what protects
   an existing token. Every inserted line must be exactly an unquoted, uncommented
   ``timeout-minutes: 1..360`` entry.
2. **Structure.** The patched file must also load strictly (one document, no anchors,
   aliases, tags or duplicate keys) with the only semantic change being that integer key
   added directly under an existing top-level job, in a block mapping, at the job's own
   child-key indentation, at most once per job and only where the job had none.

Nothing here touches the filesystem, runs a command, or imports a workflow engine.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import yaml

MAX_TIMEOUT_MINUTES = 360
_INT_TAG = "tag:yaml.org,2002:int"
_PLAIN_DECIMAL = re.compile(r"[1-9][0-9]{0,2}", re.ASCII)
_KEY = "timeout-minutes"
# The only line a patch may insert: no comment, quotes or trailing space, LF-terminated
# (the line's own LF is not part of the text matched here), integer 1..360.
_INSERTED = re.compile(r"( +)timeout-minutes: (?:[1-9][0-9]?|[1-2][0-9]{2}|3[0-5][0-9]|360)", re.ASCII)

# (marker, text, no-newline-at-end-of-file flag)
HunkLine = tuple[str, str, bool]
# (old_start, old_length, lines)
Hunk = tuple[int, int, tuple[HunkLine, ...]]


class WorkflowProofError(ValueError):
    """The patch or a workflow cannot be proven; the edit is rejected."""


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys, merge keys and non-scalar keys."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                raise WorkflowProofError("a mapping key is not a plain scalar")
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise WorkflowProofError("merge keys are not allowed")
            key = self.construct_object(key_node, deep=True)
            try:
                if key in seen:
                    raise WorkflowProofError(f"duplicate mapping key {str(key)[:40]!r}")
                seen.add(key)
            except TypeError as exc:
                raise WorkflowProofError("an unhashable mapping key") from exc
        return super().construct_mapping(node, deep)


def _screen(text: str) -> None:
    """Reject anchors, aliases, explicit tags and anything but exactly one document."""

    documents = 0
    try:
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            if isinstance(event, yaml.DocumentStartEvent):
                documents += 1
            if isinstance(event, yaml.AliasEvent):
                raise WorkflowProofError("YAML aliases are not allowed")
            if getattr(event, "anchor", None):
                raise WorkflowProofError("YAML anchors are not allowed")
            if getattr(event, "tag", None) is not None:
                raise WorkflowProofError("explicit YAML tags are not allowed")
    except yaml.YAMLError as exc:
        raise WorkflowProofError(f"unparseable YAML ({type(exc).__name__})") from exc
    if documents != 1:
        raise WorkflowProofError(f"expected exactly one YAML document, found {documents}")


def strict_load(text: str) -> Any:
    """Load exactly one anchor-free, alias-free, duplicate-key-free YAML document."""

    _screen(text)
    try:
        return yaml.load(text, Loader=_StrictLoader)  # noqa: S506 - SafeLoader subclass
    except yaml.YAMLError as exc:
        raise WorkflowProofError(f"unparseable YAML ({type(exc).__name__})") from exc


def apply_patch(before: str, hunks: Sequence[Hunk]) -> str:
    """Apply parsed hunks to ``before`` with exact context, or raise."""

    return apply_patch_tracked(before, hunks)[0]


def apply_patch_tracked(before: str, hunks: Sequence[Hunk]) -> tuple[str, list[int]]:
    """Apply hunks exactly; also return the 0-based line numbers of inserted lines in the result."""

    inserted: list[int] = []
    ends_with_newline = before.endswith("\n")
    lines = before.split("\n")
    if ends_with_newline:
        lines.pop()
    out: list[str] = []
    position = 0
    final_newline = ends_with_newline
    for old_start, old_length, body in hunks:
        start = old_start - 1 if old_length > 0 else old_start
        if start < position or start > len(lines):
            raise WorkflowProofError("hunks overlap or point outside the baseline")
        out.extend(lines[position:start])
        cursor = start
        reaches_end = start + old_length == len(lines)
        last_old_flag = last_new_flag = None
        for marker, text, no_newline in body:
            if marker in (" ", "-"):
                if cursor >= len(lines) or lines[cursor] != text:
                    raise WorkflowProofError("hunk context does not match the baseline")
                cursor += 1
                last_old_flag = no_newline
            if marker in (" ", "+"):
                if marker == "+":
                    inserted.append(len(out))
                out.append(text)
                last_new_flag = no_newline
            if no_newline and not reaches_end:
                raise WorkflowProofError("no-newline marker inside the file")
        if cursor != start + old_length:
            raise WorkflowProofError("hunk length does not match its header")
        if reaches_end:
            if last_old_flag is not None and last_old_flag != (not ends_with_newline):
                raise WorkflowProofError("end-of-file newline state does not match the baseline")
            if last_old_flag is None and not ends_with_newline and lines:
                # Touching the end of a file that lacks a final newline must say so.
                raise WorkflowProofError("end-of-file newline state does not match the baseline")
            final_newline = not bool(last_new_flag)
        position = cursor
    out.extend(lines[position:])
    return "\n".join(out) + ("\n" if final_newline else ""), inserted


def _same(first: Any, second: Any) -> bool:
    """Deep equality that does not conflate ``True`` with ``1`` or ``1`` with ``1.0``."""

    if type(first) is not type(second):
        return False
    if isinstance(first, dict):
        if len(first) != len(second):
            return False
        return all(
            any(type(key) is type(other) and key == other and _same(value, second[other]) for other in second)
            for key, value in first.items()
        )
    if isinstance(first, list):
        return len(first) == len(second) and all(_same(a, b) for a, b in zip(first, second))
    return bool(first == second)


def _job_nodes(text: str) -> dict[str, yaml.Node]:
    """Raw ``timeout-minutes`` value nodes by job id, from the composed node tree."""

    root = yaml.compose(text, Loader=_StrictLoader)
    found: dict[str, yaml.Node] = {}
    if not isinstance(root, yaml.MappingNode):
        return found
    for key_node, value_node in root.value:
        if getattr(key_node, "value", None) != "jobs" or not isinstance(value_node, yaml.MappingNode):
            continue
        for job_key, job_value in value_node.value:
            if not isinstance(job_value, yaml.MappingNode):
                continue
            for field_key, field_value in job_value.value:
                if getattr(field_key, "value", None) == _KEY:
                    found[str(job_key.value)] = field_value
    return found


def prove_timeout_additions(before: str, after: str, inserted: Sequence[int] | None = None) -> list[str]:
    """Violations (empty means proven) for turning ``before`` into ``after``.

    Proven means: both files load strictly as one document; the job ids are identical;
    the only difference is an integer ``timeout-minutes`` in 1..360, written as a plain
    decimal literal, added to jobs that had none; and nothing else, at any depth, changed.
    """

    try:
        old = strict_load(before)
        new = strict_load(after)
    except WorkflowProofError as exc:
        return [f"strict YAML load failed: {exc}"]
    if not isinstance(old, dict) or not isinstance(new, dict):
        return ["a workflow must be a mapping"]
    old_jobs, new_jobs = old.get("jobs"), new.get("jobs")
    if not isinstance(old_jobs, dict) or not isinstance(new_jobs, dict) or not old_jobs:
        return ["the workflow has no jobs mapping to edit"]
    if set(old_jobs) != set(new_jobs):
        return ["the set of job ids changed"]

    problems: list[str] = []
    added: dict[str, Any] = {}
    stripped_jobs: dict[Any, Any] = {}
    for job_id, new_job in new_jobs.items():
        old_job = old_jobs[job_id]
        if not isinstance(old_job, dict) or not isinstance(new_job, dict):
            stripped_jobs[job_id] = new_job
            continue
        if _KEY in old_job or _KEY not in new_job:
            stripped_jobs[job_id] = new_job
            continue
        value = new_job[_KEY]
        if type(value) is not int or not 1 <= value <= MAX_TIMEOUT_MINUTES:
            problems.append(f"job {str(job_id)[:40]!r}: timeout-minutes must be an integer 1..{MAX_TIMEOUT_MINUTES}")
        if "uses" in new_job:
            problems.append(f"job {str(job_id)[:40]!r}: a reusable-workflow call job cannot take timeout-minutes")
        added[job_id] = value
        stripped_jobs[job_id] = {k: v for k, v in new_job.items() if k != _KEY}
    if not added:
        problems.append("no timeout-minutes was added to any job")
    stripped = dict(new)
    stripped["jobs"] = stripped_jobs
    if not _same(stripped, old):
        problems.append("something other than job-level timeout-minutes changed")
    if problems:
        return problems

    try:
        nodes = _job_nodes(after)
    except yaml.YAMLError as exc:
        return [f"unparseable YAML ({type(exc).__name__})"]
    if inserted is not None:
        problems.extend(_position_problems(after, inserted, set(added)))
    for job_id in added:
        node = nodes.get(str(job_id))
        literal = getattr(node, "value", None)
        if (
            not isinstance(node, yaml.ScalarNode)
            or node.tag != _INT_TAG
            or node.style is not None
            or not isinstance(literal, str)
            or _PLAIN_DECIMAL.fullmatch(literal) is None
        ):
            problems.append(f"job {str(job_id)[:40]!r}: timeout-minutes must be a plain decimal literal")
    return problems


def _position_problems(after: str, inserted: Sequence[int], added_jobs: set[Any]) -> list[str]:
    """Each inserted line must be the ``timeout-minutes`` key of exactly one top-level job.

    The key must sit in a block mapping that is a direct child of the root ``jobs`` block
    mapping, at the same indentation as that job's other child keys, with at most one
    inserted line per job. Anything inside a block scalar, flow mapping, ``strategy``,
    ``steps`` or ``on`` is some other node and cannot be the key of a top-level job.
    """

    try:
        root = yaml.compose(after, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        return [f"unparseable YAML ({type(exc).__name__})"]
    if not isinstance(root, yaml.MappingNode) or root.flow_style:
        return ["the workflow root is not a block mapping"]
    jobs = next(
        (value for key, value in root.value if getattr(key, "value", None) == "jobs" and key.start_mark.column == 0),
        None,
    )
    if not isinstance(jobs, yaml.MappingNode) or jobs.flow_style:
        return ["the top-level jobs mapping is not a block mapping"]
    placed: dict[int, str] = {}
    for job_key, job_value in jobs.value:
        if not isinstance(job_value, yaml.MappingNode) or job_value.flow_style:
            continue
        columns = {child.start_mark.column for child, _ in job_value.value}
        for child, _ in job_value.value:
            if getattr(child, "value", None) == _KEY:
                placed[child.start_mark.line] = str(job_key.value)
                column = child.start_mark.column
                if columns != {column} or column <= job_key.start_mark.column:
                    placed[child.start_mark.line] = "\0misaligned"
    problems: list[str] = []
    per_job: dict[str, int] = {}
    for line_number in inserted:
        job = placed.get(line_number)
        if job is None:
            problems.append(f"inserted line {line_number + 1} is not the timeout-minutes key of a top-level job in a block mapping")
        elif job == "\0misaligned":
            problems.append(f"inserted line {line_number + 1} is not at the job's own child-key indentation")
        else:
            per_job[job] = per_job.get(job, 0) + 1
    problems.extend(f"job {job[:40]!r} received {count} inserted lines; at most one is allowed" for job, count in per_job.items() if count > 1)
    return problems


def byte_gate_problems(hunks: Sequence[Hunk]) -> list[str]:
    """The primary gate: the patch must be pure insertions of exact timeout lines."""

    problems: list[str] = []
    insertions = 0
    for _, _, body in hunks:
        for marker, text, no_newline in body:
            if no_newline:
                problems.append("a no-newline-at-end-of-file marker means an existing byte changes")
            if marker == "-":
                problems.append(f"removes or rewrites an existing line ({text.strip()[:40]!r}); only insertions are allowed")
            elif marker == "+":
                insertions += 1
                if _INSERTED.fullmatch(text) is None:
                    problems.append(
                        f"inserted line {text.strip()[:40]!r} is not exactly an unquoted, uncommented "
                        f"'timeout-minutes: 1..{MAX_TIMEOUT_MINUTES}' entry"
                    )
    if insertions == 0:
        problems.append("the patch inserts nothing")
    return problems[:20]


def prove_workflow_edit(before: str, hunks: Sequence[Hunk]) -> list[str]:
    """Both gates for one modified workflow file; an empty list means proven."""

    problems = byte_gate_problems(hunks)
    if problems:
        return problems
    try:
        after, inserted = apply_patch_tracked(before, hunks)
    except WorkflowProofError as exc:
        return [f"the diff does not apply to the baseline ({exc})"]
    # Belt and braces for byte preservation: removing the inserted lines restores the baseline.
    remaining = [line for index, line in enumerate(after.split("\n")) if index not in set(inserted)]
    if "\n".join(remaining) != before:
        return ["the patched file differs from the baseline by more than the inserted lines"]
    return prove_timeout_additions(before, after, inserted)
