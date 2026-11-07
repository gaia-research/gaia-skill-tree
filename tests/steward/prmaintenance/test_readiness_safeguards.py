"""Routine 19 readiness safeguards: local, non-live probes only.

Nothing here talks to a real forge, proxy or clock, writes the shared ledger, or provisions anything. The TLS probes
use a disposable loopback server and a throwaway self-signed certificate created under ``tmp_path``.
"""
from __future__ import annotations

import json
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from gaia_cli.steward.prmaintenance import coordination as core, executor as ex, proofs
from . import helpers as h

ROOT = Path(__file__).resolve().parents[3]
LISTING_LIMIT = 4 * 1024 * 1024


def repoWith(tmp_path: Path, files: dict[str, bytes]) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    h.run(root, "init", "-q")
    for name, data in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    h.run(root, "add", ".")
    h.run(root, "commit", "-qm", "fixture")
    return root, h.run(root, "rev-parse", "HEAD")


# --- bounded object reads: size and deadline boundaries -------------------------------------------------------------


def test_bounded_read_accepts_exactly_the_limit_and_rejects_one_byte_more(tmp_path):
    payload = bytes(range(256)) * (LISTING_LIMIT // 256)
    assert len(payload) == LISTING_LIMIT
    root, _ = repoWith(tmp_path, {"blob": payload})
    oid = h.run(root, "rev-parse", "HEAD:blob")
    deadline = time.monotonic() + 60
    assert proofs.boundedObjectRead(root, ["cat-file", "blob", oid], LISTING_LIMIT, deadline) == payload
    assert proofs.boundedObjectRead(root, ["cat-file", "blob", oid], LISTING_LIMIT - 1, deadline) is None
    assert proofs.boundedObjectRead(root, ["cat-file", "blob", oid], 0, deadline) is None


def test_bounded_read_with_an_expired_deadline_returns_nothing(tmp_path):
    root, _ = repoWith(tmp_path, {"blob": b"small"})
    oid = h.run(root, "rev-parse", "HEAD:blob")
    assert proofs.boundedObjectRead(root, ["cat-file", "blob", oid], 1024, time.monotonic() - 1) is None


def test_bounded_read_kills_a_stalled_child_at_the_deadline(tmp_path, monkeypatch):
    spawned = []
    original = subprocess.Popen

    def stalled(command, *args, **kwargs):
        child = original([sys.executable, "-c", "import time; time.sleep(120)"], *args, **kwargs)
        spawned.append(child)
        return child

    monkeypatch.setattr(proofs.subprocess, "Popen", stalled)
    started = time.monotonic()
    assert proofs.boundedObjectRead(tmp_path, ["cat-file", "blob", "0" * 40], 1024, started + 0.5) is None
    assert time.monotonic() - started < 15
    assert len(spawned) == 1 and spawned[0].poll() is not None  # reaped, not left running


def test_export_listing_is_capped_at_exactly_four_mebibytes_and_two_minutes(tmp_path, monkeypatch):
    seen = []
    started = time.monotonic()

    def record(root, args, limit, deadline):
        seen.append((args[0], limit, deadline))
        return None

    monkeypatch.setattr(proofs, "boundedObjectRead", record)
    assert not proofs.exportBase(tmp_path, "a" * 40, ["docs"], tmp_path / "out")
    [(verb, limit, deadline)] = seen
    assert (verb, limit) == ("ls-tree", LISTING_LIMIT)
    assert 119.0 <= deadline - started <= 121.0


def test_oversized_real_listing_is_refused_before_any_blob_is_read(tmp_path, monkeypatch):
    root, _ = repoWith(tmp_path, {"seed": b"x"})
    blob = h.run(root, "rev-parse", "HEAD:seed")
    rows = "".join(f"100644 {blob} 0\td/{index:05d}-{'n' * 240}\n" for index in range(15000))
    subprocess.run(["git", "-C", str(root), "update-index", "--add", "--index-info"], input=rows.encode(),
                   check=True, capture_output=True, timeout=60)
    h.run(root, "commit", "-qm", "wide tree")
    sha = h.run(root, "rev-parse", "HEAD")
    listing = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-l", "-z", "--full-tree", sha, "--", "d"],
                             capture_output=True, check=True, timeout=60).stdout
    assert len(listing) > LISTING_LIMIT  # the fixture really crosses the boundary
    reads = []
    original = proofs.boundedObjectRead

    def watch(root_, args, limit, deadline):
        reads.append(args[0])
        return original(root_, args, limit, deadline)

    monkeypatch.setattr(proofs, "boundedObjectRead", watch)
    assert not proofs.exportBase(root, sha, ["d"], tmp_path / "out")
    assert reads == ["ls-tree"]
    assert not (tmp_path / "out").exists()


