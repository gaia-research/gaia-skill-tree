"""Independent verification of one Class B dispatch (Steward V1.3).

Builder confidence is not proof.  This module is the second pair of eyes the
operating model asks for (§ 11), and it is deliberately built on one asymmetry:

    **The machine may reject.  The machine may escalate.  The machine may never
    accept.**

Everything a path comparison, a policy lookup, or an exit code can settle is
settled here, for free, before any intelligence is spent.  What survives that
machinery — *did this patch actually resolve the finding, and is this proof
genuine?* — is the only thing an independent verifier is asked to judge, and
only that judgment can produce ``accept``.

The verifier's input is a separate artifact from the builder's context.  It
carries the debt as a **sensor** recorded it, the authority envelope, the
packet, the diff, and the proof transcript.  It carries no builder narrative:
a verifier that reads the builder's reasoning is no longer independent of it.

Nothing here applies a patch, runs a command, or mutates repository state.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from gaia_cli.steward.workflowproof import Hunk, prove_workflow_edit
from gaia_cli.steward.models import (
    AuthorityClass,
    DispatchPacket,
    content_hash,
    stable_json,
)
from gaia_cli.steward.policy import DISPATCH_EXEMPT_SUBTREES


VERDICT_SCHEMA = "steward-verification-verdict-v1"
PROOF_TRANSCRIPT_SCHEMA = "steward-proof-transcript-v1"

MAX_DIFF_BYTES = 2 * 1024 * 1024
MAX_TRANSCRIPT_BYTES = 2 * 1024 * 1024

# Verdicts a verification may carry. ``pending`` is not a decision — it is the
# machine reporting that it found no disqualifying fact and that the remaining
# question needs judgment. It never means "accept".
MECHANICAL_VERDICTS = ("reject", "escalate", "pending")
FINAL_VERDICTS = ("accept", "reject", "escalate")

# Surfaces whose whole purpose is to catch a regression. A diff that removes
# protection from one of these is not automatically wrong, but it is never
# something a machine should wave through.
_GUARD_PATTERNS = (
    "tests/**",
    "scripts/validate*.py",
    "scripts/sync_*.py",
    "scripts/verify_*.py",
    "scripts/check_*.py",
    "conftest.py",
    "**/conftest.py",
)
_GUARD_SIGNAL = re.compile(
    r"^\s*(?:assert\b|def test_|async def test_|pytest\.raises|with pytest\.raises"
    r"|raise \w*Error|self\.assert|@pytest\.mark)"
)


# A direct-child workflow file. The only edit a Class B dispatch may make to one is
# adding an integer job-level `timeout-minutes` (1..360), and that is proven on YAML
# structure (see ``workflowproof``), never on how an added line happens to be spelled.
_WORKFLOW_FILE = ".github/workflows/*.yml"
_MAX_WORKFLOW_VIOLATIONS = 20


class VerificationError(RuntimeError):
    """A verification precondition was not proven; no verdict is rendered."""


@dataclass(frozen=True)
class FileChange:
    """One repository-relative path touched by a candidate diff."""

    path: str
    added: int
    removed: int
    deleted_file: bool
    created_file: bool = False

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "path": self.path,
            "added": self.added,
            "removed": self.removed,
            "deletedFile": self.deleted_file,
        }
        if self.created_file:
            data["createdFile"] = True
        return data


@dataclass(frozen=True)
class ChangeSet:
    """A parsed unified diff, reduced to what authority checking needs."""

    changes: tuple[FileChange, ...]
    diff_hash: str
    guard_signal_added: int
    guard_signal_removed: int
    deleted_guard_files: tuple[str, ...]
    # Disposition records whose COMPLETE post-diff JSON sets verifiedBy, verifiedAt or
    # verificationReceipt to a non-empty value, or cannot be evaluated at all. Each entry is
    # (path, reason). A builder never stamps, and an unreadable record is never trusted.
    stamped_paths: tuple[tuple[str, str], ...] = ()
    # Workflow-file edits that are not the pure addition of a `timeout-minutes`
    # line (founder ruling #14). Empty for every diff that touches no workflow.
    workflow_edit_violations: tuple[str, ...] = ()
    # Parsed hunks of every modified (not created, not deleted) workflow file, for
    # the structural proof; see ``workflow_structure_violations``.
    workflow_patches: tuple[tuple[str, tuple[Hunk, ...]], ...] = ()

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(change.path for change in self.changes)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "diffHash": self.diff_hash,
            "fileCount": len(self.changes),
            "files": [change.to_dict() for change in self.changes],
            "guardSignalAdded": self.guard_signal_added,
            "guardSignalRemoved": self.guard_signal_removed,
            "deletedGuardFiles": list(self.deleted_guard_files),
            **(
                {"stampedPaths": [{"path": path, "reason": reason} for path, reason in self.stamped_paths]}
                if self.stamped_paths
                else {}
            ),
        }
        if self.workflow_edit_violations:
            data["workflowEditViolations"] = list(self.workflow_edit_violations)
        return data


@dataclass(frozen=True)
class ProofEntry:
    """One executed command offered as evidence for a proof-contract item."""

    contract_index: int
    command: str
    exit_code: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "contractIndex": self.contract_index,
            "command": self.command,
            "exitCode": self.exit_code,
        }


@dataclass(frozen=True)
class ProofTranscript:
    """The builder's claimed proof, reduced to machine-checkable facts."""

    entries: tuple[ProofEntry, ...]
    transcript_hash: str
    outputs: Mapping[int, tuple[str, ...]]

    def covered(self) -> frozenset[int]:
        return frozenset(entry.contract_index for entry in self.entries)

    def failures(self) -> tuple[ProofEntry, ...]:
        return tuple(entry for entry in self.entries if entry.exit_code != 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcriptHash": self.transcript_hash,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class VerificationVerdict:
    """The six operating-model questions, plus how they were answered."""

    dispatch_id: str
    debt_id: str
    finding_confirmed: bool
    scope_valid: bool
    proof_valid: bool
    authority_still_valid: bool
    guards_weakened: bool
    new_debt: tuple[str, ...]
    verdict: str
    reasons: tuple[str, ...]
    change_set: ChangeSet
    transcript: ProofTranscript

    def __post_init__(self) -> None:
        if self.verdict not in MECHANICAL_VERDICTS:
            raise ValueError(
                "a mechanical verification may only reject, escalate, or stay pending"
            )

    @property
    def decided(self) -> bool:
        """Whether machinery already settled this without spending judgment."""

        return self.verdict != "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": VERDICT_SCHEMA,
            "dispatchId": self.dispatch_id,
            "debtId": self.debt_id,
            "findingConfirmed": self.finding_confirmed,
            "scopeValid": self.scope_valid,
            "proofValid": self.proof_valid,
            "authorityStillValid": self.authority_still_valid,
            "guardsWeakened": self.guards_weakened,
            "newDebt": list(self.new_debt),
            "verdict": self.verdict,
            "decidedBy": "machine" if self.decided else "pending-independent-judgment",
            "reasons": list(self.reasons),
            "changeSet": self.change_set.to_dict(),
            "proof": self.transcript.to_dict(),
        }

    @property
    def verdict_hash(self) -> str:
        return content_hash(self.to_dict())


