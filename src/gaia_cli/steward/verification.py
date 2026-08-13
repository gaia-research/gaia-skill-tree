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


def parse_unified_diff(text: str) -> ChangeSet:
    """Parse a git unified diff, failing closed on anything ambiguous.

    Scope checking is only as trustworthy as this function: a path it silently
    fails to see is a path that never gets checked against the envelope.  So
    every construct it cannot reduce to an unambiguous repository-relative path
    — a quoted or escaped filename, a rename, a header it does not recognise —
    raises rather than being skipped.
    """

    if len(text.encode("utf-8")) > MAX_DIFF_BYTES:
        raise VerificationError("candidate diff exceeds the 2 MiB safety limit")

    changes: list[FileChange] = []
    current: str | None = None
    added = removed = 0
    deleted_file = False
    guard_added = guard_removed = 0
    deleted_guards: list[str] = []

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
        if line.startswith("diff --git "):
            flush()
            current = _diff_header_path(line)
            continue
        if current is None:
            # Content outside any file header cannot be attributed to a path,
            # so it cannot be scope-checked. Only benign preamble is tolerated.
            if line.strip() and not line.startswith(("index ", "From ", "Date ", "Subject:", "---", "commit ", "Author: ")):
                raise VerificationError(f"diff content precedes any file header: {line[:80]!r}")
            continue
        if line.startswith("rename from ") or line.startswith("rename to "):
            raise VerificationError(
                "renames are not verifiable by this parser; supply the diff as a "
                "delete plus an add"
            )
        if line.startswith("deleted file mode"):
            deleted_file = True
            continue
        if line.startswith(("+++ ", "--- ", "@@", "index ", "new file mode", "old mode", "new mode", "similarity index", "Binary files", "\\ No newline")):
            continue
        if line.startswith("+"):
            added += 1
            if _is_guard(current) and _GUARD_SIGNAL.match(line[1:]):
                guard_added += 1
        elif line.startswith("-"):
            removed += 1
            if _is_guard(current) and _GUARD_SIGNAL.match(line[1:]):
                guard_removed += 1
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


def _diff_header_path(line: str) -> str:
    """Extract the single repository-relative path from a ``diff --git`` header."""

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