def test_content_proofs_pass_when_the_temp_root_is_a_symlink_like_macos_var(tmp_path, monkeypatch):
    import tempfile

    real = tmp_path / "real-tmp"
    real.mkdir()
    alias = tmp_path / "var-alias"
    alias.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(tempfile, "tempdir", str(alias))
    fx = h.makeRepo(tmp_path / "content")
    head = fx.head("2026-44")
    results = proofs.contentEngineProofs(fx.root, fx.base, head, "2026-44")
    assert [p.state for p in results if p.name in {"rendered-html", "index-rebuild"}] == [proofs.PASS, proofs.PASS]


# --- HTTPS transport: real TLS verification, no proxy, no redirects, bounded body -----------------------------------


class LoopbackTls:
    """One-connection-at-a-time TLS server that records the plaintext it receives after a successful handshake."""

    def __init__(self, certificate: Path, key: Path, reply: bytes):
        self.reply, self.requests, self.handshakeFailures = reply, [], 0
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(str(certificate), str(key))
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(8)
        self.listener.settimeout(0.2)
        self.port = self.listener.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except (socket.timeout, OSError):
                continue
            try:
                connection.settimeout(5)
                with self.context.wrap_socket(connection, server_side=True) as tls:
                    data = b""
                    while b"\r\n\r\n" not in data:
                        chunk = tls.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    self.requests.append(data)
                    tls.sendall(self.reply)
            except (ssl.SSLError, OSError):
                self.handshakeFailures += 1
            finally:
                connection.close()

    def close(self):
        self.stop.set()
        self.thread.join(5)
        self.listener.close()


def reply(status: str, body: bytes, extra: str = "") -> bytes:
    return (f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n{extra}"
            "Connection: close\r\n\r\n").encode() + body


@pytest.fixture()
def certificate(tmp_path):
    cert, key = tmp_path / "loopback.pem", tmp_path / "loopback.key"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes",
                    "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=127.0.0.1",
                    "-addext", "subjectAltName=IP:127.0.0.1"], check=True, capture_output=True, timeout=60)
    return cert, key


def trust(certificate) -> ssl.SSLContext:
    """A trusted application seam: an explicit CA context. The environment cannot override trust (see the review tests)."""
    return ssl.create_default_context(cafile=str(certificate[0]))


def serve(certificate, body: bytes = b"{}", status: str = "200 OK", extra: str = "") -> LoopbackTls:
    server = LoopbackTls(*certificate, reply(status, body, extra))
    return server


def test_untrusted_certificate_is_rejected_before_any_request_or_credential_is_sent(certificate, monkeypatch):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    server = serve(certificate)
    try:
        transport = ex.HttpsTransport(f"https://127.0.0.1:{server.port}", "synthetic-credential-never-sent")
        with pytest.raises(core.CoordinationError, match="HTTPS invocation failed") as failure:
            transport.request("PUT", "/repos/example/pulls/1/merge", {"sha": "a" * 40})
        assert "synthetic-credential-never-sent" not in str(failure.value)
    finally:
        server.close()
    assert server.requests == []  # the handshake never completed, so no HTTP bytes (or Authorization) left the client