def _matches(path: str, pattern: str) -> bool:
    """Return whether ``path`` lies inside a ``dir/**`` scope or matches exactly."""

    if pattern.endswith("/**"):
        prefix = PurePosixPath(pattern[:-3]).parts
        return PurePosixPath(path).parts[: len(prefix)] == prefix
    if pattern.startswith("**/"):
        return PurePosixPath(path).name == pattern[3:]
    return path == pattern or PurePosixPath(path).match(pattern)


def _in_scope(path: str, pattern: str) -> bool:
    """Whether ``path`` is inside an envelope scope: a ``dir/**`` subtree or an exact path.

    A file glob such as ``.github/workflows/*.yml`` matches a direct child of that
    one directory, anchored at the repository root. ``_matches`` is right-anchored
    (``PurePosixPath.match``), which would also accept ``docs/.github/workflows/x.yml``;
    an envelope must never be wider than it reads.
    """

    if pattern.endswith("/**") or "*" not in pattern:
        return _matches(path, pattern)
    pattern_parts = PurePosixPath(pattern).parts
    path_parts = PurePosixPath(path).parts
    return len(pattern_parts) == len(path_parts) and all(
        fnmatchcase(part, glob) for part, glob in zip(path_parts, pattern_parts)
    )


def _carveOut(path: str, denied: str, packet: DispatchPacket) -> bool:
    """Whether the one policy carve-out lifts the ``founder/**`` ban for ``path``.

    Exact pair only: a packet for the carve-out's own debt kind that allows that
    exact subtree, a path inside it, and the ``founder/**`` ban. No other ban is
    ever lifted, and no other rule or kind ever qualifies; for everything else a
    forbidden path stays forbidden even when a narrower path is allowed.
    """

    if denied != "founder/**":
        return False
    kind = packet.debt.get("kind") if isinstance(packet.debt, Mapping) else None
    return any(
        exempt_kind == kind and glob in packet.allowed_paths and _in_scope(path, glob)
        for glob, exempt_kind in DISPATCH_EXEMPT_SUBTREES.items()
    )


