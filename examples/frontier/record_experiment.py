"""Bind recorded, reviewer-controlled outputs; never assert verifier authority.

This recorder reads artifacts, not packet commands. A comparative result is a
claim for Meta review, not authentication or public challenge admission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.frontier import validate_experiment_receipt, validate_request

DEFAULT_REQUEST = "generated-output/frontier/git-log-L-graft.verification-request-v1.json"
DEFAULT_NATIVE = "generated-output/frontier/git-log-L.execution.json"
DEFAULT_RECEIPT = "generated-output/frontier/git-log-L.experiment-receipt-v1.json"
RESULTS = ("supported", "contradicted", "inconclusive", "execution_failed")


def artifact_path(root: Path, relative: str) -> Path:
    """Confine reads/writes to real generated-output/frontier descendants."""
    root = root.resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or rel.parts[:2] != ("generated-output", "frontier") or len(rel.parts) < 3:
        raise ValueError("artifact must be a relative generated-output/frontier descendant")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("artifact paths must not contain symlinks")
    if not current.resolve().is_relative_to(root):
        raise ValueError("artifact is outside checkout")
    return current


def artifact_source(root: Path, relative: str) -> Path:
    rel = Path(relative)
    path = (root / rel).resolve()
    if rel.is_absolute() or ".." in rel.parts or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("request input path is not a file inside the checkout")
    return path


def build_receipt(*, root: Path, request_rel: str = DEFAULT_REQUEST,
                  native_rel: str = DEFAULT_NATIVE, target_rel: str | None = None,
                  result: str = "inconclusive") -> dict:
    if result not in RESULTS:
        raise ValueError("invalid experimental result")
    request = json.loads(artifact_path(root, request_rel).read_text(encoding="utf-8"))
    if validate_request(request):
        raise ValueError("request integrity check failed")
    native_raw = artifact_path(root, native_rel).read_bytes()
    execution = json.loads(native_raw)
    if not isinstance(execution, dict) or execution.get("experiment") != "git-log-L-vs-graft-v1" or execution.get("executionCheck") != "passed":
        raise ValueError("fixed runner output did not match expected reviewed protocol")
    if execution.get("gitVersion") not in {request["native"]["version"], "git version " + request["native"]["version"]}:
        raise ValueError("local Git version differs from candidate version bound by request")
    for key, expected in (("requestId", request["requestId"]), ("fixtureDigest", request["fixture"]["contentDigest"]), ("protocolDigest", request["protocol"]["contentDigest"])):
        if execution.get(key) != expected:
            raise ValueError(f"native artifact {key} does not match the request")
    # Also bind to the actual files this checkout holds, not only the request's claim.
    for key, spec in (("fixtureDigest", request["fixture"]), ("protocolDigest", request["protocol"])):
        actual = "sha256:" + hashlib.sha256(artifact_source(root, spec["path"]).read_bytes()).hexdigest()
        if actual != spec["contentDigest"]:
            raise ValueError(f"checkout {key[:-6]} bytes differ from the request")
    output = execution.get("output")
    if not isinstance(output, str) or execution.get("outputDigest") != "sha256:" + hashlib.sha256(output.encode("utf-8")).hexdigest():
        raise ValueError("native recorded output digest mismatch")
    outputs = [{"label": "native", "contentDigest": "sha256:" + hashlib.sha256(native_raw).hexdigest(), "path": native_rel}]
    limitations = ["This is an untrusted experiment record, not verifier authentication or public challenge admission."]
    if target_rel is not None:
        target_raw = artifact_path(root, target_rel).read_bytes()
        if not target_raw.strip():
            raise ValueError("target output artifact is empty")
        if artifact_path(root, native_rel) == artifact_path(root, target_rel):
            raise ValueError("native and target outputs must be distinct artifacts")
        if hashlib.sha256(target_raw).digest() == hashlib.sha256(native_raw).digest():
            raise ValueError("native and target outputs must have distinct content")
        outputs.append({"label": "target", "contentDigest": "sha256:" + hashlib.sha256(target_raw).hexdigest(), "path": target_rel})
        limitations.append("Paired artifacts alone establish neither comparable performance, superiority nor independent verification; Meta must assess protocol execution and counterevidence.")
    else:
        limitations.append("Fixed Git fixture runner executed; no target comparison output is attached.")
    receipt = {
        "schemaVersion": "frontier-experiment-receipt-v1", "experimentRunId": "run-" + uuid.uuid4().hex,
        "campaignId": request["campaignId"], "nativeVersion": request["native"]["version"],
        "requestId": request["requestId"], "leadDigest": request["leadDigest"], "claimDigest": request["claimDigest"],
        "sourceDigest": request["source"]["contentDigest"], "targetDigest": request["target"]["contentDigest"],
        "targetRevision": request["target"]["revision"], "historyRef": request["historyRef"],
        "protocolDigest": request["protocol"]["contentDigest"], "fixtureDigest": request["fixture"]["contentDigest"],
        "result": result, "outputs": outputs, "limitations": limitations,
        "recordedAtUTC": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    errors = validate_experiment_receipt(receipt, request, repo_root=root)
    if errors:
        raise ValueError("receipt invalid: " + "; ".join(errors))
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--native-output", default=DEFAULT_NATIVE)
    parser.add_argument("--target-output", help="actual separately recorded paired target output, never a command")
    parser.add_argument("--result", choices=RESULTS, default="inconclusive")
    parser.add_argument("--output", default=DEFAULT_RECEIPT, help="new receipt path; existing history is never replaced")
    args = parser.parse_args(argv)
    try:
        receipt = build_receipt(root=ROOT, request_rel=args.request, native_rel=args.native_output,
                                target_rel=args.target_output, result=args.result)
        destination = artifact_path(ROOT, args.output)
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