def test_trusted_certificate_sends_one_bearer_request_and_ignores_proxy_environment(certificate, monkeypatch):
    proxy = socket.socket()
    proxy.bind(("127.0.0.1", 0))
    proxy.listen(1)
    proxy.settimeout(0.5)
    for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy"):
        monkeypatch.setenv(name, f"http://127.0.0.1:{proxy.getsockname()[1]}")
    monkeypatch.setenv("NO_PROXY", "")
    server = serve(certificate, b'{"merged": true}')
    try:
        reply_ = ex.HttpsTransport(f"https://127.0.0.1:{server.port}", "synthetic-credential", context=trust(certificate)).request(
            "PUT", "/repos/example/pulls/1/merge", {"sha": "a" * 40})
        with pytest.raises((socket.timeout, TimeoutError)):
            proxy.accept()  # nothing ever connected to the proxy
    finally:
        server.close()
        proxy.close()
    assert reply_.status == 200 and reply_.body == {"merged": True}
    assert len(server.requests) == 1
    head = server.requests[0].decode("latin-1")
    assert head.startswith("PUT /repos/example/pulls/1/merge HTTP/1.1")
    assert "authorization: bearer synthetic-credential" in head.lower()
    assert "synthetic-credential" not in repr(reply_)


def test_redirect_is_returned_not_followed_and_hostname_mismatch_is_rejected(certificate, monkeypatch):
    server = serve(certificate, b"{}", "302 Found", "Location: https://127.0.0.1:1/elsewhere\r\n")
    try:
        redirected = ex.HttpsTransport(f"https://127.0.0.1:{server.port}", "synthetic", context=trust(certificate)).request("GET", "/x")
        assert redirected.status == 302 and len(server.requests) == 1
        # The certificate names the IP only: the same listener under the name "localhost" must fail verification.
        with pytest.raises(core.CoordinationError, match="HTTPS invocation failed"):
            ex.HttpsTransport(f"https://localhost:{server.port}", "synthetic", context=trust(certificate)).request("GET", "/x")
    finally:
        server.close()
    assert len(server.requests) == 1


def test_response_body_over_two_mebibytes_is_refused(certificate, monkeypatch):
    limit = 2 * 1024 * 1024
    exact = json.dumps({"pad": "x" * (limit - 11)}).encode()
    assert len(exact) == limit
    server = serve(certificate, exact)
    try:
        assert ex.HttpsTransport(f"https://127.0.0.1:{server.port}", "synthetic", context=trust(certificate)).request("GET", "/x").status == 200
    finally:
        server.close()
    server = serve(certificate, exact + b" ")
    try:
        with pytest.raises(core.CoordinationError, match="HTTPS invocation failed"):
            ex.HttpsTransport(f"https://127.0.0.1:{server.port}", "synthetic", context=trust(certificate)).request("GET", "/x")
    finally:
        server.close()


# --- no automation can reach the critical-write verbs ---------------------------------------------------------------


def test_no_workflow_or_script_invokes_the_critical_write_verbs_and_full_workflow_stays_manual():
    import yaml

    workflow = yaml.safe_load((ROOT / ".github/workflows/steward-full.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"workflow_dispatch"}, "steward-full must stay manual-only until reauthorized"
    verbs = re.compile(r"steward_pr(?:\.py)?[\"' ]+(?:gate-merge|gate-close|execute|recover|abort|finalize)|steward pr (?:execute|gate-)")
    workflows = ROOT / ".github/workflows"
    scanned = [*sorted(workflows.glob("*.y*ml")), *sorted(workflows.glob("*.md")),
               *sorted(path for path in (ROOT / "scripts").glob("*.py") if path.name != "steward_pr.py")]
    offenders = [str(path.relative_to(ROOT)) for path in scanned
                 if verbs.search(path.read_text(encoding="utf-8", errors="replace"))]
    assert offenders == []
