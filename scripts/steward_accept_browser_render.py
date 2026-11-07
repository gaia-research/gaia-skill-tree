#!/usr/bin/env python3
"""Accept a browser-render artifact from the unprivileged collector job, or record why it was not accepted.

The collector (`scripts/steward_collect_browser_render.js`) installs Playwright and runs a browser, so it runs in a job with
`contents: read` and no persisted credentials. The privileged Steward job never runs that code. It downloads the artifact
into a directory and runs this script, which reads exactly two files from it as data:

    python scripts/steward_accept_browser_render.py --from browser-artifact

* Whatever render or status was in `.gaia/steward/inputs/` is deleted first, so nothing older can stand in for the result.
* Both files must be regular files (never symlinks), within a size bound, and valid JSON of the declared schemas.
* The artifact must carry the producer job's own run and attempt (`browser-render-attempt.json`), and that value, the producer job's
  `needs.<job>.outputs.attempt` and this job's `STEWARD_BROWSER_ATTEMPT` must all be present and equal. On a re-run of failed
  jobs, an earlier attempt's artifact therefore fails here instead of being relabelled as current.
* The status must be headless. `ok` needs a valid render; a `failed` or `refused` status (the collector's own honest result,
  with no render) is accepted as itself so the sensor reports the real reason. An interactive claim is rejected.
* The render must pass the browser-render sensor's own structural validation (viewports and renders).
* Accepted files are copied into place. Anything else leaves a current failed status (`collection-incomplete` when the
  artifact is absent, `artifact-rejected` when it is invalid), so the sensor reports NOT EVALUATED, never healthy.

* The outcome is bound to this attempt: an acceptance record (attempt id, digests of the two files) is written, and the run
  started with `--browser-collection external` accepts the render only if that record names its own attempt
  (`STEWARD_BROWSER_ATTEMPT`) and the digests still match. A render that was never accepted for this attempt is invalidated.

Exit 0 always: the run's own evaluation, not this step, decides what a missing browser means. The outcome is printed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.steward import browsercollect  # noqa: E402
from gaia_cli.steward.primitives import SensorUnavailable  # noqa: E402
from gaia_cli.steward.sensors_render import _STATUS_REASONS, BrowserRenderSensor  # noqa: E402

RENDER_SCHEMA = "steward-browser-render-v1"
MAX_BYTES = 8 * 1024 * 1024


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("not a regular file")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("too large")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("not an object")
    return document


ATTEMPT_FILE = "browser-render-attempt.json"
ATTEMPT_SCHEMA = "steward-browser-render-attempt-v1"
PRODUCER_ENV = "STEWARD_BROWSER_PRODUCER_ATTEMPT"


def producerAttemptOf(directory: Path) -> str:
    """The run/attempt the producer job wrote into the artifact itself. Raises ValueError when absent or malformed."""

    document = _read(directory / ATTEMPT_FILE)
    value = document.get("attemptId")
    if document.get("schemaVersion") != ATTEMPT_SCHEMA or not isinstance(value, str) or not value.strip():
        raise ValueError("attempt record")
    return value


def checkAttempt(directory: Path, attemptId: str | None, producerAttempt: str | None) -> None:
    """The artifact must come from THIS run and attempt: its own record, the producer job's output and the consumer's
    attempt must all be present and equal. On a re-run of failed jobs an earlier attempt's artifact fails here."""

    embedded = producerAttemptOf(directory)
    if not attemptId or not producerAttempt or not (embedded == producerAttempt == attemptId):
        raise ValueError("attempt mismatch")


