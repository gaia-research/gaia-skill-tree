"""The one shared helper that gives a temporary test registry a readable authorization index.

Authorization fails closed when ``registry/named-skills.json`` is missing or malformed
(founder ruling 2026-11-08, ``founder/steward/decisions/steward-authz-fail-closed-2283.json``).
A temp registry that omitted the file used to bootstrap-allow by accident; now it is
denied before the verb under test runs. Every temp-registry builder whose tests drive a
gated ``gaia dev`` verb calls this, so the real bootstrap decision (a readable index with
zero Verifiers) is what runs. Tests of the denial itself write their own index, or none.
"""

from __future__ import annotations

import json
from pathlib import Path

from gaia_cli.registry import named_skills_index_path


def writeBootstrapIndex(registryRoot) -> Path:
    """Write a readable, empty authorization index (zero Verifiers) under ``registryRoot``."""
    path = Path(named_skills_index_path(str(registryRoot)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"buckets": {}, "byContributor": {}, "awaitingClassification": []}),
        encoding="utf-8",
    )
    return path
