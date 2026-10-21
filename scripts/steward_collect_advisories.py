#!/usr/bin/env python3
"""Turn `pip-audit --format json` output into the dependency-advisory sensor's driver input.

The Steward sensors never touch the network. A driver (the scheduled workflow,
or an operator) runs the audit and hands the result over as
`.gaia/steward/inputs/advisories.json`. This script is that hand-over: a pure
transform with no network access of its own.

    pip-audit --format json > pip-audit.json
    python scripts/steward_collect_advisories.py pip-audit.json \
      --repository gaia-research/gaia-skill-tree

The output carries `collectedAt`, the instant the freshness check reads, so the
sensor does not have to fall back to the file's modification time. Only the
fields the sensor reads are kept from each vulnerability. Dependencies pip-audit
could not resolve (`name` plus `skip_reason`) are kept as skips, never dropped:
the sensor reports them as not audited rather than clean.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT = Path(".gaia/steward/inputs/advisories.json")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


class InputError(ValueError):
    """The pip-audit output is not a shape the dependency-advisory sensor accepts."""


def require_text(mapping: dict[str, Any], key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where} requires a non-empty string {key}")
    return value


def convert_vulnerability(vuln: Any, where: str) -> dict[str, Any]:
    if not isinstance(vuln, dict):
        raise InputError(f"{where} is not an object")
    fix_versions = vuln.get("fix_versions", [])
    if not isinstance(fix_versions, list) or not all(isinstance(item, str) for item in fix_versions):
        raise InputError(f"{where} requires fix_versions as a list of strings")
    return {"id": require_text(vuln, "id", where), "fix_versions": fix_versions}


def convert_dependency(dependency: Any, index: int) -> dict[str, Any]:
    where = f"dependency {index}"
    if not isinstance(dependency, dict):
        raise InputError(f"{where} is not an object")
    name = require_text(dependency, "name", where)
    if "version" not in dependency and "skip_reason" in dependency:
        # Mirrors the sensor: pip-audit could not resolve this package, so it is
        # carried through as a skip. It must never be turned into a clean entry.
        reason = dependency["skip_reason"]
        if not isinstance(reason, str):
            raise InputError(f"{where} skip_reason must be a string")
        return {"name": name, "skip_reason": reason}
    vulns = dependency.get("vulns")
    if not isinstance(vulns, list):
        raise InputError(f"{where} requires a vulns list")
    findings = [
        convert_vulnerability(vuln, f"{where} vulnerability {position}")
        for position, vuln in enumerate(vulns)
    ]
    return {"name": name, "version": require_text(dependency, "version", where), "vulns": findings}


def convert(raw: Any, *, repository: str, collected_at: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise InputError("pip-audit output must be a JSON object")
    dependencies = raw.get("dependencies")
    if not isinstance(dependencies, list):
        raise InputError("pip-audit output has no dependencies list")
    fixes = raw.get("fixes", [])
    if not isinstance(fixes, list):
        raise InputError("pip-audit fixes must be a list when present")
    return {
        "collectedAt": collected_at,
        "repository": repository,
        "dependencies": [convert_dependency(item, index) for index, item in enumerate(dependencies)],
        "fixes": fixes,
    }


def publish(path: Path, document: dict[str, Any]) -> None:
    """Write the document so a reader sees either the old file or the complete new one."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle, staged = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
    except BaseException:
        Path(staged).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="file holding `pip-audit --format json` output")
    parser.add_argument("--repository", required=True, help="owner/name of the audited checkout")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        if not REPOSITORY.fullmatch(args.repository):
            raise InputError("--repository must be owner/name")
        raw = json.loads(args.source.read_text(encoding="utf-8"))
        document = convert(
            raw,
            repository=args.repository,
            collected_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        publish(args.output, document)
    except (OSError, json.JSONDecodeError, InputError) as exc:
        print(f"steward_collect_advisories: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {len(document['dependencies'])} dependencies to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