def validate(directory: Path) -> tuple[dict, Path | None, Path]:
    """Return ``(status, render path or None, status path)`` for a valid artifact, or raise ValueError (never echoed).

    An ok status needs a structurally valid headless render. A failed or refused status is a valid, honest result with
    no render: it is accepted as itself so the sensor reports the collector's own reason.
    """

    status = _read(directory / browsercollect.STATUS_RELATIVE.name)
    statusPath = directory / browsercollect.STATUS_RELATIVE.name
    if status.get("schemaVersion") != browsercollect.STATUS_SCHEMA:
        raise ValueError("status schema")
    if status.get("mode") not in ("headless",):
        raise ValueError("only a headless collection is accepted")
    if status.get("state") in ("failed", "refused"):
        if (directory / browsercollect.RENDER_RELATIVE.name).exists():
            raise ValueError("a failed collection must not carry a render")
        if status.get("reason") not in _STATUS_REASONS:
            raise ValueError("status reason")
        return status, None, statusPath
    if status.get("state") != "ok":
        raise ValueError("status state")
    render = _read(directory / browsercollect.RENDER_RELATIVE.name)
    if render.get("schemaVersion") != RENDER_SCHEMA:
        raise ValueError("render schema")
    try:
        viewports = BrowserRenderSensor._viewports(render.get("viewports"))
        BrowserRenderSensor._renders(render.get("renders"), viewports)
        BrowserRenderSensor._unrendered(render.get("unrendered"))
    except SensorUnavailable as exc:
        raise ValueError("render structure") from exc
    return status, directory / browsercollect.RENDER_RELATIVE.name, statusPath


def accept(root: Path, directory: Path, attemptId: str | None = None, producerAttempt: str | None = None) -> dict:
    """Validate the artifact and install it, then bind the result to ``attemptId`` (the run verifies it)."""

    outcome = _accept(root, directory, attemptId, producerAttempt)
    if attemptId:
        browsercollect.writeAcceptance(root, attemptId, outcome["state"])
    return outcome


def _accept(root: Path, directory: Path, attemptId: str | None, producerAttempt: str | None) -> dict:
    browsercollect.invalidateRender(root)
    browsercollect.clearAcceptance(root)
    try:
        (root / browsercollect.STATUS_RELATIVE).unlink()
    except FileNotFoundError:
        pass
    try:
        from gaia_cli.steward.policy import StewardPolicy

        headless = StewardPolicy.load(root).browser.headless
    except Exception:  # noqa: BLE001 - an unreadable policy must not turn collection off silently
        headless = True
    if not headless:
        browsercollect.writeStatus(root, "refused", "headless-disabled", "headless")
        return {"state": "refused", "reason": "headless-disabled"}
    present = directory.is_dir() and any((directory / name).exists() for name in (
        browsercollect.RENDER_RELATIVE.name, browsercollect.STATUS_RELATIVE.name, ATTEMPT_FILE))
    if not present:
        browsercollect.writeStatus(root, "failed", "collection-incomplete", "headless")
        return {"state": "failed", "reason": "collection-incomplete"}
    try:
        checkAttempt(directory, attemptId, producerAttempt)
        status, render, statusPath = validate(directory)
    except (ValueError, OSError):
        browsercollect.writeStatus(root, "failed", "artifact-rejected", "headless")
        return {"state": "failed", "reason": "artifact-rejected"}
    target = root / browsercollect.RENDER_RELATIVE.parent
    target.mkdir(parents=True, exist_ok=True)
    if render is not None:
        shutil.copyfile(render, root / browsercollect.RENDER_RELATIVE)
    shutil.copyfile(statusPath, root / browsercollect.STATUS_RELATIVE)
    if status["state"] == "ok":
        return {"state": "ok", "reason": None}
    return {"state": status["state"], "reason": status["reason"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--from", dest="source", type=Path, required=True, help="directory holding the downloaded artifact")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="checkout whose .gaia/steward/inputs receives the files")
    parser.add_argument("--attempt", default=None, help=f"this job's run and attempt (default: ${browsercollect.ATTEMPT_ENV})")
    parser.add_argument("--producer-attempt", default=None,
                        help=f"the producer job's own run and attempt output (default: ${PRODUCER_ENV})")
    args = parser.parse_args(argv)
    attempt = args.attempt or os.environ.get(browsercollect.ATTEMPT_ENV)
    producer = args.producer_attempt or os.environ.get(PRODUCER_ENV)
    outcome = accept(args.root.resolve(), args.source, attempt, producer)
    print(f"browser-render artifact: {outcome['state']}" + (f" ({outcome['reason']})" if outcome["reason"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
