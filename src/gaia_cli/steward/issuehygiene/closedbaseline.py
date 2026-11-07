"""Durable last-known verified closed-issue count (founder ruling steward-census-empty-page-crosschecks).

Closed listings have no independent total, so a repeated empty 200 cannot be told from a real empty history. The
census collector therefore keeps one diagnostic fact across runs: the last closed-issue count it VERIFIED, with when
it saw it, from which provider and over what scope. This module is that record and the rules around it. It is a
baseline for noticing that something is wrong, never proof that anything is right: no closure depends on it.

Rules, each one pinned by a test:

* A baseline is written only from a verified read. A failed, refused or unverified scan never touches it.
* A count that goes up or stays level replaces the baseline.
* A decrease is first explained. Reopening closed issues lowers the closed count legitimately, so a decrease no
  larger than the number of issues reopened since the baseline was observed replaces the baseline and says why.
* A decrease nothing explains is NEVER adopted, however often it is seen. The verified baseline is kept and the lower
  count is reported as a diagnostic (`unexplainedLower`). Only reopening evidence can lower the baseline.
* The baseline is written only after the whole census proved complete (the collector enforces this), and a baseline that
  could not be restored is never replaced (it is reported as not evaluated).

The module reads and writes one small JSON file and never touches the network.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "steward-closed-issue-baseline-v1"
DEFAULT_PATH = Path(".gaia/steward/inputs/closed-issue-baseline.json")
SCOPE = "issues only (pull requests excluded), state=closed, all time"
SOURCES = ("gh-api", "mcp")
_MAX_BYTES = 64 * 1024


@dataclass(frozen=True)
class Baseline:
    count: int
    observedAt: str
    source: str
    scope: str
    unexplainedLower: Mapping[str, Any] | None = None

    def to_dict(self, repo: str) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schemaVersion": SCHEMA,
            "repo": repo,
            "count": self.count,
            "observedAt": self.observedAt,
            "source": self.source,
            "scope": self.scope,
        }
        if self.unexplainedLower:
            document["unexplainedLower"] = dict(self.unexplainedLower)
        return document

    def summary(self) -> dict[str, Any]:
        """The fields telemetry shows: count, observedAt, source, scope."""

        return {"count": self.count, "observedAt": self.observedAt, "source": self.source, "scope": self.scope}


def _isCount(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def loadBaseline(path: Path, repo: str) -> tuple[Baseline | None, str | None]:
    """Read the baseline file. Returns ``(baseline, problem)``; never raises.

    A missing file is ``(None, None)``: the first run. A file that cannot be trusted is ``(None, reason)`` so the
    caller reports it and, because nothing verified is lost by it, may write a fresh baseline from a verified read.
    A baseline about another repository is untrusted rather than reused.
    """

    if not path.exists() and not path.is_symlink():
        return None, None
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_BYTES:
            return None, "baseline-not-a-regular-file"
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "baseline-unreadable"
    if not isinstance(raw, dict) or raw.get("schemaVersion") != SCHEMA:
        return None, "baseline-schema-unknown"
    if raw.get("repo") != repo:
        return None, "baseline-other-repository"
    if not _isCount(raw.get("count")) or raw.get("source") not in SOURCES:
        return None, "baseline-malformed"
    if not isinstance(raw.get("observedAt"), str) or not isinstance(raw.get("scope"), str):
        return None, "baseline-malformed"
    lower = raw.get("unexplainedLower")
    if lower is not None and not (
        isinstance(lower, dict) and _isCount(lower.get("count")) and _isCount(lower.get("consecutive"))
        and isinstance(lower.get("firstObservedAt"), str)
    ):
        return None, "baseline-malformed"
    return Baseline(raw["count"], raw["observedAt"], raw["source"], raw["scope"], lower), None


def saveBaseline(path: Path, repo: str, baseline: Baseline) -> None:
    """Atomic write beside the target, then rename."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=str(path.parent), prefix=".closed-baseline-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(baseline.to_dict(repo), stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


@dataclass(frozen=True)
class Judgement:
    """What a verified count means against the baseline, and what to store next (None: leave the file as it is)."""

    direction: str  # first | same | up | down
    delta: int | None
    explained: bool | None
    explanation: str
    update: str  # created | updated | unchanged | kept-unexplained-lower | preserved | not-evaluated
    next: Baseline | None


def judge(
    baseline: Baseline | None,
    count: int,
    observedAt: str,
    source: str,
    reopened: int | None,
    reopenedReason: str | None = None,
) -> Judgement:
    """Judge one VERIFIED count. ``reopened`` is the issues reopened since the baseline, or None when unknown."""

    fresh = Baseline(count, observedAt, source, SCOPE)
    if baseline is None:
        return Judgement("first", None, None, "no earlier verified baseline", "created", fresh)
    delta = count - baseline.count
    if delta >= 0:
        direction = "same" if delta == 0 else "up"
        return Judgement(direction, delta, None, "closed count did not decrease",
                         "unchanged" if delta == 0 else "updated", fresh)
    drop = -delta
    if reopened is not None and reopened >= drop:
        return Judgement(
            "down", delta, True,
            f"{reopened} issue(s) reopened since {baseline.observedAt} explain the drop of {drop}",
            "updated", fresh,
        )
    why = (
        f"only {reopened} reopened issue(s) found since {baseline.observedAt} for a drop of {drop}"
        if reopened is not None else f"reopen events unavailable ({reopenedReason or 'unknown'})"
    )
    lower = baseline.unexplainedLower
    if lower and lower.get("count") == count:
        consecutive = int(lower["consecutive"]) + 1
        first = str(lower["firstObservedAt"])
    else:
        consecutive, first = 1, observedAt
    held = Baseline(
        baseline.count, baseline.observedAt, baseline.source, baseline.scope,
        {"count": count, "consecutive": consecutive, "firstObservedAt": first, "lastObservedAt": observedAt},
    )
    return Judgement(
        "down", delta, False,
        f"{why}; the verified baseline of {baseline.count} is kept and {count} is reported as a diagnostic "
        f"(seen on {consecutive} consecutive run(s)); only reopening evidence can lower the baseline",
        "kept-unexplained-lower", held,
    )
