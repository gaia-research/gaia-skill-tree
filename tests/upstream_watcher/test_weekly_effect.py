"""Offline durable fake-effect recovery proofs (P2 Slice 4B).

Uses only closed-world concrete ``FakeIssueService`` + ``FakeEffectTransport``
hydrated from synthetic fixture data. ``LiveGh``, duck-typed/wrapped ``LiveGh``,
subclasses, and network access are trapped and refused with zero calls.
No live forge mutations, no writer activation, and no ``named-v3`` journal settlement.
"""

from __future__ import annotations

import copy
import dataclasses
import socket
from pathlib import Path
from typing import Any

import pytest

from scripts.upstream_watcher import (
    envelope as wire,
    repository_batch as rb,
    weekly_binding as wb,
    weekly_effect as we,
    weekly_journal as wj,
    weekly_reducer as wr,
)
from scripts.upstream_watcher.live import LiveGh


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("offline weekly_effect test attempted network access")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbidden)


def _authority() -> dict[str, dict[str, Any]]:
    def _suite(sid: str, repo: str, root: str, base_slug: str) -> dict[str, dict[str, Any]]:
        owner = sid.split("/", 1)[0]
        comp = f"{owner}/{base_slug}"
        return {
            sid: {
                "id": sid,
                "suiteRef": sid,
                "upstreamComponentRoot": root,
                "suiteComponents": [comp],
                "links": {"github": f"https://github.com/{repo}"},
                "upstream": {"repo": repo, "version": "v1.0.0"},
            },
            comp: {
                "id": comp,
                "suiteRef": sid,
                "links": {"github": f"https://github.com/{repo}/blob/main/{root}/{base_slug}/SKILL.md"},
            },
        }

    auth: dict[str, dict[str, Any]] = {}
    auth.update(_suite("owner/a", "owner/repo", "skills-a", "a-base"))
    auth.update(_suite("owner/b", "owner/repo", "skills-b", "b-base"))
    auth.update(_suite("owner/c", "owner/repo", "skills-c", "c-base"))
    auth.update(_suite("other/good", "other/good", "skills", "good-base"))
    return auth


def _empty_index() -> dict[str, dict[str, Any]]:
    return {"byId": {}, "bySlug": {}}


def _raw_finding(
    named_id: str = "owner/a",
    *,
    repo: str = "owner/repo",
    version: str = "v1.1.0",
    adds: tuple[str, ...] = ("alpha",),
    removes: tuple[str, ...] = (),
    component_root: str = "skills-a",
    released_at: str = "2026-11-16T08:00:00Z",
) -> dict[str, Any]:
    return {
        "finding_type": "update",
        "skillId": named_id,
        "currentVersion": "v1.0.0",
        "newVersion": version,
        "sourceUrl": f"https://github.com/{repo}/releases/tag/{version}",
        "releasedAt": released_at,
        "mode": "components",
        "upstreamComponentRoot": component_root,
        "componentAdds": list(adds),
        "componentRemoves": list(removes),
        "linkLiveness": [],
        "nameDrift": [],
    }


