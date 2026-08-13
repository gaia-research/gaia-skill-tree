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
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from gaia_cli.steward.models import (
    AuthorityClass,
    DispatchPacket,
    content_hash,
    stable_json,
)


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


class VerificationError(RuntimeError):
    """A verification precondition was not proven; no verdict is rendered."""


@dataclass(frozen=True)
class FileChange:
    """One repository-relative path touched by a candidate diff."""

    path: str
    added: int
    removed: int
    deleted_file: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "added": self.added,
            "removed": self.removed,
            "deletedFile": self.deleted_file,
        }


@dataclass(frozen=True)
class ChangeSet:
    """A parsed unified diff, reduced to what authority checking needs."""

    changes: tuple[FileChange, ...]
    diff_hash: str
    guard_signal_added: int
    guard_signal_removed: int
    deleted_guard_files: tuple[str, ...]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(change.path for change in self.changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "diffHash": self.diff_hash,
            "fileCount": len(self.changes),
            "files": [change.to_dict() for change in self.changes],
            "guardSignalAdded": self.guard_signal_added,
            "guardSignalRemoved": self.guard_signal_removed,
            "deletedGuardFiles": list(self.deleted_guard_files),
        }


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


def parse_unified_diff(text: str) -> ChangeSet:
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
    guard_added = guard_removed = 0

    current: str | None = None
    added = removed = 0
    deleted_file = False
    pending_header: str | None = None
    pending_deleted = False
    pending_old: str | None = None
    old_remaining = new_remaining = 0

    def flush() -> None:
        nonlocal current, added, removed, deleted_file
        if current is None:
            return
        changes.append(
            FileChange(path=current, added=added, removed=removed, deleted_file=deleted_file)
        )
        if deleted_file and _is_guard(current):
            deleted_guards.append(current)
        current, added, removed, deleted_file = None, 0, 0, False

    for line in text.splitlines():
        if old_remaining > 0 or new_remaining > 0:
            # Inside a hunk of declared length. Nothing here is a header, no
            # matter what it looks like.
            assert current is not None
            if line.startswith("\\"):
                continue  # "\ No newline at end of file" belongs to neither side
            if line.startswith("+"):
                new_remaining -= 1
                added += 1
                if _is_guard(current) and _GUARD_SIGNAL.match(line[1:]):
                    guard_added += 1
            elif line.startswith("-"):
                old_remaining -= 1
                removed += 1
                if _is_guard(current) and _GUARD_SIGNAL.match(line[1:]):
                    guard_removed += 1
            elif line.startswith(" ") or line == "":
                old_remaining -= 1
                new_remaining -= 1
            else:
                raise VerificationError(
                    f"unreadable line inside a hunk of {current}: {line[:80]!r}"
                )
            if old_remaining < 0 or new_remaining < 0:
                raise VerificationError(f"hunk in {current} overruns its declared length")
            continue

        if line.startswith("diff --git "):
            flush()
            pending_header = _diff_header_path(line)
            pending_deleted = False
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
            if pending_header is not None and pending_header != current:
                # The header said one path and the body says another. git
                # applies the body; a parser that believed the header would be
                # scope-checking a file that never gets written.
                raise VerificationError(
                    f"diff header names {pending_header!r} but its body names "
                    f"{current!r}; the two must agree"
                )
            pending_header, pending_old, pending_deleted = None, None, False
            continue
        match = _HUNK_HEADER.match(line)
        if match is not None:
            if current is None:
                raise VerificationError(f"hunk belongs to no file: {line[:80]!r}")
            old_remaining = int(match.group(2)) if match.group(2) is not None else 1
            new_remaining = int(match.group(4)) if match.group(4) is not None else 1
            continue
        if not line.strip() or line.startswith(_TOLERATED_PREAMBLE):
            continue
        raise VerificationError(f"unreadable line outside any hunk: {line[:80]!r}")

    if old_remaining > 0 or new_remaining > 0:
        raise VerificationError("the diff ends inside an unfinished hunk")
    flush()

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
        if not any(_matches(path, allowed) for allowed in packet.allowed_paths)
    ]
    forbidden = [
        path
        for path in change_set.paths
        if any(_matches(path, denied) for denied in packet.forbidden_paths)
    ]
    scope_valid = not outside and not forbidden
    if outside:
        reasons.append("diff writes outside allowedPaths: " + ", ".join(sorted(outside)))
    if forbidden:
        reasons.append("diff writes inside forbiddenPaths: " + ", ".join(sorted(forbidden)))

    # 3. Is the proof complete and passing? Coverage and exit codes are exact;
    #    whether the output is genuine is not, and is asked of the verifier.
    required = frozenset(range(1, len(packet.proof) + 1))
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
