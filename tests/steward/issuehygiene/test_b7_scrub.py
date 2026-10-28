"""Lane B7 round-2 credential scrub (M3): every new shape is replaced in every place that stores text.

The stored places are the closing comments, the preserved original payload, the snapshot title, the receipts
and the ledger action params. Each shape is planted in a child intake's title, then the raw value must be absent
from all of them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import _executeProvenClosure as executeClosure, planClosures
from gaia_cli.steward.issuehygiene.executor import compactPlan
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT
from gaia_cli.steward.primitives.redact import scrub
from tests.steward.issuehygiene.e_fakes import censusOf as censusOfDocument
from tests.steward.issuehygiene.test_b5_closure_guard import Forge, checkout
from tests.steward.issuehygiene.test_b_closure import liveOf
from tests.steward.issuehygiene.test_b_reconcile import NOW, policyFor

# (name, the raw value that must never be stored, text that contains it)
SHAPES = [
    ("hf", "hf_" + "a" * 34, "token " + "hf_" + "a" * 34),
    ("npm", "npm_" + "B" * 36, "npm_" + "B" * 36),
    ("gitlab", "glpat-" + "x" * 20 + "_y", "glpat-" + "x" * 20 + "_y"),
    ("jwt", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
     "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
    ("bearer", "abcdefghijklmnop1234", "Authorization: Bearer abcdefghijklmnop1234"),
    ("password", "hunter2hunter2", 'password = "hunter2hunter2"'),
    ("secret", "s3cr3t-value-xyz", "secret: s3cr3t-value-xyz"),
    ("token-assign", "tok-abcdef123456", "token=tok-abcdef123456"),
    ("api-key", "zzabc123def456", "api_key: zzabc123def456"),
    ("aws-40", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
]


@pytest.mark.parametrize(("name", "raw", "text"), SHAPES)
def test_every_shape_is_replaced_by_its_fingerprint(name: str, raw: str, text: str) -> None:
    replaced = scrub(text)
    assert raw not in replaced
    assert "sha256=" in replaced


@pytest.mark.parametrize(("name", "raw", "text"), SHAPES)
def test_no_stored_place_keeps_the_raw_value(tmp_path: Path, name: str, raw: str, text: str) -> None:
    root, document = checkout(tmp_path)
    for row in document["issues"]:
        if row["number"] == 10:
            row["title"] = f"[intake] obra/writing-skills {text}"
    (root / CENSUS_INPUT).write_text(json.dumps(document), encoding="utf-8")
    manifest = reconcile(censusOfDocument(document), buildRegistryIndex(root), policyFor(), NOW)
    plan = next(p for p in planClosures(manifest, policyFor()) if p["issue"] == 10)

    stored = [
        json.dumps(plan["original"], sort_keys=True),        # the preserved original payload
        "".join(plan["comments"]),                            # the closing comments
        json.dumps(plan["expectedSnapshot"], sort_keys=True),  # the snapshot title
        json.dumps(compactPlan(plan), sort_keys=True),         # the ledger action params
        json.dumps(plan["evidence"], sort_keys=True),
    ]
    for text_ in stored:
        assert raw not in text_, name

    live = liveOf(next(row for row in document["issues"] if row["number"] == 10))
    receipts = tmp_path / "receipts" / "R1.jsonl"
    executeClosure(plan, Forge({10: live}), receipts, NOW, "R1", "gaia-research/gaia-skill-tree")
    assert raw not in receipts.read_text(encoding="utf-8"), name  # the receipt
