"""Record the currently observed fixed-runner result without asserting independence."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import uuid
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.frontier import validate_experiment_receipt, validate_request

request_rel="generated-output/frontier/git-log-L-graft.verification-request-v1.json"
execution_rel="generated-output/frontier/git-log-L.execution.json"
receipt_rel="generated-output/frontier/git-log-L.experiment-receipt-v1.json"
request=json.loads((ROOT/request_rel).read_text(encoding="utf-8"))
execution_path=ROOT/execution_rel
execution=json.loads(execution_path.read_text(encoding="utf-8"))
if validate_request(request): raise SystemExit("request integrity check failed")
if execution.get("experiment")!="git-log-L-vs-graft-v1" or execution.get("executionCheck")!="passed":
    raise SystemExit("fixed runner output did not match expected reviewed protocol")
if execution.get("gitVersion", "").removeprefix("git version ")!=request["native"]["version"]:
    raise SystemExit("local Git version differs from the candidate version bound by request")
raw=execution_path.read_bytes()
receipt={
    "schemaVersion":"frontier-experiment-receipt-v1",
    "experimentRunId":"run-"+uuid.uuid4().hex,
    "campaignId":request["campaignId"], "nativeVersion":request["native"]["version"],
    "requestId":request["requestId"], "leadDigest":request["leadDigest"], "claimDigest":request["claimDigest"],
    "sourceDigest":request["source"]["contentDigest"], "targetDigest":request["target"]["contentDigest"],
    "targetRevision":request["target"]["revision"], "historyRef":request["historyRef"],
    "protocolDigest":request["protocol"]["contentDigest"], "fixtureDigest":request["fixture"]["contentDigest"],
    # Git fixture ran; the paired actual Graft task has not been independently executed.
    "result":"inconclusive", "outputs":[{"label":"native","contentDigest":"sha256:"+hashlib.sha256(raw).hexdigest(),"path":execution_rel}],
    "limitations":["Fixed Git fixture runner executed; no independent Graft comparison output is present.","This is an untrusted experiment record, not verifier authentication or public challenge admission."],
    "recordedAtUTC":execution["recordedAtUTC"],
}
errors=validate_experiment_receipt(receipt,request,repo_root=ROOT)
if errors: raise SystemExit("receipt invalid: "+"; ".join(errors))
out=ROOT/receipt_rel; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(receipt_rel)
print("result",receipt["result"],"verification=untrusted-experiment-record", "admission=blocked")
