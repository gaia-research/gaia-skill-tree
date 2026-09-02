#!/usr/bin/env python3
"""Run the gaia-curate command spine against a bounded temporary fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
FIXTURE = SKILL_DIR / "fixtures" / "playbook-runtime"
FIXTURE_SOURCE = FIXTURE / "source" / "UPSTREAM_SKILL.md"
CAPTURED_AT = "2026-09-02T00:00:00Z"


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(item.read_bytes())
    return digest.hexdigest()


def _run_cli(arguments: list[str], workspace: Path, invocations: dict[str, int]) -> str:
    env = os.environ.copy()
    fixture_python = FIXTURE / "python"
    src = ROOT / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(fixture_python), str(src), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "gaia_cli", "--registry", str(workspace), *arguments],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gaia {' '.join(arguments)} failed ({result.returncode}): {result.stderr}"
        )
    command = " ".join(arguments[:2])
    invocations[command] = invocations.get(command, 0) + 1
    return result.stdout


def _source_frontmatter(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise RuntimeError("fixture source is missing YAML frontmatter")
    _start, frontmatter, _body = content.split("---", 2)
    parsed = yaml.safe_load(frontmatter)
    if not isinstance(parsed, dict):
        raise RuntimeError("fixture source frontmatter is not an object")
    return {"name": parsed["name"], "description": parsed["description"]}


def _fixed_bounded_decision(prefill: dict) -> dict[str, str]:
    if prefill.get("exactDedupe", {}).get("matched"):
        raise RuntimeError("fixture unexpectedly entered exact-dedupe disposition")
    strong = [
        option
        for option in prefill.get("mappingOptions", [])
        if option.get("matchTier") == "strong"
    ]
    if len(strong) != 1:
        raise RuntimeError(f"fixture requires exactly one strong mapping option; got {len(strong)}")
    return {
        "value": "MAP",
        "reasonCode": "MAP_EXISTING_GENERIC",
        "genericId": strong[0]["genericId"],
    }


def run(output_dir: Path) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace = output_dir / "workspace"
    shutil.copytree(FIXTURE / "workspace", workspace)
    registry_before = _tree_digest(workspace / "registry")
    invocations: dict[str, int] = {}

    snapshot_stdout = _run_cli(
        ["dev", "list", "--generic", "--json"], workspace, invocations
    )
    snapshot = json.loads(snapshot_stdout)
    snapshot_path = output_dir / "generic-snapshot.json"
    snapshot_path.write_text(snapshot_stdout, encoding="utf-8")

    candidate = {
        "id": "candidate-playbook-001",
        "name": "Example Skill",
        "description": "A reusable example capability with an explicit operating boundary.",
        "url": "https://github.com/example/repo/blob/main/skills/example/SKILL.md",
        "sourceLane": "source-repository",
    }
    prefill_stdout = _run_cli(
        [
            "dev",
            "prefill",
            candidate["id"],
            "--name",
            candidate["name"],
            "--description",
            candidate["description"],
            "--url",
            candidate["url"],
            "--source-lane",
            candidate["sourceLane"],
            "--json",
        ],
        workspace,
        invocations,
    )
    prefill = json.loads(prefill_stdout)
    prefill_path = output_dir / "prefill-packet.json"
    prefill_path.write_text(prefill_stdout, encoding="utf-8")

    decision = _fixed_bounded_decision(prefill)
    source_path = FIXTURE_SOURCE
    source_frontmatter = _source_frontmatter(source_path)
    if source_frontmatter != prefill["normalized"]:
        raise RuntimeError("prefill normalized fields do not match fetched source frontmatter")

    packet = dict(prefill)
    packet["lifecycle"] = [
        "discovered",
        "fetched",
        "parsed",
        "normalized",
        "deduped",
        "mapped",
        "review-ready",
    ]
    packet["source"] = {
        **prefill["source"],
        "hostRepository": "https://github.com/example/repo",
        "fetchedAt": CAPTURED_AT,
        "contentSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "frontmatter": source_frontmatter,
    }
    packet["genericSnapshot"] = {
        "capturedAt": CAPTURED_AT,
        "command": "gaia dev list --generic --json",
        "generics": snapshot,
        "contentSha256": _canonical_digest(snapshot),
        "mappingOptionsSha256": _canonical_digest(prefill["mappingOptions"]),
    }
    packet["decision"] = decision
    packet_path = output_dir / f"{candidate['id']}.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    validator = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_discovery_packet.py"),
            "--generic-snapshot",
            str(snapshot_path),
            str(packet_path),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if validator.returncode != 0:
        raise RuntimeError(f"packet validator failed: {validator.stderr}")

    selected = next(
        option for option in packet["mappingOptions"] if option["genericId"] == decision["genericId"]
    )
    presentation = output_dir / "L4-REVIEW.md"
    presentation.write_text(
        "\n".join(
            [
                "# L4 discovery review",
                "",
                f"- Candidate: `{packet['candidateId']}`",
                f"- Disposition: `{decision['value']}` (`{decision['reasonCode']}`)",
                f"- Generic: `{decision['genericId']}`",
                f"- Signal: `{selected['matchTier']}` at `{selected['similarity']:.6f}`",
                f"- Source: {packet['source']['canonicalUrl']}",
                f"- Packet: `{packet_path.name}`",
                "- Boundary: stop at L4; no intake, registry, Git, or GitHub mutation.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry_after = _tree_digest(workspace / "registry")
    if registry_after != registry_before:
        raise RuntimeError("fixture run mutated its isolated registry")

    receipt = {
        "snapshotInvocationCount": invocations.get("dev list", 0),
        "prefillInvocationCount": invocations.get("dev prefill", 0),
        "decision": decision,
        "registrySha256Before": registry_before,
        "registrySha256After": registry_after,
        "validator": validator.stdout.strip(),
        "packet": str(packet_path),
        "presentation": str(presentation),
    }
    (output_dir / "run-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = run(args.output_dir)
    except (KeyError, OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"fixture dry-run failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
