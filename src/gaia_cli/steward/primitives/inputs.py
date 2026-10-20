"""Freshness rules for driver-supplied sensor inputs.

A driver collects an optional external input (CI history, an advisory scan,
test history) into ignored ``.gaia/steward/inputs/``. The sensor never fetches
anything itself, so it cannot tell a current collection from one left behind
last month: this module is where "how old is too old" is decided once.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.primitives.files import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.primitives.redact import describe_value

MAX_INPUT_AGE = timedelta(days=7)
# Drivers and sensors usually share a machine; a few minutes of skew is not "the future".
FUTURE_TOLERANCE = timedelta(minutes=5)
_STAMP_KEYS = ("collectedAt", "generatedAt")


_REMOTE = re.compile(
    r"^(?:[a-z][a-z0-9+.-]*://(?:[^/@]*@)?[^/]+/|[^/@\s]+@[^/:\s]+:)(?P<path>.+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def origin_repository(root: Path) -> str | None:
    """Return ``owner/name`` for the checkout's ``origin`` remote, or None when unknowable.

    Only URL-shaped remotes (https, ssh, scp-like) count; a local-path remote
    or a checkout with no ``origin`` is "not determinable", never a mismatch.
    """

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    match = _REMOTE.match(result.stdout.decode("utf-8", errors="replace").strip())
    if not match:
        return None
    parts = [part for part in match.group("path").split("/") if part]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def parse_instant(value: Any, where: str) -> datetime:
    """Parse an ISO-8601 instant; naive values are UTC. Never echoes ``value``."""

    if not isinstance(value, str) or not value.strip():
        raise SensorUnavailable(f"{where} requires a non-empty timestamp string")
    text = value.strip()
    text = text[:-1] + "+00:00" if text[-1:] in ("Z", "z") else text
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SensorUnavailable(f"{where} has an unparseable timestamp {describe_value(value)}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def require_fresh(
    document: Mapping[str, Any],
    path: Path,
    observed_at: str,
    *,
    label: str,
) -> dict[str, str]:
    """Raise ``SensorNotEvaluated`` unless the input is within a week and not from the future.

    The age comes from the document's ``collectedAt`` (or ``generatedAt``) when
    it carries one, else from the file's modification time: ``pip-audit`` output
    has no timestamp of its own. Returns provenance saying which was used.
    """

    now = parse_instant(observed_at, "observed_at")
    stamped = next((key for key in _STAMP_KEYS if key in document), None)
    if stamped is not None:
        collected = parse_instant(document[stamped], f"{label} {stamped}")
        source = stamped
    else:
        try:
            collected = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError as exc:
            raise SensorUnavailable(f"cannot stat {path.name}: {exc}") from exc
        source = "file-mtime"
    if collected > now + FUTURE_TOLERANCE:
        raise SensorNotEvaluated(f"stale input: {label} is dated in the future ({source})")
    if now - collected > MAX_INPUT_AGE:
        raise SensorNotEvaluated(
            f"stale input: {label} is older than {MAX_INPUT_AGE.days} days ({source})"
        )
    return {
        "freshnessSource": source,
        "collectedAt": collected.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
