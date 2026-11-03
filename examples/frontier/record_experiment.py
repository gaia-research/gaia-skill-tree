"""Bind recorded, reviewer-controlled outputs; never assert verifier authority.

This recorder reads artifacts, not packet commands. A comparative result is a
claim for Meta review, not authentication or public challenge admission.

Receipt construction lives in `gaia_cli.frontier.build_experiment_receipt`; a
protocol file declares the experiment id, version probe, expected artifact keys
and pre-registered result rule. The contract is always read from the protocol file
the request pins; `--protocol`, if given, must name that same file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.frontier import DEFAULT_ARTIFACT_ROOT, EXPERIMENT_RESULTS, build_experiment_receipt, resolve_artifact

DEFAULT_REQUEST = "generated-output/frontier/git-log-L-graft.verification-request-v1.json"
DEFAULT_NATIVE = "generated-output/frontier/git-log-L.execution.json"
DEFAULT_RECEIPT = "generated-output/frontier/git-log-L.experiment-receipt-v1.json"
RESULTS = EXPERIMENT_RESULTS


def artifact_path(root: Path, relative: str, artifact_root: str = DEFAULT_ARTIFACT_ROOT) -> Path:
    """Confine reads/writes to real artifact-root descendants."""
    return resolve_artifact(root, relative, artifact_root)


def build_receipt(*, root: Path, request_rel: str = DEFAULT_REQUEST,
                  native_rel: str = DEFAULT_NATIVE, target_rel: str | None = None,
                  result: str = "inconclusive", protocol: str | None = None,
                  artifact_root: str = DEFAULT_ARTIFACT_ROOT, trace_paths: list[tuple[str, str]] | None = None) -> dict:
    if result not in RESULTS:
        raise ValueError("invalid experimental result")
    request = json.loads(artifact_path(root, request_rel, artifact_root).read_text(encoding="utf-8"))
    return build_experiment_receipt(
        root=root, request=request, execution_path=native_rel, target_path=target_rel, result=result,
        protocol=protocol, artifact_root=artifact_root, trace_paths=trace_paths)


def parse_traces(items: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for item in items:
        label, sep, path = item.partition("=")
        if not sep or not label or not path:
            raise ValueError(f"--trace expects LABEL=PATH, got {item!r}")
        pairs.append((label, path))
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--native-output", default=DEFAULT_NATIVE)
    parser.add_argument("--target-output", help="actual separately recorded paired target output, never a command")
    parser.add_argument("--result", choices=RESULTS, default="inconclusive")
    parser.add_argument("--protocol", help="repo-relative protocol file; must be the one the request pins (default: the pinned file)")
    parser.add_argument("--artifact-root", default=DEFAULT_ARTIFACT_ROOT, help="generated-output/frontier (default) or evidence/frontier-challenges/<id>/artifacts")
    parser.add_argument("--trace", action="append", default=[], metavar="LABEL=PATH", help="raw-stream trace artifact (argv, tool versions, stdout/stderr digests) whose digest the receipt binds; repeatable. Declared, not authenticated")
    parser.add_argument("--output", default=DEFAULT_RECEIPT, help="new receipt path; existing history is never replaced")
    args = parser.parse_args(argv)
    try:
        receipt = build_receipt(root=ROOT, request_rel=args.request, native_rel=args.native_output,
                                target_rel=args.target_output, result=args.result,
                                protocol=args.protocol, artifact_root=args.artifact_root,
                                trace_paths=parse_traces(args.trace))
        destination = artifact_path(ROOT, args.output, args.artifact_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, "recording refused: " + str(exc) + "\n")
    print(args.output)
    print("result", receipt["result"], "verification=untrusted-experiment-record", "admission=blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
