"""Optional cached #1833 offline normal-path proof; never fetches issue data.

Set P1_LEGACY_CACHE to the owner's bounded JSON cache. The issue body is untrusted
fixture data and never printed/committed. Release responses below are explicitly
SYNTHETIC, not assertions about current upstream latest tags or deployed main.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from scripts.lib import named_iterator
from scripts.upstream_watcher import watcher
from scripts.upstream_watcher.live import LiveGh
from test_count_2278 import ConnectionRunner, mixedRows


@pytest.mark.skipif(not os.environ.get("P1_LEGACY_CACHE"), reason="owner-supplied bounded cache not configured; no network fallback")
def test_cached_identity_case_via_real_normal_offline_transport(monkeypatch, tmp_path):
    cache_path = Path(os.environ["P1_LEGACY_CACHE"])
    cache_digest = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    body = cached["body"]
    raw_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    root = Path(__file__).resolve().parents[2]
    direction = json.loads((root / "founder/reports/upstream-backlog-2026-11/P1_IDENTITY_FOUNDER_DECISIONS.json").read_text())
    # Technical framing proof only; operational code NEVER tries alternate hashes.
    assert raw_sha == "ae62e163b04c2b24057d629ff1024a19982c8180d88a7ad2c5b64707f3ab8d1a"
    assert hashlib.sha256((body + "\n").encode("utf-8")).hexdigest() == direction["issueBodySha256"]
    assert cached["number"] == 1833

    named = tmp_path / "named"
    named.mkdir()
    sources = {"ruvnet/dual-mode": "ruvnet/ruflo", "ruvnet/ruflo": "ruvnet/ruflo",
               "ruvnet/agentdb": "ruvnet/AgentDB", "garrytan/gstack": "garrytan/gstack"}
    for identifier, repo in sources.items():
        (named / (identifier.replace("/", "-") + ".md")).write_text(
            f'---\nid: {identifier}\nname: Offline fixture\nlevel: "2★"\n'
            f'suiteComponents: [fixture/component]\nsuiteRef: ruvnet/ruflo\n'
            f'links:\n  github: https://github.com/{repo}\n'
            f'upstream:\n  repo: {repo}\n  version: v0\n---\n', encoding="utf-8")
    monkeypatch.setattr(named_iterator, "_DEFAULT_NAMED_DIR", named)
    def forbidden(*args, **kwargs):
        raise AssertionError("cached-case proof attempted network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    release_reads = []
    def release(url, **kwargs):
        repo = url.removeprefix("https://api.github.com/repos/").removesuffix("/releases/latest")
        assert repo in set(sources.values()) and kwargs == {"strict": True}
        release_reads.append(repo)
        return {"tag_name": "v99.0.0", "published_at": "2026-11-20T00:00:00Z",
                "html_url": f"https://github.com/{repo}/releases/tag/v99.0.0"}
    monkeypatch.setattr(watcher, "fetch_json", release)
    rows = mixedRows()
    rows[0].update(number=cached["number"], title=cached["title"], body=body, labels=cached["labels"])
    before_hash = hashlib.sha256(rows[0]["body"].encode()).hexdigest()
    runner = ConnectionRunner(rows, open_count=226)
    actual_run = subprocess.run
    reads = []
    def transport(args, **kwargs):
        if args[:2] == ["git", "show"]:
            # The sole local historical authority lookup, not any live source read.
            assert args == ["git", "show", "9b4d9b98043140188f00b14d0ac8fa6bc02491b7:registry/named/ruvnet/agentdb.md"]
            reads.append("pinned-local-history")
            return actual_run(args, **kwargs)
        assert args[:2] == ["gh", "api"], "unexpected subprocess outside read-only fixture transport"
        query = next((a for a in args if a.startswith("query=")), "")
        assert "mutation" not in query.lower()
        method = next((f for f in ("--method", "-X") if f in args), None)
        assert method is None or args[args.index(method) + 1] == "GET"
        return runner(args, **kwargs)
    monkeypatch.setattr(subprocess, "run", transport)
    monkeypatch.setattr(watcher, "LiveGh", LiveGh)
    report_path = tmp_path / "report.json"
    code = watcher.main(["--child-mode", "batch", "--dry-run", "--report", str(report_path)])
    report = json.loads(report_path.read_text())
    assert code == 0 and report["unknownEvidence"] == []
    assert report["dryRun"] is True and report["writeReadiness"] is False
    assert (report["issuesCreated"], report["issuesUpdated"]) == (2, 1)
    assert len(report["observedFindings"]) == len(report["suites"]) == 4
    plans = {p["repository"]: p for p in report["repositories"]}
    assert set(plans) == {"ruvnet/ruflo", "ruvnet/agentdb", "garrytan/gstack"}
    ruflo = plans["ruvnet/ruflo"]
    assert ruflo["umbrella"] == 1833 and ruflo["outcome"] == "held"
    assert [f["skillId"] for f in ruflo["payload"]["findings"]] == ["ruvnet/dual-mode", "ruvnet/ruflo"]
    hold = report["knownLegacyHolds"][0]
    assert hold["legacyNamedId"] == "ruvnet/agentdb" and hold["bodySha256"] == raw_sha
    assert hold["bodyHashScheme"] == "raw_api_utf8" and not hold["writeReadiness"]
    assert hold["currentReleaseRepository"] == "ruvnet/agentdb"
    assert reads == ["pinned-local-history", "pinned-local-history"]  # old repo AND the distinct current named scope
    assert len(release_reads) == 4 and runner.writes == []
    # Red OLD contract: the retained single-ID planner still refuses this exact
    # cached payload. Green NEW normal path above retains every named finding
    # while reporting a visible, immutable historical migration hold.
    from upstream_fakes import FakeGh
    from scripts.upstream_watcher.batch import run_batch
    old_gh = FakeGh([{**cached, "state": "open"}])
    old_report, old_code = run_batch(report["observedFindings"], old_gh, apply=False,
                                   index_loader=lambda: {"byId": {}, "bySlug": {}})
    assert old_code == 3 and old_report["unknownEvidence"] and old_gh.writes == []
    assert "payload identity conflicts" in old_report["unknownEvidence"][0]["detail"]
    assert hashlib.sha256(rows[0]["body"].encode()).hexdigest() == before_hash
    assert hashlib.sha256(cache_path.read_bytes()).hexdigest() == cache_digest
