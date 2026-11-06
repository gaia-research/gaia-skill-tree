"""Build a read-only bound verification request and Meta handoff from a lead, protocol and fixture.

With no arguments this reproduces the original fixed git-log-L example. A different
experiment supplies its own `--lead`, `--protocol` and `--fixture`; the protocol and
fixture bytes (and the lead's target and captured source) are bound into the request.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.frontier import create_verification_request, experiment_declaration, read_only_handoff, validate_lead

DEFAULT_LEAD = "examples/frontier/git-log-L-graft.challenger-lead-v1.json"
DEFAULT_PROTOCOL = "examples/frontier/protocols/git-log-L-vs-graft-v1.json"
DEFAULT_FIXTURE = "examples/frontier/fixtures/line-history/sample-v1.py"


def defaultOutputs(lead_rel: str) -> tuple[str, str]:
    stem = re.sub(r"\.challenger-lead-v1$", "", Path(lead_rel).stem)
    return (f"generated-output/frontier/{stem}.verification-request-v1.json", f"generated-output/frontier/{stem}.meta-handoff-v1.json")


ALLOWED_OUTPUT_PREFIXES = (("generated-output",), ("evidence", "frontier-challenges"))


def checkedOutput(relative: str) -> Path:
    """Repo-relative output under generated-output/ or evidence/frontier-challenges/, never over a tracked file."""
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not any(rel.parts[:len(p)] == p and len(rel.parts) > len(p) for p in ALLOWED_OUTPUT_PREFIXES):
        raise ValueError("output path must be repo-relative under generated-output/ or evidence/frontier-challenges/")
    path = (ROOT / rel).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("output path escapes the checkout")
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", rel.as_posix()], capture_output=True).returncode == 0
    if tracked:
        raise ValueError(f"refusing to overwrite tracked file: {relative}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lead", default=DEFAULT_LEAD, help="repo-relative challenger lead JSON")
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL, help="repo-relative reviewed protocol file (committed at HEAD)")
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="repo-relative reviewed fixture file (committed at HEAD)")
    parser.add_argument("--request-out", help="request output path (default derives from the lead name)")
    parser.add_argument("--handoff-out", help="handoff output path (default derives from the lead name)")
    args = parser.parse_args(argv)
    request_rel, handoff_rel = defaultOutputs(args.lead)
    request_rel, handoff_rel = args.request_out or request_rel, args.handoff_out or handoff_rel
    try:
        lead = json.loads((ROOT / args.lead).read_text(encoding="utf-8"))
        errors = validate_lead(lead)
        if errors:
            raise ValueError("lead invalid: " + "; ".join(errors))
        # Fail before binding if the protocol declares no (or a malformed) experiment contract.
        protocol = json.loads((ROOT / args.protocol).read_text(encoding="utf-8"))
        experiment_declaration(protocol)
        request = create_verification_request(lead, repo_root=ROOT, lead_path=args.lead,
            protocol_path=args.protocol, fixture_path=args.fixture)
        handoff = read_only_handoff(lead, packet_path=args.lead, request=request)
        destinations = [(relative, checkedOutput(relative), value) for relative, value in ((request_rel, request), (handoff_rel, handoff))]
        for relative, path, value in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            print(relative)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, "request build refused: " + str(exc) + "\n")
    print("request", request["requestId"])
    print("handoff verification", handoff["verification"], handoff["advisoryMatch"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
