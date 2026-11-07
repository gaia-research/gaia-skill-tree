"""The browser-render collection attempt, owned by the run that needs it (founder ruling steward-browser-render-driver).

Headless Chromium is on by default for scheduled and founder runs, so the run itself starts the collector. A real,
interactive browser is only ever started when THIS run was given ``--interactive-browser``: the collector gets
``STEWARD_INTERACTIVE_BROWSER=1`` from here and from nowhere else.

Evidence is tied to the attempt. Before the collector starts, the previous render is deleted and a status marker
``failed / collection-incomplete`` is written. The collector overwrites the marker with ``ok`` only when it finishes. A
collector that is killed, times out, cannot start or never writes anything therefore leaves a current failed status and no
render, so the browser-render sensor reports NOT EVALUATED. An older render is never evaluated as healthy.

Nothing here touches the network; the collector serves the tracked ``docs/`` tree locally and aborts every external request.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

RENDER_RELATIVE = Path(".gaia/steward/inputs/browser-render.json")
STATUS_RELATIVE = Path(".gaia/steward/inputs/browser-render-status.json")
STATUS_SCHEMA = "steward-browser-render-status-v1"
ACCEPTANCE_RELATIVE = Path(".gaia/steward/inputs/browser-render-accepted.json")
ACCEPTANCE_SCHEMA = "steward-browser-render-accepted-v1"
ATTEMPT_ENV = "STEWARD_BROWSER_ATTEMPT"
COLLECTOR_RELATIVE = Path("scripts/steward_collect_browser_render.js")
# Where a driver installs the collector's single dependency without running any package lifecycle script.
NODE_MODULES_RELATIVE = Path("scripts/steward-browser/node_modules")
COLLECT_TIMEOUT_SECONDS = 1200
MODES = ("headless", "interactive")


def _stamp(moment: datetime | None = None) -> str:
    return (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def writeStatus(root: Path, state: str, reason: str | None, mode: str, *, at: datetime | None = None) -> None:
    """Record how the current collection attempt ended. ``reason`` is required unless the state is ok."""

    if state not in ("ok", "failed", "refused") or mode not in MODES:
        raise ValueError("unknown browser collection state or mode")
    document: dict[str, Any] = {"schemaVersion": STATUS_SCHEMA, "state": state, "collectedAt": _stamp(at), "mode": mode}
    if state != "ok":
        document["reason"] = reason
    target = root / STATUS_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".browser-render-status-{os.getpid()}.tmp")
    temporary.write_text(json.dumps(document), encoding="utf-8")
    os.replace(temporary, target)


def invalidateRender(root: Path) -> None:
    """Delete the previous render so it can never be read as the result of the attempt about to start."""

    try:
        (root / RENDER_RELATIVE).unlink()
    except FileNotFoundError:
        pass


def collectorEnvironment(root: Path, interactive: bool) -> dict[str, str]:
    """The collector's environment. The interactive switch exists only when this run authorized it."""

    env = {key: value for key, value in os.environ.items() if key != "STEWARD_INTERACTIVE_BROWSER"}
    modules = root / NODE_MODULES_RELATIVE
    if modules.is_dir():
        env["NODE_PATH"] = os.pathsep.join(filter(None, [str(modules), env.get("NODE_PATH", "")]))
    if interactive:
        env["STEWARD_INTERACTIVE_BROWSER"] = "1"
    return env