# Post-review stamp fields of a credential disposition record. Only the lead's
# integrate step sets them; a builder diff must leave them empty or absent. The
# check runs on the COMPLETE post-diff JSON of each record, never on isolated
# added lines (a multi-line value can change under an unchanged key line), and
# fails closed when that JSON cannot be produced or is not a valid object.
_STAMP_SUBTREE = "founder/steward/security-dispositions/"
_STAMP_FIELDS = ("verifiedby", "verifiedat", "verificationreceipt")
MAX_BASE_BYTES = 256 * 1024

BaseReader = Callable[[str], "str | None"]


def checkoutBase(root: Path) -> BaseReader:
    """Read a file's pre-diff text from a checkout, or None when it is not a plain readable file."""

    resolved = root.resolve()

    def read(rel: str) -> str | None:
        path = (resolved / rel)
        try:
            if path.is_symlink() or not path.is_file() or resolved not in path.resolve().parents:
                return None
            if path.stat().st_size > MAX_BASE_BYTES:
                return None
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    return read


@dataclass
class _Hunk:
    old_start: int
    lines: list[tuple[str, str]]


def _applyHunks(base: list[str], hunks: list[_Hunk]) -> list[str]:
    """Apply unified-diff hunks to ``base`` lines; any mismatch raises (fail closed)."""

    out: list[str] = []
    cursor = 0  # next unread index into base
    for hunk in hunks:
        # A hunk with no old lines inserts AFTER old_start, otherwise it starts AT old_start.
        has_old = any(tag in (" ", "-") for tag, _ in hunk.lines)
        start = hunk.old_start - 1 if has_old else hunk.old_start
        if start < cursor or start > len(base):
            raise VerificationError("a hunk overlaps an earlier one or lies outside the file")
        out.extend(base[cursor:start])
        cursor = start
        for tag, content in hunk.lines:
            if tag in (" ", "-"):
                if cursor >= len(base) or base[cursor] != content:
                    raise VerificationError("a hunk does not apply to the current file")
                if tag == " ":
                    out.append(content)
                cursor += 1
            else:
                out.append(content)
    out.extend(base[cursor:])
    return out


def _postImageProblem(path: str, is_new: bool, hunks: list[_Hunk], read: BaseReader | None) -> str | None:
    """Why a disposition record's post-diff JSON cannot be accepted, or None when it is clean."""

    if is_new:
        base: list[str] = []
    else:
        text = read(path) if read is not None else None
        if text is None:
            return "post-diff JSON unavailable: the file's current content could not be read"
        base = text.split("\n")
    try:
        post = "\n".join(_applyHunks(base, hunks))
    except VerificationError as exc:
        return f"post-diff JSON unavailable: {exc}"
    try:
        body = json.loads(post)
    except ValueError:
        return "post-diff content is not valid JSON"
    if not isinstance(body, dict):
        return "post-diff JSON is not an object"
    for key, value in body.items():
        if str(key).strip().casefold() in _STAMP_FIELDS and value not in (None, ""):
            return f"sets {key}: only the lead's integrate step may stamp a record"
    return None
def _is_guard(path: str) -> bool:
    return any(_matches(path, pattern) for pattern in _GUARD_PATTERNS)


