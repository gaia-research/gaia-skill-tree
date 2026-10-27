"""Reviewed fixed-code experiment runner. Reads no lead/packet and executes no packet strings."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "line-history" / "sample-v1.py"
UPDATED = b'''def score(value):\n    # Updated implementation with a bounded input guard.\n    if value < 0:\n        return 0\n    return value + 2\n\n\ndef caller(item):\n    return score(item)\n'''


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUEST = "generated-output/frontier/git-log-L-graft.verification-request-v1.json"
PROTOCOL_PATH = Path(__file__).parent / "protocols" / "git-log-L-vs-graft-v1.json"


def sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git(cwd: Path, *args: str) -> str:
    """Run Git isolated from ambient user/system config, templates and hooks."""
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(cwd), "GIT_TERMINAL_PROMPT": "0"}
    isolation = ["-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false"]
    return subprocess.check_output(["git", *isolation, "-C", str(cwd), *args], stderr=subprocess.STDOUT, text=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="reviewer-controlled receipt output path")
    parser.add_argument("--request", default=DEFAULT_REQUEST, help="bound verification request (repo-relative or absolute); only its id is embedded")
    args = parser.parse_args()
    request_path = Path(args.request)
    request = json.loads((request_path if request_path.is_absolute() else ROOT / request_path).read_text(encoding="utf-8"))
    request_id = request["requestId"]
    fixture_digest = sha(FIXTURE_PATH.read_bytes())
    protocol_digest = sha(PROTOCOL_PATH.read_bytes())
    with tempfile.TemporaryDirectory(prefix="gaia-frontier-git-L-") as td:
        repo = Path(td)
        git(repo, "init", "-q", "--template=")
        git(repo, "config", "user.name", "Frontier Fixture")
        git(repo, "config", "user.email", "fixture@example.invalid")
        target = repo / "sample.py"
        target.write_bytes(FIXTURE_PATH.read_bytes())
        git(repo, "add", "sample.py")
        git(repo, "commit", "-qm", "fixture baseline")
        baseline = git(repo, "rev-parse", "HEAD").strip()
        target.write_bytes(UPDATED)
        git(repo, "add", "sample.py")
        git(repo, "commit", "-qm", "fixture update")
        updated = git(repo, "rev-parse", "HEAD").strip()
        output = git(repo, "log", "--format=%H %s", "-L", ":score:sample.py")
        if baseline not in output or updated not in output or "return value + 1" not in output or "return value + 2" not in output:
            raise RuntimeError("controlled git log -L fixture did not contain both expected revisions and line bodies")
        record = {
            "experiment": "git-log-L-vs-graft-v1",
            "requestId": request_id,
            "fixtureDigest": fixture_digest,
            "protocolDigest": protocol_digest,
            "gitVersion": git(repo, "--version").strip(),
            "fixtureBaselineCommit": baseline,
            "fixtureUpdatedCommit": updated,
            "output": output,
            "outputDigest": "sha256:" + hashlib.sha256(output.encode()).hexdigest(),
            "executionCheck": "passed",
            "result": "inconclusive",
            "interpretation": "The bounded Git operation ran as expected; Graft comparison has not been executed by an independent verifier. No comparative conclusion or public challenge follows.",
            "recordedAtUTC": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:  # exclusive: never overwrite an existing output
        stream.write(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("gitVersion", "fixtureBaselineCommit", "fixtureUpdatedCommit", "outputDigest", "result")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