def _envelope_issue(
    raw_findings: list[dict[str, Any]],
    authority: dict[str, dict[str, Any]],
    *,
    number: int = 10,
    state: str = "open",
    updated_at: str = "2026-11-15T12:00:00Z",
    labels: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    report, code = rb.run_repository_batch(
        raw_findings,
        we.FakeIssueService(),
        apply=False,
        authority=authority,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
        plan_only=True,
    )
    assert code == 0
    env_payload = report["repositories"][0]["payload"]
    return {
        "number": number,
        "state": state,
        "title": wire.title(env_payload),
        "body": wire.render(env_payload),
        "labels": list(labels) if labels is not None else ["upstream:release", "needs-triage"],
        "updated_at": updated_at,
    }, env_payload


def _commit_and_bind(
    journal_path: Path,
    *,
    poll_id: str,
    observed_at: str,
    raw_findings: list[dict[str, Any]],
    service: we.FakeIssueService,
    authority: dict[str, dict[str, Any]],
    expected_pin: wj.JournalPin | None = None,
    allow_bootstrap: bool = False,
    initialized: bool = False,
) -> tuple[wj.JournalCommitResult, wr.PollInput, wb.RepositoryBinding]:
    report, code = rb.run_repository_batch(
        raw_findings,
        service,
        apply=False,
        authority=authority,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
        plan_only=True,
    )
    assert code == 0, f"planner failed unexpectedly: {report.get('unknownEvidence')}"
    poll = wr.poll_input_from_batch_report(poll_id, observed_at, report, complete=True)
    commit = wj.commit_poll(
        journal_path,
        poll,
        authority,
        expected_pin=expected_pin,
        allow_bootstrap=allow_bootstrap,
        initialized=initialized,
    )
    assert commit.persisted is True
    bound = wb.bind_weekly_plans(
        commit,
        poll,
        service,
        authority,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
    )
    assert bound.status == wb.RUN_STATUS_BOUND and len(bound.candidate_intents) == 1
    return commit, poll, bound.candidate_intents[0]


# 1. Closed-world boundary: LiveGh, duck-typed/wrapped LiveGh, and subclasses refused with zero calls
def test_live_gh_wrapped_duck_typed_forge_and_subclasses_refused_with_zero_calls(tmp_path: Path) -> None:
    auth = _authority()
    live_calls: list[list[str]] = []
    wrapper_calls: list[str] = []

    def _trap_runner(args: list[str], **kwargs: Any) -> Any:
        live_calls.append(list(args))
        raise AssertionError("LiveGh runner must never be invoked")

    live_gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=_trap_runner)

    class WrappedLiveGh:
        """Duck-typed wrapper around LiveGh exposing every fake store/transport method name."""

        repo = "gaia-research/gaia-skill-tree"

        def __init__(self, inner: LiveGh) -> None:
            self._inner = inner

        def _trap(self, name: str) -> Any:
            wrapper_calls.append(name)
            raise AssertionError(f"wrapped LiveGh method must never be invoked: {name}")

        def list_issues(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("list_issues")

        def get_issue(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("get_issue")

        def create_issue(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("create_issue")

        def edit_issue(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("edit_issue")

        def edit_labels(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("edit_labels")

        def list_comments(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("list_comments")

        def child_state(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("child_state")

        def fake_create_umbrella(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("fake_create_umbrella")

        def fake_update_umbrella(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("fake_update_umbrella")

        def lookup_causal_witness(self, *args: Any, **kwargs: Any) -> Any:
            return self._trap("lookup_causal_witness")

    wrapped = WrappedLiveGh(live_gh)

    with pytest.raises(TypeError, match="exact FakeIssueService"):
        we.FakeEffectTransport(live_gh)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact FakeIssueService"):
        we.FakeEffectTransport(wrapped)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="cannot be subclassed"):
        type("SubService", (we.FakeIssueService,), {})
    with pytest.raises(TypeError, match="cannot be subclassed"):
        type("SubTransport", (we.FakeEffectTransport,), {})

    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "effect-intent.json"
    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-live-trap",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    for bad_transport in (live_gh, wrapped, service):
        res_exec = we.execute_fake_effect(
            repo_bind,
            journal_path,
            ckpt_path,
            bad_transport,  # type: ignore[arg-type]
            auth,
            policy={},
            historical_loader=lambda _: {},
        )
        assert res_exec.status == we.EFFECT_STATUS_REFUSED
        assert res_exec.reason == "transport-must-be-fake-effect-transport"
        assert res_exec.write_authorized is False and res_exec.write_readiness is False and res_exec.journal_settled is False

        res_rec = we.recover_fake_effect(
            ckpt_path,
            bad_transport,  # type: ignore[arg-type]
            auth,
            policy={},
            historical_loader=lambda _: {},
        )
        assert res_rec.status == we.EFFECT_STATUS_REFUSED
        assert res_rec.reason == "transport-must-be-fake-effect-transport"

    assert not ckpt_path.exists()
    assert live_calls == [] and wrapper_calls == []


# 2. Fake create succeeds, then confirm checkpoint replace fails -> fresh coordinator recovers without reissue
def test_fake_create_checkpoint_replace_crash_fresh_coordinator_recovers_without_reissue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "create-intent.json"

    commit, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-create-crash",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a", version="v2.0.0", adds=("alpha",))],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )
    journal_bytes_before = journal_path.read_bytes()

    real_atomic_write = we._atomic_write_bytes
    failed_confirm = {"done": False}

    def _fail_on_confirmed(target: Path, encoded_bytes: bytes) -> None:
        if not failed_confirm["done"] and b'"state": "confirmed"' in encoded_bytes:
            failed_confirm["done"] = True
            raise OSError("simulated crash during confirmation checkpoint replace")
        real_atomic_write(target, encoded_bytes)

    monkeypatch.setattr(we, "_atomic_write_bytes", _fail_on_confirmed)

    coord_1 = we.FakeEffectTransport(service)
    with pytest.raises(OSError, match="simulated crash"):
        we.execute_fake_effect(
            repo_bind,
            journal_path,
            ckpt_path,
            coord_1,
            auth,
            policy={},
            historical_loader=lambda _: {},
        )

    assert failed_confirm["done"] is True
    assert len(service.attempt_calls) == 1
    assert len(service.writes) == 1 and service.writes[0][0] == "create"
    created_num = service.writes[0][1]

    ckpt_after_crash, err = we.load_intent_checkpoint(ckpt_path)
    assert err is None and ckpt_after_crash is not None
    assert ckpt_after_crash.state == we.INTENT_STATE_ATTEMPTED
    assert ckpt_after_crash.receipt is None

    # Coordinator restart: instantiate a brand-new FakeEffectTransport against the persistent FakeIssueService.
    monkeypatch.setattr(we, "_atomic_write_bytes", real_atomic_write)
    coord_2 = we.FakeEffectTransport(service)
    assert coord_2 is not coord_1
    rec = we.recover_fake_effect(
        ckpt_path,
        coord_2,
        auth,
        binding=repo_bind,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec.status == we.EFFECT_STATUS_CONFIRMED
    assert rec.recovered is True and rec.effect_called is False
    assert rec.write_authorized is False and rec.write_readiness is False and rec.journal_settled is False
    assert rec.receipt is not None
    assert rec.receipt.action == "create"
    assert rec.receipt.umbrella == created_num
    assert rec.receipt.repository == "owner/repo"
    assert rec.receipt.envelope_sha256 == repo_bind.envelope_sha256
    assert rec.receipt.journal_pin == commit.handle.pin
    assert dict(rec.receipt.selected_finding_digests) == {"owner/a": repo_bind.selected_members[0].finding_sha256}
    assert dict(rec.receipt.preserved_sibling_digests) == {}
    assert len(service.attempt_calls) == 1 and len(service.writes) == 1

    # Replaying execute_fake_effect on yet another fresh coordinator reconciles idempotently.
    coord_3 = we.FakeEffectTransport(service)
    replay = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        coord_3,
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert replay.status == we.EFFECT_STATUS_CONFIRMED
    assert replay.recovered is False and replay.effect_called is False
    assert replay.receipt == rec.receipt
    assert len(service.attempt_calls) == 1 and len(service.writes) == 1
    assert journal_path.read_bytes() == journal_bytes_before


# 3. Fake update succeeds (preserving sibling + resetting upstream:approved), confirm replace fails -> fresh coordinator recovers
def test_fake_update_checkpoint_replace_crash_fresh_coordinator_recovers_and_preserves_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = _authority()
    existing_c = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    existing_issue, existing_env = _envelope_issue(
        [existing_c],
        auth,
        number=10,
        labels=["upstream:release", "needs-triage", "upstream:approved"],
    )
    existing_c_finding = existing_env["findings"][0]
    existing_c_sha = existing_c_finding["payloadSha256"]

    service = we.FakeIssueService([existing_issue])
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "update-intent.json"

    commit, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-update-crash",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a", version="v2.0.0", adds=("alpha",))],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )
    assert repo_bind.target is not None and repo_bind.target.action == "update" and repo_bind.target.umbrella == 10
    journal_bytes_before = journal_path.read_bytes()

    real_atomic_write = we._atomic_write_bytes
    failed_confirm = {"done": False}

    def _fail_on_confirmed(target: Path, encoded_bytes: bytes) -> None:
        if not failed_confirm["done"] and b'"state": "confirmed"' in encoded_bytes:
            failed_confirm["done"] = True
            raise OSError("simulated crash during update confirm replace")
        real_atomic_write(target, encoded_bytes)

    monkeypatch.setattr(we, "_atomic_write_bytes", _fail_on_confirmed)

    with pytest.raises(OSError, match="simulated crash"):
        we.execute_fake_effect(
            repo_bind,
            journal_path,
            ckpt_path,
            we.FakeEffectTransport(service),
            auth,
            policy={},
            historical_loader=lambda _: {},
        )

    assert len(service.attempt_calls) == 1
    assert [w[0] for w in service.writes] == ["labels", "edit"]
    assert service.issue_numbers == frozenset({10})
    updated_issue = service.snapshot_issue(10)
    updated_labels = {lbl["name"] for lbl in updated_issue["labels"]}
    assert "upstream:approved" not in updated_labels
    assert "upstream:needs-info" in updated_labels

    # Restart via a brand-new coordinator calling execute_fake_effect -> recovers without reissuing.
    monkeypatch.setattr(we, "_atomic_write_bytes", real_atomic_write)
    rec = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec.status == we.EFFECT_STATUS_CONFIRMED
    assert rec.recovered is True and rec.effect_called is False
    assert rec.receipt is not None
    assert rec.receipt.action == "update" and rec.receipt.umbrella == 10
    assert dict(rec.receipt.preserved_sibling_digests) == {"owner/c": existing_c_sha}
    assert rec.receipt.journal_pin == commit.handle.pin
    assert len(service.attempt_calls) == 1
    assert [w[0] for w in service.writes] == ["labels", "edit"]

    parsed_live = wire.read(updated_issue["body"], auth, title_text=updated_issue["title"])
    by_id = {f["skillId"]: f for f in parsed_live["findings"]}
    assert by_id["owner/c"] == existing_c_finding
    assert journal_path.read_bytes() == journal_bytes_before


# 4. Attempted-before-effect crash: never reissues, conservatively holds
def test_attempted_before_effect_crash_holds_and_never_reissues(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "pre-effect-crash.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-pre-crash",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_before_effect_once = True
    res1 = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res1.status == we.EFFECT_STATUS_HELD
    assert res1.reason == "effect-callback-ambiguous"
    assert res1.effect_called is True
    assert service.writes == () and len(service.attempt_calls) == 1

    # Fresh coordinator recovery sees absence + no witness -> holds, ZERO reissue.
    res2 = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        binding=repo_bind,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res2.status == we.EFFECT_STATUS_HELD
    assert res2.reason == "attempted-without-causal-evidence"
    assert res2.effect_called is False
    assert service.writes == () and len(service.attempt_calls) == 1

    # Re-calling execute_fake_effect also NEVER reissues.
    res3 = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res3.status == we.EFFECT_STATUS_HELD
    assert res3.effect_called is False
    assert service.writes == () and len(service.attempt_calls) == 1


# 5. Callback ambiguous failure AFTER fake write -> fresh coordinator recovers; if witness lost -> holds, never replays
def test_callback_ambiguous_failure_recovers_with_witness_and_holds_if_witness_lost(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "ambiguous-after.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-ambig-after",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_after_effect_once = True
    res1 = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res1.status == we.EFFECT_STATUS_HELD
    assert res1.reason == "effect-callback-ambiguous"
    assert len(service.writes) == 1 and len(service.attempt_calls) == 1

    # Fresh coordinator recovers via fresh complete readback + service-owned witness.
    rec = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec.status == we.EFFECT_STATUS_CONFIRMED
    assert rec.recovered is True and rec.effect_called is False
    assert rec.receipt is not None and rec.receipt.umbrella == service.writes[0][1]
    assert len(service.writes) == 1 and len(service.attempt_calls) == 1

    # Separate run: fake write succeeded, then process-local witness evidence disappears -> MUST hold, never replay!
    service_lost = we.FakeIssueService()
    journal_lost = tmp_path / "named-v3-lost.json"
    ckpt_lost = tmp_path / "witness-lost.json"
    _, _, bind_lost = _commit_and_bind(
        journal_lost,
        poll_id="poll-witness-lost",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service_lost,
        authority=auth,
        allow_bootstrap=True,
    )
    service_lost.fail_after_effect_once = True
    we.execute_fake_effect(
        bind_lost,
        journal_lost,
        ckpt_lost,
        we.FakeEffectTransport(service_lost),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    service_lost.clear_witnesses()
    rec_lost = we.recover_fake_effect(
        ckpt_lost,
        we.FakeEffectTransport(service_lost),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec_lost.status == we.EFFECT_STATUS_HELD
    assert rec_lost.reason == "unattributed-matching-create"
    assert rec_lost.receipt is None
    assert len(service_lost.attempt_calls) == 1 and len(service_lost.writes) == 1


def test_unavailable_fake_service_holds_recovery_without_reissuing(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "service-unavailable.json"
    _, _, binding = _commit_and_bind(
        journal_path,
        poll_id="poll-service-unavailable",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_before_effect_once = True
    transport = we.FakeEffectTransport(service)
    first = we.execute_fake_effect(
        binding,
        journal_path,
        ckpt_path,
        transport,
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert first.status == we.EFFECT_STATUS_HELD
    assert len(service.attempt_calls) == 1

    # Simulate loss of the independent fake service. Recovery must be an explicit
    # hold, not an exception or a second effect attempt.
    transport._service = None  # type: ignore[assignment]
    recovered = we.recover_fake_effect(ckpt_path, transport, auth, policy={}, historical_loader=lambda _: {})
    assert recovered.status == we.EFFECT_STATUS_HELD
    assert recovered.reason == "fake-service-unavailable"
    assert len(service.attempt_calls) == 1 and service.writes == ()


# 6. Unrelated external actor creates identical canonical payload -> NOT causally confirmed
def test_unrelated_external_identical_create_is_not_causally_confirmed(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "unattributed-create.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-ext-create",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_before_effect_once = True
    res1 = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res1.status == we.EFFECT_STATUS_HELD

    assert repo_bind.target is not None and repo_bind.envelope_body is not None
    service.external_create_issue(repo_bind.target.title, ["upstream:release", "needs-triage"], repo_bind.envelope_body)

    rec = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec.status == we.EFFECT_STATUS_HELD
    assert rec.reason == "unattributed-matching-create"
    assert rec.receipt is None
    assert len(service.attempt_calls) == 1


# 7. Duplicate open umbrella after create -> NOT confirmed
def test_duplicate_open_umbrella_after_create_is_held(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "dup-create.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-dup-create",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_after_effect_once = True
    res1 = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res1.status == we.EFFECT_STATUS_HELD

    assert repo_bind.target is not None and repo_bind.envelope_body is not None
    service.external_create_issue(repo_bind.target.title, ["upstream:release", "needs-triage"], repo_bind.envelope_body)

    rec = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec.status == we.EFFECT_STATUS_HELD
    assert rec.reason == "duplicate-open-umbrellas-after-create"
    assert rec.receipt is None


# 8. Missing/incomplete or opaque historical inventory during recovery -> held, zero raw body leakage
def test_incomplete_and_contradictory_fresh_inventory_holds_recovery(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "incomplete-inv.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-incomplete-inv",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_after_effect_once = True
    we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )

    service.fail_list = True
    rec_fail = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec_fail.status == we.EFFECT_STATUS_HELD
    assert rec_fail.reason == "inventory-readback-failed"
    assert rec_fail.receipt is None

    service.fail_list = False
    service.seed_issue(
        {
            "number": 999,
            "state": "closed",
            "title": "[upstream] owner/repo → v0.9.0",
            "body": "SECRET_RAW_HISTORICAL_BODY_DO_NOT_LEAK",
            "labels": ["upstream:release"],
            "updated_at": "2026-11-18T12:00:00Z",
        }
    )
    rec_opaque = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec_opaque.status == we.EFFECT_STATUS_HELD
    assert rec_opaque.reason is not None
    assert "opaque-release-history" in rec_opaque.reason
    assert "SECRET_RAW_HISTORICAL_BODY_DO_NOT_LEAK" not in rec_opaque.reason

    service.remove_issue(999)
    rec_ok = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec_ok.status == we.EFFECT_STATUS_CONFIRMED
    assert rec_ok.recovered is True and len(service.attempt_calls) == 1


# 9. Journal changes between intent and confirm -> refuses confirmation rather than resurrecting stale scope
def test_journal_advance_between_intent_and_confirm_refuses_confirmation(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "stale-journal.json"

    commit1, _, repo_bind1 = _commit_and_bind(
        journal_path,
        poll_id="poll-j1",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a", version="v1.1.0", adds=("alpha",))],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    service.fail_after_effect_once = True
    res1 = we.execute_fake_effect(
        repo_bind1,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res1.status == we.EFFECT_STATUS_HELD

    report2, code2 = rb.run_repository_batch(
        [_raw_finding("owner/a", version="v1.2.0", adds=("alpha", "delta"))],
        we.FakeIssueService(),
        apply=False,
        authority=auth,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
        plan_only=True,
    )
    assert code2 == 0
    poll2 = wr.poll_input_from_batch_report("poll-j2", "2026-11-24T10:00:00Z", report2, complete=True)
    commit2 = wj.commit_poll(journal_path, poll2, auth, expected_pin=commit1.handle.pin, initialized=True)
    assert commit2.persisted is True

    rec = we.recover_fake_effect(
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec.status == we.EFFECT_STATUS_REFUSED
    assert rec.reason == "journal-changed-since-intent"
    assert rec.receipt is None


def _advance_journal_once(
    journal_path: Path,
    auth: dict[str, dict[str, Any]],
    expected_pin: wj.JournalPin,
) -> wj.JournalCommitResult:
    report, code = rb.run_repository_batch(
        [_raw_finding("owner/a", version="v1.2.0", adds=("alpha", "delta"))],
        we.FakeIssueService(),
        apply=False,
        authority=auth,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
        plan_only=True,
    )
    assert code == 0
    poll = wr.poll_input_from_batch_report(
        "poll-race-advance", "2026-11-24T10:00:00Z", report, complete=True
    )
    commit = wj.commit_poll(journal_path, poll, auth, expected_pin=expected_pin, initialized=True)
    assert commit.persisted is True
    return commit


def test_revision_advance_during_post_effect_readback_keeps_attempted_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "readback-race.json"
    commit1, _, binding = _commit_and_bind(
        journal_path,
        poll_id="poll-race-readback",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    real_readback = we._read_and_validate_complete_inventory
    calls = {"count": 0}

    def _advance_after_post_readback(*args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        result = real_readback(*args, **kwargs)
        if calls["count"] == 2:
            _advance_journal_once(journal_path, auth, commit1.handle.pin)
        return result

    monkeypatch.setattr(we, "_read_and_validate_complete_inventory", _advance_after_post_readback)
    result = we.execute_fake_effect(
        binding, journal_path, ckpt_path, we.FakeEffectTransport(service), auth,
        policy={}, historical_loader=lambda _: {},
    )

    assert calls["count"] == 2
    assert result.status == we.EFFECT_STATUS_REFUSED
    assert result.reason == "journal-changed-since-intent"
    assert len(service.attempt_calls) == 1 and len(service.writes) == 1
    checkpoint, err = we.load_intent_checkpoint(ckpt_path)
    assert err is None and checkpoint is not None
    assert checkpoint.state == we.INTENT_STATE_ATTEMPTED and checkpoint.receipt is None
    assert wj.load_journal(journal_path, auth, initialized=True).state.revision == 2


def test_revision_advance_during_preflight_refuses_before_fake_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "preflight-race.json"
    commit1, _, binding = _commit_and_bind(
        journal_path,
        poll_id="poll-race-preflight",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )
    real_preflight = we._preflight_fake_effect

    def _advance_after_preflight(*args: Any, **kwargs: Any) -> Any:
        result = real_preflight(*args, **kwargs)
        _advance_journal_once(journal_path, auth, commit1.handle.pin)
        return result

    monkeypatch.setattr(we, "_preflight_fake_effect", _advance_after_preflight)
    result = we.execute_fake_effect(
        binding, journal_path, ckpt_path, we.FakeEffectTransport(service), auth,
        policy={}, historical_loader=lambda _: {},
    )

    assert result.status == we.EFFECT_STATUS_REFUSED
    assert result.reason == "journal-changed-since-intent"
    assert len(service.attempt_calls) == 0 and len(service.writes) == 0
    assert not ckpt_path.exists()
    assert wj.load_journal(journal_path, auth, initialized=True).state.revision == 2


# 10. Wrong pre-state snapshot, wrong post payload, and mismatched named/target/pin
def test_wrong_pre_state_wrong_post_payload_and_mismatched_target_or_pin(tmp_path: Path) -> None:
    auth = _authority()
    existing_c = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    existing_issue, _ = _envelope_issue([existing_c], auth, number=10)
    service = we.FakeIssueService([existing_issue])
    journal_path = tmp_path / "named-v3.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-prestate",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a", version="v2.0.0", adds=("alpha",))],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    # A) Wrong pre-state at preflight.
    service.external_edit_issue(10, existing_issue["title"], existing_issue["body"] + "\n")
    ckpt_pre = tmp_path / "wrong-pre.json"
    res_pre = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_pre,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res_pre.status == we.EFFECT_STATUS_REFUSED
    assert res_pre.reason == "preflight-target-snapshot-mismatch"
    assert not ckpt_pre.exists() and len(service.attempt_calls) == 0

    # B) Wrong post payload after update (same title, untouched sibling owner/c dropped by external edit).
    service2 = we.FakeIssueService([existing_issue])
    journal_path2 = tmp_path / "named-v3-2.json"
    ckpt_post = tmp_path / "wrong-post.json"
    _, _, repo_bind2 = _commit_and_bind(
        journal_path2,
        poll_id="poll-poststate",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a", version="v1.1.0", adds=("alpha",))],
        service=service2,
        authority=auth,
        allow_bootstrap=True,
    )
    service2.fail_after_effect_once = True
    we.execute_fake_effect(
        repo_bind2,
        journal_path2,
        ckpt_post,
        we.FakeEffectTransport(service2),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    rogue_issue, _ = _envelope_issue([_raw_finding("owner/a", version="v1.1.0", adds=("alpha",))], auth, number=10)
    service2.external_edit_issue(10, rogue_issue["title"], rogue_issue["body"])

    rec_post = we.recover_fake_effect(
        ckpt_post,
        we.FakeEffectTransport(service2),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert rec_post.status == we.EFFECT_STATUS_HELD
    assert rec_post.reason == "post-effect-body-digest-mismatch"
    assert rec_post.receipt is None

    # C) Mismatched binding / conflicting existing intent.
    other_service = we.FakeIssueService()
    other_journal = tmp_path / "other-named-v3.json"
    _, _, other_bind = _commit_and_bind(
        other_journal,
        poll_id="poll-other",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/b", version="v2.1.0", adds=("beta",), component_root="skills-b")],
        service=other_service,
        authority=auth,
        allow_bootstrap=True,
    )
    res_conflict = we.execute_fake_effect(
        other_bind,
        other_journal,
        ckpt_post,
        we.FakeEffectTransport(other_service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res_conflict.status == we.EFFECT_STATUS_REFUSED
    assert res_conflict.reason == "conflicting-existing-intent"
    assert len(other_service.attempt_calls) == 0


# 11. Missing-after-init, corrupt checkpoint, checkpoint-journal collision, and records-mode decline
def test_missing_after_init_corrupt_checkpoint_collision_and_records_decline(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-guards",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )

    res_missing = we.execute_fake_effect(
        repo_bind,
        journal_path,
        tmp_path / "missing.json",
        we.FakeEffectTransport(service),
        auth,
        initialized=True,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res_missing.status == we.EFFECT_STATUS_REFUSED
    assert res_missing.reason == "intent-checkpoint-missing-after-init"

    res_collide = we.execute_fake_effect(
        repo_bind,
        journal_path,
        journal_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res_collide.status == we.EFFECT_STATUS_REFUSED
    assert res_collide.reason == "checkpoint-path-collides-with-journal"

    corrupt_ckpt = tmp_path / "corrupt.json"
    corrupt_ckpt.write_text('{"format": "wrong", "digest": "bad"}\n', encoding="utf-8")
    res_corrupt = we.execute_fake_effect(
        repo_bind,
        journal_path,
        corrupt_ckpt,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res_corrupt.status == we.EFFECT_STATUS_REFUSED
    assert res_corrupt.reason is not None and res_corrupt.reason.startswith("intent-checkpoint-invalid:")
    assert corrupt_ckpt.read_text(encoding="utf-8") == '{"format": "wrong", "digest": "bad"}\n'

    records_payload = copy.deepcopy(repo_bind.envelope_payload)
    assert records_payload is not None
    records_payload["candidateRecords"] = {"chunks": 1, "rows": 1, "sha256": "a" * 64}
    records_bind = dataclasses.replace(repo_bind, envelope_payload=records_payload)
    res_rec_layout = we.execute_fake_effect(
        records_bind,
        journal_path,
        tmp_path / "records.json",
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res_rec_layout.status == we.EFFECT_STATUS_REFUSED
    assert res_rec_layout.reason == "records-comment-layout-out-of-scope"
    assert service.writes == ()


# 12. Closed issues and PRs excluded; lowest eligible OPEN umbrella bound; no children created
def test_closed_and_pr_excluded_and_lowest_open_umbrella_updated(tmp_path: Path) -> None:
    auth = _authority()
    existing_c = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    closed_issue, _ = _envelope_issue([existing_c], auth, number=5, state="closed", updated_at="2026-11-18T10:00:00Z")
    pr_row = {
        "number": 7,
        "state": "open",
        "title": "[upstream] owner/repo → v1.1.0",
        "body": "PR body",
        "labels": ["upstream:release"],
        "updated_at": "2026-11-18T11:00:00Z",
        "pull_request": {"url": "https://api.github.com/repos/gaia-research/gaia-skill-tree/pulls/7"},
    }
    low_open, _ = _envelope_issue([existing_c], auth, number=12, state="open", updated_at="2026-11-18T12:00:00Z")
    high_open, _ = _envelope_issue([existing_c], auth, number=25, state="open", updated_at="2026-11-18T13:00:00Z")

    service = we.FakeIssueService([closed_issue, pr_row, high_open, low_open])
    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "lowest-open.json"

    _, _, repo_bind = _commit_and_bind(
        journal_path,
        poll_id="poll-lowest",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a", version="v2.0.0", adds=("alpha",))],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )
    assert repo_bind.target is not None and repo_bind.target.umbrella == 12

    res = we.execute_fake_effect(
        repo_bind,
        journal_path,
        ckpt_path,
        we.FakeEffectTransport(service),
        auth,
        policy={},
        historical_loader=lambda _: {},
    )
    assert res.status == we.EFFECT_STATUS_CONFIRMED
    assert res.receipt is not None and res.receipt.umbrella == 12
    assert service.writes == (("edit", 12),)
    assert service.issue_numbers == frozenset({5, 7, 12, 25})


def test_instance_method_injection_is_blocked_for_service_and_transport(tmp_path: Path) -> None:
    auth = _authority()
    service = we.FakeIssueService()
    transport = we.FakeEffectTransport(service)
    trap_calls: list[str] = []
    trap = lambda *args, **kwargs: trap_calls.append("called")
    for obj, names in (
        (service, ("_apply_fake_create", "_apply_fake_update")),
        (transport, ("fake_create_umbrella", "fake_update_umbrella")),
    ):
        for name in names:
            with pytest.raises(AttributeError):
                setattr(obj, name, trap)

    journal_path = tmp_path / "named-v3.json"
    ckpt_path = tmp_path / "no-injection.json"
    _, _, binding = _commit_and_bind(
        journal_path,
        poll_id="poll-no-instance-injection",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service,
        authority=auth,
        allow_bootstrap=True,
    )
    result = we.execute_fake_effect(
        binding, journal_path, ckpt_path, transport, auth,
        policy={}, historical_loader=lambda _: {},
    )
    assert result.status == we.EFFECT_STATUS_CONFIRMED
    assert result.effect_called is True
    assert [row[0] for row in service.writes] == ["create"]
    assert trap_calls == []


def test_copied_confirmed_checkpoint_requires_fresh_effect_and_witness(tmp_path: Path) -> None:
    auth = _authority()
    service_b = we.FakeIssueService()
    journal_path = tmp_path / "named-v3.json"
    checkpoint_b = tmp_path / "service-b.json"
    _, _, binding = _commit_and_bind(
        journal_path,
        poll_id="poll-confirmed-copy",
        observed_at="2026-11-23T10:00:00Z",
        raw_findings=[_raw_finding("owner/a")],
        service=service_b,
        authority=auth,
        allow_bootstrap=True,
    )
    confirmed = we.execute_fake_effect(
        binding, journal_path, checkpoint_b, we.FakeEffectTransport(service_b), auth,
        policy={}, historical_loader=lambda _: {},
    )
    assert confirmed.status == we.EFFECT_STATUS_CONFIRMED
    assert confirmed.receipt is not None

    # Copy an internally valid confirmation to a separate empty fake service.
    checkpoint_a = tmp_path / "service-a.json"
    checkpoint_a.write_bytes(checkpoint_b.read_bytes())
    service_a = we.FakeIssueService()
    before = checkpoint_a.read_bytes()
    rejected = we.recover_fake_effect(
        checkpoint_a, we.FakeEffectTransport(service_a), auth,
        binding=binding, policy={}, historical_loader=lambda _: {},
    )
    assert rejected.status == we.EFFECT_STATUS_HELD
    assert rejected.receipt is None
    assert service_a.writes == () and service_a.attempt_calls == ()
    assert checkpoint_a.read_bytes() == before

    # Genuine persisted confirmation remains valid against its retained service.
    fresh = we.recover_fake_effect(
        checkpoint_b, we.FakeEffectTransport(service_b), auth,
        binding=binding, policy={}, historical_loader=lambda _: {},
    )
    assert fresh.status == we.EFFECT_STATUS_CONFIRMED
    assert fresh.receipt == confirmed.receipt
    assert len(service_b.attempt_calls) == 1
    assert len(service_b.writes) == 1
