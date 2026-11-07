#!/usr/bin/env python3
"""Accept a browser-render artifact from the unprivileged collector job, or record why it was not accepted.

The collector (`scripts/steward_collect_browser_render.js`) installs Playwright and runs a browser, so it runs in a job with
`contents: read` and no persisted credentials. The privileged Steward job never runs that code. It downloads the artifact
into a directory and runs this script, which reads exactly two files from it as data:

    python scripts/steward_accept_browser_render.py --from browser-artifact

* Whatever render or status was in `.gaia/steward/inputs/` is deleted first, so nothing older can stand in for the result.
* Both files must be regular files (never symlinks), within a size bound, and valid JSON of the declared schemas.
* The status must say `ok` and `headless`: an artifact claiming an interactive browser, or a failed attempt, is not a result.
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
from gaia_cli.steward.sensors_render import BrowserRenderSensor  # noqa: E402

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


def validate(directory: Path) -> tuple[Path, Path]:
    """Return the two validated file paths, or raise ValueError with a reason that is never echoed."""

    render = _read(directory / browsercollect.RENDER_RELATIVE.name)
    status = _read(directory / browsercollect.STATUS_RELATIVE.name)
    if status.get("schemaVersion") != browsercollect.STATUS_SCHEMA or status.get("state") != "ok":
        raise ValueError("status is not an ok status")
    if status.get("mode") != "headless":
        raise ValueError("only a headless collection is accepted")
    if render.get("schemaVersion") != RENDER_SCHEMA:
        raise ValueError("render schema")
    try:
        viewports = BrowserRenderSensor._viewports(render.get("viewports"))
        BrowserRenderSensor._renders(render.get("renders"), viewports)
        BrowserRenderSensor._unrendered(render.get("unrendered"))
    except SensorUnavailable as exc:
        raise ValueError("render structure") from exc
    return directory / browsercollect.RENDER_RELATIVE.name, directory / browsercollect.STATUS_RELATIVE.name


def accept(root: Path, directory: Path, attemptId: str | None = None) -> dict:
    """Validate the artifact and install it, then bind the result to ``attemptId`` (the run verifies it)."""

    outcome = _accept(root, directory)
    if attemptId:
        browsercollect.writeAcceptance(root, attemptId, outcome["state"])
    return outcome


def _accept(root: Path, directory: Path) -> dict:
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
        browsercollect.RENDER_RELATIVE.name, browsercollect.STATUS_RELATIVE.name))
    if not present:
        browsercollect.writeStatus(root, "failed", "collection-incomplete", "headless")
        return {"state": "failed", "reason": "collection-incomplete"}
    try:
        render, status = validate(directory)
    except (ValueError, OSError):
        browsercollect.writeStatus(root, "failed", "artifact-rejected", "headless")
        return {"state": "failed", "reason": "artifact-rejected"}
    target = root / browsercollect.RENDER_RELATIVE.parent
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(render, root / browsercollect.RENDER_RELATIVE)
    shutil.copyfile(status, root / browsercollect.STATUS_RELATIVE)
    return {"state": "ok", "reason": None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--from", dest="source", type=Path, required=True, help="directory holding the downloaded artifact")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="checkout whose .gaia/steward/inputs receives the files")
    parser.add_argument("--attempt", default=None, help=f"attempt id the run will verify (default: ${browsercollect.ATTEMPT_ENV})")
    args = parser.parse_args(argv)
    attempt = args.attempt or os.environ.get(browsercollect.ATTEMPT_ENV)
    outcome = accept(args.root.resolve(), args.source, attempt)
    print(f"browser-render artifact: {outcome['state']}" + (f" ({outcome['reason']})" if outcome["reason"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