_HUNK_HEADER = re.compile(r"^@@+ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_TOLERATED_PREAMBLE = ("commit ", "Author: ", "Date: ", "From ", "Subject: ")
_IGNORED_METADATA = (
    "index ",
    "new file mode",
    "old mode",
    "new mode",
    "similarity index",
    "dissimilarity index",
    "GIT binary patch",
)


def parse_unified_diff(text: str, *, base: BaseReader | None = None) -> ChangeSet:
    """Parse a git unified diff the way ``git apply`` reads one, failing closed.

    Scope checking is only as trustworthy as this function: a path it fails to
    see is a path that never gets checked against the envelope. Two properties
    make that trustworthy, and both were learned from a real bypass.

    **Paths come from the ``---``/``+++`` pair, not from ``diff --git``.** That
    is where ``git apply`` reads them, and it will apply a section with no
    ``diff --git`` header at all. A parser that trusted the header could be
    handed a header naming an allowed path above a body naming a forbidden one,
    report `scopeValid: True`, and watch the patch write somewhere it was never
    granted. A header may still appear, and must then *agree* with the body.

    **Hunk bodies are consumed by their declared line counts.** Content lines
    are only interpreted inside a hunk whose length the header declared, so a
    removed line that happens to read ``--- a/somewhere`` is content rather
    than a new file section. Without counting, that ambiguity is the same
    bypass wearing different clothes.

    Everything it cannot reduce to one unambiguous repository-relative path —
    a rename, a quoted or escaped name, a combined diff, a hunk belonging to no
    file, a stray line outside any hunk — raises rather than being skipped.
    """

    if len(text.encode("utf-8")) > MAX_DIFF_BYTES:
        raise VerificationError("candidate diff exceeds the 2 MiB safety limit")

    changes: list[FileChange] = []
    deleted_guards: list[str] = []
    stamped: dict[str, str] = {}
    guard_added = guard_removed = 0
    hunks: list[_Hunk] = []
    workflow_violations: list[str] = []
    workflow_patches: list[tuple[str, tuple[Hunk, ...]]] = []

    current: str | None = None
    added = removed = 0
    deleted_file = False
    created_file = False
    pending_header: str | None = None
    pending_deleted = False
    pending_created = False
    pending_old: str | None = None
    old_remaining = new_remaining = 0
    # Hunk capture for workflow files: [old_start, old_length, [[marker, text, no_newline]]].
    open_hunks: list[list[Any]] = []

    def flush() -> None:
        nonlocal current, added, removed, deleted_file, created_file, open_hunks, hunks
        if current is None:
            return
        if current.startswith(_STAMP_SUBTREE) and not deleted_file:
            problem = _postImageProblem(current, created_file, hunks, base)
            if problem is not None:
                stamped[current] = problem
        hunks = []
        changes.append(
            FileChange(
                path=current, added=added, removed=removed,
                deleted_file=deleted_file, created_file=created_file,
            )
        )
        if _in_scope(current, _WORKFLOW_FILE):
            if deleted_file:
                workflow_violations.append(f"{current}: deletes the workflow file")
            elif created_file:
                workflow_violations.append(f"{current}: creates a workflow file; creation is never allowed")
            else:
                workflow_patches.append(
                    (
                        current,
                        tuple(
                            (int(h[0]), int(h[1]), tuple((m, t, bool(n)) for m, t, n in h[2]))
                            for h in open_hunks
                        ),
                    )
                )
        if deleted_file and _is_guard(current):
            deleted_guards.append(current)
        current, added, removed, deleted_file, created_file = None, 0, 0, False, False
        open_hunks = []

    def header_only() -> None:
        """Record a ``diff --git`` section that has no ``---``/``+++`` pair.

        git applies such a section (an empty new file, a mode change, a binary change),
        so its path must be scope-checked like any other rather than silently unseen.
        """

        nonlocal current, deleted_file, created_file, pending_header
        if pending_header is None:
            return
        current, deleted_file, created_file = pending_header, pending_deleted, pending_created
        pending_header = None
        flush()

    # Split on LF only, like git: ``str.splitlines`` would also break on CR, VT, FF, NEL and
    # U+2028/9 and silently drop the CR of CRLF content, so what the verifier saw would not
    # be the bytes git applies.
    records = text.split("\n")
    if records and records[-1] == "":
        records.pop()
    for line in records:
        if old_remaining > 0 or new_remaining > 0:
            # Inside a hunk of declared length. Nothing here is a header, no
            # matter what it looks like.
            assert current is not None
            if line.startswith("\\"):
                # "\ No newline at end of file" belongs to neither side's line count.
                if open_hunks and open_hunks[-1][2]:
                    open_hunks[-1][2][-1][2] = True
                continue
            if open_hunks and _in_scope(current, _WORKFLOW_FILE):
                open_hunks[-1][2].append([line[:1] if line[:1] in ("+", "-", " ") else " ", line[1:], False])
            if line.startswith("+"):
                new_remaining -= 1
                added += 1
                if _is_guard(current) and _GUARD_SIGNAL.match(line[1:]):
                    guard_added += 1
                if hunks:
                    hunks[-1].lines.append(("+", line[1:]))
            elif line.startswith("-"):
                old_remaining -= 1
                removed += 1
                if _is_guard(current) and _GUARD_SIGNAL.match(line[1:]):
                    guard_removed += 1
                if hunks:
                    hunks[-1].lines.append(("-", line[1:]))
            elif line.startswith(" ") or line == "":
                old_remaining -= 1
                new_remaining -= 1
                if hunks:
                    hunks[-1].lines.append((" ", line[1:]))
            else:
                raise VerificationError(
                    f"unreadable line inside a hunk of {current}: {line[:80]!r}"
                )
            if old_remaining < 0 or new_remaining < 0:
                raise VerificationError(f"hunk in {current} overruns its declared length")
            continue

        if line.startswith("diff --git "):
            flush()
            header_only()
            pending_header = _diff_header_path(line)
            pending_deleted = False
            pending_created = False
            pending_old = None
            continue
        if line.startswith("diff --cc ") or line.startswith("diff --combined "):
            raise VerificationError("combined diffs are not verifiable by this parser")
        if line.startswith("rename from ") or line.startswith("rename to "):
            raise VerificationError(
                "renames are not verifiable by this parser; supply the diff as a "
                "delete plus an add"
            )
        if line.startswith("deleted file mode"):
            pending_deleted = True
            continue
        if line.startswith("new file mode"):
            pending_created = True
            continue
        if line.startswith("\\") and open_hunks:
            # "\ No newline at end of file" arriving after the hunk's last counted line.
            if open_hunks[-1][2]:
                open_hunks[-1][2][-1][2] = True
            continue
        if line.startswith("Binary files") or line.startswith(_IGNORED_METADATA):
            continue
        if line.startswith("--- "):
            pending_old = line[4:]
            continue
        if line.startswith("+++ "):
            if pending_old is None:
                raise VerificationError(
                    f"a new-file line has no matching old-file line: {line[:80]!r}"
                )
            flush()
            current, deleted_file = _section_path(pending_old, line[4:])
            deleted_file = deleted_file or pending_deleted
            created_file = pending_created or _strip_side(pending_old) == "/dev/null"
            if pending_header is not None and pending_header != current:
                # The header said one path and the body says another. git
                # applies the body; a parser that believed the header would be
                # scope-checking a file that never gets written.
                raise VerificationError(
                    f"diff header names {pending_header!r} but its body names "
                    f"{current!r}; the two must agree"
                )
            pending_header, pending_old, pending_deleted, pending_created = None, None, False, False
            continue
        match = _HUNK_HEADER.match(line)
        if match is not None:
            if current is None:
                raise VerificationError(f"hunk belongs to no file: {line[:80]!r}")
            old_remaining = int(match.group(2)) if match.group(2) is not None else 1
            new_remaining = int(match.group(4)) if match.group(4) is not None else 1
            hunks.append(_Hunk(old_start=int(match.group(1)), lines=[]))
            open_hunks.append(
                [int(match.group(1)), old_remaining, []]
            )
            continue
        if not line.strip() or line.startswith(_TOLERATED_PREAMBLE):
            continue
        raise VerificationError(f"unreadable line outside any hunk: {line[:80]!r}")

    if old_remaining > 0 or new_remaining > 0:
        raise VerificationError("the diff ends inside an unfinished hunk")
    flush()
    header_only()

    if not changes:
        raise VerificationError("candidate diff touches no files")
    seen = [change.path for change in changes]
    if len(seen) != len(set(seen)):
        raise VerificationError("candidate diff touches the same path twice")
    return ChangeSet(
        changes=tuple(sorted(changes, key=lambda item: item.path)),
        diff_hash=content_hash(text),
        guard_signal_added=guard_added,
        guard_signal_removed=guard_removed,
        deleted_guard_files=tuple(sorted(deleted_guards)),
        stamped_paths=tuple(sorted(stamped.items())),
        workflow_edit_violations=tuple(workflow_violations),
        workflow_patches=tuple(sorted(workflow_patches)),
    )


def _strip_side(value: str) -> str:
    """Reduce one ``---``/``+++`` operand to a repository-relative path."""

    # git never emits a timestamp, but plain `diff -u` does, after a tab.
    candidate = value.split("\t", 1)[0].strip()
    if not candidate:
        raise VerificationError("a diff file line names nothing")
    if '"' in candidate or "\\" in candidate:
        raise VerificationError(f"quoted or escaped diff path is not verifiable: {candidate!r}")
    if candidate == "/dev/null":
        return candidate
    if candidate.startswith(("a/", "b/")):
        candidate = candidate[2:]
    path = PurePosixPath(candidate)
    if not candidate or path.is_absolute() or ".." in path.parts:
        raise VerificationError(f"unsafe diff path: {candidate!r}")
    return candidate


def _section_path(old_side: str, new_side: str) -> tuple[str, bool]:
    """Resolve the one path a ``---``/``+++`` pair writes, and whether it deletes."""

    old, new = _strip_side(old_side), _strip_side(new_side)
    if old == "/dev/null" and new == "/dev/null":
        return _unverifiable("a diff section names /dev/null on both sides")
    if new == "/dev/null":
        return old, True
    if old == "/dev/null":
        return new, False
    if old != new:
        return _unverifiable(
            f"a diff section rewrites {old!r} as {new!r}; supply that as a delete plus an add"
        )
    return new, False


def _unverifiable(message: str) -> tuple[str, bool]:
    raise VerificationError(message)


def _diff_header_path(line: str) -> str:
    """Extract the single repository-relative path from a ``diff --git`` header.

    The header is corroboration, never the source of truth: ``_section_path``
    decides, and a header that disagrees with the body raises.
    """

    remainder = line[len("diff --git ") :].strip()
    if '"' in remainder or "\\" in remainder:
        raise VerificationError(f"quoted or escaped diff path is not verifiable: {remainder!r}")
    parts = remainder.split(" ")
    if len(parts) != 2 or not parts[0].startswith("a/") or not parts[1].startswith("b/"):
        raise VerificationError(f"unparseable diff header: {line[:120]!r}")
    left, right = parts[0][2:], parts[1][2:]
    if left != right:
        raise VerificationError(f"diff header renames {left!r} to {right!r}; not verifiable")
    path = PurePosixPath(left)
    if path.is_absolute() or ".." in path.parts or not left:
        raise VerificationError(f"unsafe diff path: {left!r}")
    return left



# Proof items the process itself discharges. A builder cannot obtain its own
# independent review; the verification step after mechanical checks *is* that
# review, and a machine verdict never accepts. Requiring the builder to evidence
# it only invited a fabricated entry or a spurious escalation.
PROCESSOWNEDPROOF = frozenset({"obtain independent review before integration"})


def processOwnedProof(item: str) -> bool:
    return " ".join(str(item).split()).rstrip(".").casefold() in PROCESSOWNEDPROOF

def parse_proof_transcript(raw: str, *, proof_contract_length: int) -> ProofTranscript:
    """Parse the builder's proof transcript into machine-checkable facts."""

    if len(raw.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
        raise VerificationError("proof transcript exceeds the 2 MiB safety limit")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid proof transcript JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != PROOF_TRANSCRIPT_SCHEMA:
        raise VerificationError(
            f"proof transcript must declare schemaVersion {PROOF_TRANSCRIPT_SCHEMA}"
        )
    entries_raw = data.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise VerificationError("proof transcript entries must be a non-empty list")

    entries: list[ProofEntry] = []
    outputs: dict[int, list[str]] = {}
    for item in entries_raw:
        if not isinstance(item, dict):
            raise VerificationError("each proof transcript entry must be an object")
        index = item.get("contractIndex")
        command = item.get("command")
        exit_code = item.get("exitCode")
        if isinstance(index, bool) or not isinstance(index, int):
            raise VerificationError("proof transcript contractIndex must be an integer")
        if not 1 <= index <= proof_contract_length:
            raise VerificationError(
                f"proof transcript contractIndex {index} is outside the packet's "
                f"1..{proof_contract_length} proof contract"
            )
        if not isinstance(command, str) or not command.strip():
            raise VerificationError("proof transcript command must be a non-empty string")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise VerificationError("proof transcript exitCode must be an integer")
        output = item.get("output", "")
        if not isinstance(output, str):
            raise VerificationError("proof transcript output must be a string")
        entries.append(ProofEntry(contract_index=index, command=command.strip(), exit_code=exit_code))
        outputs.setdefault(index, []).append(output)

    ordered = tuple(sorted(entries, key=lambda item: (item.contract_index, item.command)))
    return ProofTranscript(
        entries=ordered,
        transcript_hash=content_hash(raw),
        outputs={index: tuple(values) for index, values in sorted(outputs.items())},
    )


def is_workflow_path(path: str) -> bool:
    """Whether ``path`` is a direct-child ``.github/workflows/*.yml`` file."""

    return _in_scope(path, _WORKFLOW_FILE)


def workflow_structure_violations(
    change_set: ChangeSet, baseline: Mapping[str, str | None] | None
) -> list[str]:
    """Structural proof for every modified workflow file in the diff.

    ``baseline`` maps each workflow path to the content the diff was cut against
    (``None`` when the file is absent there). With no baseline the edit cannot be
    proven, which is a rejection, never a pass.
    """

    problems: list[str] = []
    for path, hunks in change_set.workflow_patches:
        before = (baseline or {}).get(path)
        if before is None:
            problems.append(f"{path}: no baseline content was supplied, so the edit cannot be proven structurally")
            continue
        problems.extend(f"{path}: {item}" for item in prove_workflow_edit(before, hunks))
    return problems


def evaluate(
    *,
    packet: DispatchPacket,
    change_set: ChangeSet,
    transcript: ProofTranscript,
    debt_source: str,
    sensor_sources: Sequence[str],
    baseline_open_debt: Sequence[str],
    current_open_debt: Sequence[str],
    authority_still_class_b: bool,
    workflow_baseline: Mapping[str, str | None] | None = None,
) -> VerificationVerdict:
    """Answer every verification question machinery can answer, then stop.

    The order below is the cost doctrine made literal: disqualifying facts are
    cheapest, so they are checked first and end the verification without a
    single token spent.  ``pending`` is the only outcome that costs anything.
    """

    reasons: list[str] = []

    # 1. Was the finding real? A machine cannot judge whether the patch addresses
    #    the finding, but it can prove the finding came from a sensor rather than
    #    from whoever wanted the work authorized.
    finding_confirmed = debt_source in set(sensor_sources)
    if not finding_confirmed:
        reasons.append(
            f"the debt's source {debt_source!r} is not a registered sensor; the "
            "finding was asserted, not observed"
        )

    # 2. Did scope expand? Pure function of the diff and the envelope.
    outside = [
        path
        for path in change_set.paths
        if not any(_in_scope(path, allowed) for allowed in packet.allowed_paths)
    ]
    forbidden = [
        path
        for path in change_set.paths
        if any(
            _in_scope(path, denied) and not _carveOut(path, denied, packet)
            for denied in packet.forbidden_paths
        )
    ]
    stamped = list(change_set.stamped_paths)
    structural = workflow_structure_violations(change_set, workflow_baseline)
    scope_valid = (
        not outside
        and not forbidden
        and not stamped
        and not change_set.workflow_edit_violations
        and not structural
    )
    if outside:
        reasons.append("diff writes outside allowedPaths: " + ", ".join(sorted(outside)))
    if forbidden:
        reasons.append("diff writes inside forbiddenPaths: " + ", ".join(sorted(forbidden)))
    for stamped_path, why in stamped:
        reasons.append(f"disposition record {stamped_path}: {why}")
    if change_set.workflow_edit_violations:
        reasons.append(
            "a workflow diff may not create or delete a workflow file: "
            + "; ".join(change_set.workflow_edit_violations)
        )
    if structural:
        reasons.append(
            "a workflow edit must be proven to add only job-level timeout-minutes: "
            + "; ".join(structural[:_MAX_WORKFLOW_VIOLATIONS])
        )

    # 3. Is the proof complete and passing? Coverage and exit codes are exact;
    #    whether the output is genuine is not, and is asked of the verifier.
    required = frozenset(
        index for index, item in enumerate(packet.proof, start=1) if not processOwnedProof(item)
    )
    uncovered = sorted(required - transcript.covered())
    failed = transcript.failures()
    proof_valid = not uncovered and not failed
    if uncovered:
        reasons.append(
            "proof contract items with no evidence: " + ", ".join(str(item) for item in uncovered)
        )
    if failed:
        reasons.append(
            "proof commands exited non-zero: "
            + ", ".join(f"{item.command} → {item.exit_code}" for item in failed)
        )

    # 4. Is the original authority class still valid?
    authority_still_valid = authority_still_class_b and packet.authority is AuthorityClass.B
    if not authority_still_valid:
        reasons.append(
            "the debt is no longer classified Class B under current policy; the "
            "authority this work was done under has lapsed"
        )

    # 5. Were guards weakened?
    guards_weakened = bool(change_set.deleted_guard_files) or (
        change_set.guard_signal_removed > change_set.guard_signal_added
    )
    if change_set.deleted_guard_files:
        reasons.append(
            "guard files deleted: " + ", ".join(change_set.deleted_guard_files)
        )
    elif guards_weakened:
        reasons.append(
            f"net removal of {change_set.guard_signal_removed - change_set.guard_signal_added} "
            "guard assertions"
        )

    # 6. Did new debt appear?
    new_debt = tuple(
        sorted(set(current_open_debt) - set(baseline_open_debt) - {packet.debt.get("id")})
    )
    if new_debt:
        reasons.append("new debt appeared since dispatch: " + ", ".join(new_debt))

    verdict = _mechanical_verdict(
        finding_confirmed=finding_confirmed,
        scope_valid=scope_valid,
        proof_valid=proof_valid,
        authority_still_valid=authority_still_valid,
        guards_weakened=guards_weakened,
        new_debt=new_debt,
    )
    if verdict == "pending":
        reasons.append(
            "no disqualifying fact found mechanically; whether the patch resolves "
            "the finding and whether the proof is genuine require independent judgment"
        )

    return VerificationVerdict(
        dispatch_id=packet.dispatch_id,
        debt_id=str(packet.debt.get("id")),
        finding_confirmed=finding_confirmed,
        scope_valid=scope_valid,
        proof_valid=proof_valid,
        authority_still_valid=authority_still_valid,
        guards_weakened=guards_weakened,
        new_debt=new_debt,
        verdict=verdict,
        reasons=tuple(reasons),
        change_set=change_set,
        transcript=transcript,
    )


def _mechanical_verdict(
    *,
    finding_confirmed: bool,
    scope_valid: bool,
    proof_valid: bool,
    authority_still_valid: bool,
    guards_weakened: bool,
    new_debt: tuple[str, ...],
) -> str:
    """Map mechanical facts to the only verdicts a machine may reach.

    Rejection is for facts that are disqualifying on their own terms: work
    outside its envelope, or proof that is missing or failing.  Escalation is
    for facts that are *not* the builder's error but change who should decide —
    a lapsed authority, a weakened guard, unrelated debt appearing mid-flight.

    There is deliberately no branch returning ``accept``.
    """

    if not scope_valid or not proof_valid or not finding_confirmed:
        return "reject"
    if not authority_still_valid or guards_weakened or new_debt:
        return "escalate"
    return "pending"


def verification_payload(verdict: VerificationVerdict, packet: DispatchPacket) -> dict[str, Any]:
    """The durable receipt body for one verification."""

    payload = {
        "verdict": verdict.to_dict(),
        "packetHash": packet.packet_hash,
        "verdictHash": verdict.verdict_hash,
    }
    stable_json(payload)
    return payload


def read_text_input(path: Path, *, label: str, limit: int) -> str:
    """Read one verification input file with an explicit safety ceiling."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"cannot read {label} at {path}: {exc}") from exc
    if len(raw) > limit:
        raise VerificationError(f"{label} exceeds its safety limit")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError(f"{label} must be UTF-8 text: {exc}") from exc
