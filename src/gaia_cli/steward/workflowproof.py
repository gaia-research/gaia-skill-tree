"""Structural proof that a workflow edit only adds job-level timeouts (founder ruling #14).

The workflow-timeout route is the one Steward write into ``.github/``. A check on the
spelling of added lines is not enough: an indented ``timeout-minutes: 15`` line can be
a step key, shell text inside a ``run: |`` scalar, a second key that silently overrides
a first, or a non-ASCII numeral that parses as a string. So the proof here is about
YAML meaning. It loads the baseline and the patched file strictly, then demands that
the only semantic difference is an integer ``timeout-minutes`` of 1..360, written as a
plain decimal, added directly under an existing job that lacked one.

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
                out.append(text)
                last_new_flag = no_newline
            if no_newline and not reaches_end:
                raise WorkflowProofError("no-newline marker inside the file")
        if cursor != start + old_length:
            raise WorkflowProofError("hunk length does not match its header")
        if reaches_end:
            if last_old_flag is not None and last_old_flag != (not ends_with_newline):
                raise WorkflowProofError("end-of-file newline state does not match the baseline")
            final_newline = not bool(last_new_flag)
        position = cursor
    out.extend(lines[position:])
    return "\n".join(out) + ("\n" if final_newline else "")


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


def prove_timeout_additions(before: str, after: str) -> list[str]:
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
