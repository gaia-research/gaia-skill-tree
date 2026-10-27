"""Build read-only bound request/handoff from the fixed Frontier example."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.frontier import create_verification_request, read_only_handoff, validate_lead

lead_rel = "examples/frontier/git-log-L-graft.challenger-lead-v1.json"
request_rel = "generated-output/frontier/git-log-L-graft.verification-request-v1.json"
handoff_rel = "generated-output/frontier/git-log-L-graft.meta-handoff-v1.json"
lead = json.loads((ROOT / lead_rel).read_text(encoding="utf-8"))
errors = validate_lead(lead)
if errors: raise SystemExit("lead invalid: " + "; ".join(errors))
request = create_verification_request(lead, repo_root=ROOT, lead_path=lead_rel,
    protocol_path="examples/frontier/protocols/git-log-L-vs-graft-v1.json",
    fixture_path="examples/frontier/fixtures/line-history/sample-v1.py")
handoff = read_only_handoff(lead, packet_path=lead_rel, request=request)
for relative, value in ((request_rel, request), (handoff_rel, handoff)):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(relative)
print("request", request["requestId"])
print("handoff verification", handoff["verification"], handoff["advisoryMatch"])