def collect(
    root: Path,
    *,
    repository: str | None,
    headless: bool,
    interactive: bool,
    run: Callable[..., Any] = subprocess.run,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    timeout: float = COLLECT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run one collection attempt and return ``{state, reason, mode}`` as recorded in the status file."""

    mode = "interactive" if interactive else "headless"
    invalidateRender(root)
    if not interactive and not headless:
        writeStatus(root, "refused", "headless-disabled", mode, at=now())
        return {"state": "refused", "reason": "headless-disabled", "mode": mode}
    # The attempt marker: anything short of a clean finish leaves this behind.
    writeStatus(root, "failed", "collection-incomplete", mode, at=now())
    if not repository:
        writeStatus(root, "failed", "collection-error", mode, at=now())
        return {"state": "failed", "reason": "collection-error", "mode": mode}
    command = ["node", str(root / COLLECTOR_RELATIVE), "--repository", repository, "--out", str(root / RENDER_RELATIVE)]
    if interactive:
        command.append("--interactive")
    try:
        finished = run(command, cwd=str(root), env=collectorEnvironment(root, interactive), capture_output=True,
                       text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        # Whatever the collector wrote before it hung is not a result: overwrite the status and drop the render.
        invalidateRender(root)
        writeStatus(root, "failed", "collection-incomplete", mode, at=now())
        return {"state": "failed", "reason": "collection-incomplete", "mode": mode}
    except OSError:
        writeStatus(root, "failed", "collection-error", mode, at=now())
        return {"state": "failed", "reason": "collection-error", "mode": mode}
    if getattr(finished, "returncode", 0) != 0:
        # A collector that exits nonzero did not complete, even if it had already written an ok status or a render.
        current = recorded(root, mode)
        invalidateRender(root)
        if current["state"] == "ok":
            writeStatus(root, "failed", "collection-error", mode, at=now())
            return {"state": "failed", "reason": "collection-error", "mode": mode}
        return current  # an honest failed or refused status written by the collector itself stays
    return recorded(root, mode)


def recorded(root: Path, mode: str) -> dict[str, Any]:
    """What the status file says now. A clean ok needs the render to exist too; otherwise it is not ok."""

    try:
        status = json.loads((root / STATUS_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        status = {}
    state = status.get("state") if isinstance(status, Mapping) else None
    if state == "ok" and not (root / RENDER_RELATIVE).is_file():
        writeStatus(root, "failed", "collection-incomplete", mode)
        return {"state": "failed", "reason": "collection-incomplete", "mode": mode}
    state = state if state in ("ok", "failed", "refused") else "failed"
    reason = None if state == "ok" else ((status.get("reason") if isinstance(status, Mapping) else None) or "collection-incomplete")
    return {"state": state, "reason": reason, "mode": mode}


# --- external collection: an earlier job collected, and the run verifies it was accepted for THIS attempt ---------


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def writeAcceptance(root: Path, attemptId: str, state: str) -> None:
    """Bind the files now on disk to one attempt. Written by the validator, checked by the run."""

    document = {
        "schemaVersion": ACCEPTANCE_SCHEMA,
        "attemptId": attemptId,
        "state": state,
        "statusSha256": _digest(root / STATUS_RELATIVE),
        "renderSha256": _digest(root / RENDER_RELATIVE),
    }
    target = root / ACCEPTANCE_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".browser-render-accepted-{os.getpid()}.tmp")
    temporary.write_text(json.dumps(document), encoding="utf-8")
    os.replace(temporary, target)


def clearAcceptance(root: Path) -> None:
    try:
        (root / ACCEPTANCE_RELATIVE).unlink()
    except FileNotFoundError:
        pass


def verifyExternal(
    root: Path, attemptId: str | None, *, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    """Accept an externally collected render only with a same-attempt acceptance whose digests still match the files.

    Anything else (no attempt id, no acceptance, another attempt, files changed since acceptance, an old render left
    on disk) invalidates the render and records a current failed status, so a stale input is never evaluated as healthy.
    """

    mode = "headless"
    try:
        accepted = json.loads((root / ACCEPTANCE_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        accepted = None
    statusDigest = _digest(root / STATUS_RELATIVE)
    valid = (
        bool(attemptId)
        and isinstance(accepted, Mapping)
        and accepted.get("schemaVersion") == ACCEPTANCE_SCHEMA
        and accepted.get("attemptId") == attemptId
        and statusDigest is not None
        and accepted.get("statusSha256") == statusDigest
        and accepted.get("renderSha256") == _digest(root / RENDER_RELATIVE)
    )
    if not valid:
        invalidateRender(root)
        writeStatus(root, "failed", "collection-incomplete", mode, at=now())
        return {"state": "failed", "reason": "collection-incomplete", "mode": mode, "external": True}
    result = recorded(root, mode)
    result["external"] = True
    return result
