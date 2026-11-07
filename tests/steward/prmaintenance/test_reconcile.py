"""Reconciliation builds a tracked replacement; it never rewrites the producer's branch and never invents a payload."""

from __future__ import annotations

import pytest

from gaia_cli.steward.prmaintenance import proofs, reconcile
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor  # noqa: F401

from tests.steward.prmaintenance import helpers as h


def test_a_stale_stamped_head_with_a_dropped_index_row_is_rebuilt_into_a_replacement_that_passes_every_proof(tmp_path):
    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44", version="8.26.10", dropIndexRow="2026-43")
    assert proofs.stampProof(fx.root, fx.base, original, ["docs/reports/2026-44/index.html"]).state == "fail"
    made = reconcile.buildReplacement(fx.root, h.REPO, 2157, original, "2026-44", fx.base, tmp_path / "wt")
    assert made.branch == "docs/steward-pr-2157-2026-44" and made.original == 2157
    assert set(made.files) == {"docs/reports/2026-44/index.html", "docs/reports/index.html", "docs/api/v1/reports/2026-44.json",
                               "docs/api/v1/reports/index.json"}
    for proof in [proofs.reportJsonProof(fx.root, made.commit, "2026-44"), proofs.stampProof(fx.root, fx.base, made.commit, list(made.files))] \
            + proofs.contentEngineProofs(fx.root, fx.base, made.commit, "2026-44"):
        assert proof.state == "pass", proof
    # the payload is the producer's, byte for byte
    assert proofs.blob(fx.root, made.commit, "docs/api/v1/reports/2026-44.json") == proofs.blob(fx.root, original, "docs/api/v1/reports/2026-44.json")
    # the original is untouched, and the replacement links back to it
    assert proofs.hasCommit(fx.root, original)
    assert f"gaia-steward:replaces repo={h.REPO} pr=2157 head={original[:12]}" in made.body
    assert "%s" not in made.body and "docs/reports/2026-44/index.html" in made.body  # no unformatted placeholder in the PR text
    message = h.run(fx.root, "log", "-1", "--format=%B", made.commit)
    assert "Replaces #2157" in message and "Co-Authored-By: github-actions[bot]" in message


def test_the_replacement_preserves_history_when_a_newer_report_already_exists(tmp_path):
    fx = h.makeRepo(tmp_path / "w", labels=("2026-42", "2026-44"))
    original = fx.head("2026-43", dropIndexRow="2026-44", version="8.0.0")
    made = reconcile.buildReplacement(fx.root, h.REPO, 2200, original, "2026-43", fx.base, tmp_path / "wt")
    index = proofs.blob(fx.root, made.commit, "docs/api/v1/reports/index.json").decode()
    assert all(label in index for label in ("2026-42", "2026-43", "2026-44"))


def test_it_refuses_when_the_producers_objects_or_the_destination_are_missing_or_the_label_is_malformed(tmp_path):
    fx = h.makeRepo(tmp_path / "w")
    with pytest.raises(reconcile.ReconcileError, match="not local"):
        reconcile.buildReplacement(fx.root, h.REPO, 1, "d" * 40, "2026-44", fx.base, tmp_path / "wt1")
    original = fx.head("2026-44")
    with pytest.raises(reconcile.ReconcileError, match="destination tip is not local"):
        reconcile.buildReplacement(fx.root, h.REPO, 1, original, "2026-44", "e" * 40, tmp_path / "wt2")
    with pytest.raises(reconcile.ReconcileError, match="ISO week"):
        reconcile.buildReplacement(fx.root, h.REPO, 1, original, "../x", fx.base, tmp_path / "wt3")


def test_it_never_reuses_a_worktree_and_cleans_up_a_failed_build(tmp_path):
    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44")
    (tmp_path / "wt").mkdir()
    with pytest.raises(reconcile.ReconcileError, match="already exists"):
        reconcile.buildReplacement(fx.root, h.REPO, 1, original, "2026-44", fx.base, tmp_path / "wt")
    # a payload that the destination's generator cannot render fails closed and leaves no branch behind
    fx.branch("docs/content-engine-2026-45")
    (fx.root / "docs/api/v1/reports").mkdir(parents=True, exist_ok=True)
    (fx.root / "docs/api/v1/reports/2026-45.json").write_text("{not json")
    (fx.root / "docs/api/v1/reports/index.json").write_text(proofs.blob(fx.root, fx.base, "docs/api/v1/reports/index.json").decode())
    broken = fx.commit("broken payload")
    with pytest.raises(reconcile.ReconcileError):
        reconcile.buildReplacement(fx.root, h.REPO, 9, broken, "2026-45", fx.base, tmp_path / "wt-broken")
    assert "docs/steward-pr-9-2026-45" not in h.run(fx.root, "branch", "--list")


# --- the operator surface -------------------------------------------------------------------------------------------

def test_cli_reconcile_builds_once_records_budget_and_reports_an_opened_replacement(tmp_path, capsys):
    import json

    from gaia_cli.steward.prmaintenance import cli, state

    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44", version="8.26.10")
    h.writeCensus(fx, h.census([h.row(fx, original, "2026-44", number=2157)], fx.base))
    root = str(fx.root)
    assert cli.main(["--root", root, "--json", "reconcile", "--number", "2157", "--run-id", "r1", "--worktree", str(tmp_path / "wt")]) == 0
    built = json.loads(capsys.readouterr().out)
    assert built["branch"] == "docs/steward-pr-2157-2026-44" and "gaia-steward:replaces" in built["body"]
    assert state.readRecords(fx.root, "outcomes")[-1]["state"] == "built"
    # a second build in the same run is over the policy's replacement budget only when the cap is reached; a different run may build
    assert cli.main(["--root", root, "--json", "reconcile-opened", "--number", "2157", "--head", original, "--replacement", "2290",
                     "--branch", built["branch"], "--run-id", "r1"]) == 0
    capsys.readouterr()
    assert cli.main(["--root", root, "--json", "reconcile", "--number", "2157", "--run-id", "r2", "--worktree", str(tmp_path / "wt2")]) == 3
    assert json.loads(capsys.readouterr().out)["alreadyDone"] == "replacement-opened"
    # a withdrawn replacement may be rebuilt; the retirement is on the record
    assert cli.main(["--root", root, "--json", "reconcile-retired", "--number", "2157", "--head", original, "--replacement", "2290",
                     "--reason", "branch renamed", "--run-id", "r2"]) == 0
    capsys.readouterr()
    assert cli.main(["--root", root, "--json", "reconcile", "--number", "2157", "--run-id", "r3", "--worktree", str(tmp_path / "wt3")]) == 0


def test_cli_reconcile_refuses_what_is_not_proven_reconcilable_or_is_revoked(tmp_path, capsys):
    import json

    from gaia_cli.steward.prmaintenance import cli, state

    fx = h.makeRepo(tmp_path / "w")
    clean = fx.head("2026-44")  # already merge-ready: nothing to reconcile
    h.writeCensus(fx, h.census([h.row(fx, clean, "2026-44", number=2157)], fx.base))
    root = str(fx.root)
    assert cli.main(["--root", root, "--json", "reconcile", "--number", "2157", "--run-id", "r1", "--worktree", str(tmp_path / "a")]) == 2
    assert json.loads(capsys.readouterr().out)["refused"] == "not-reconcilable"
    assert cli.main(["--root", root, "--json", "reconcile", "--number", "999", "--run-id", "r1", "--worktree", str(tmp_path / "b")]) == 2
    capsys.readouterr()
    stale = fx.head("2026-45", version="8.0.0")
    h.writeCensus(fx, h.census([h.row(fx, stale, "2026-45", number=2270)], fx.base))
    (state.storeDir(fx.root) / state.KILL_FILE).write_text("x")
    assert cli.main(["--root", root, "--json", "reconcile", "--number", "2270", "--run-id", "r1", "--worktree", str(tmp_path / "c")]) == 2
    assert json.loads(capsys.readouterr().out)["refused"] == "kill-switch"


# --- the destination moves after a replacement was built (the auto-release restamps every page) ----------------------

def release(fx, version="9.1.0"):
    """What the repository's auto-release does on every merge: bump the version and restamp every page, on main."""

    h.run(fx.root, "checkout", "-q", "main")
    (fx.root / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8")
    for page in sorted((fx.root / "docs/reports").glob("*/index.html")) + [fx.root / "docs/reports/index.html"]:
        page.write_text(h.stamped(page.read_text(encoding="utf-8"), version), encoding="utf-8")
    (fx.root / "docs/about.html").write_text("<html>about</html>\n", encoding="utf-8")
    return fx.commit(f"chore: release v{version} [skip-gen]")


def test_a_replacement_is_refreshed_onto_a_moved_tip_without_rewriting_history_and_passes_every_proof(tmp_path):
    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44", version="8.26.10")
    made = reconcile.buildReplacement(fx.root, h.REPO, 2157, original, "2026-44", fx.base, tmp_path / "wt")
    tip = release(fx)
    assert proofs.stampProof(fx.root, tip, made.commit, list(made.files)).state == "fail"  # stale against the new tip
    refreshed = reconcile.refreshReplacement(fx.root, "2026-44", tmp_path / "wt", tip, number=2157, originalHead=original, repo=h.REPO)
    assert refreshed.commit != made.commit and refreshed.branch == made.branch
    ancestry = h.run(fx.root, "merge-base", "--is-ancestor", made.commit, refreshed.commit)  # raises if not an ancestor: history is kept
    assert h.run(fx.root, "merge-base", "--is-ancestor", tip, refreshed.commit) == ancestry
    assert set(h.run(fx.root, "diff", "--name-only", tip, refreshed.commit).splitlines()) == set(made.files)
    for proof in [proofs.reportJsonProof(fx.root, refreshed.commit, "2026-44"), proofs.stampProof(fx.root, tip, refreshed.commit, list(made.files))] \
            + proofs.contentEngineProofs(fx.root, tip, refreshed.commit, "2026-44"):
        assert proof.state == "pass", proof
    assert proofs.blob(fx.root, refreshed.commit, "docs/api/v1/reports/2026-44.json") == proofs.blob(fx.root, original, "docs/api/v1/reports/2026-44.json")


def test_refresh_refuses_a_dirty_worktree_a_missing_tip_and_a_bad_label(tmp_path):
    fx = h.makeRepo(tmp_path / "w")
    original = fx.head("2026-44", version="8.26.10")
    made = reconcile.buildReplacement(fx.root, h.REPO, 2157, original, "2026-44", fx.base, tmp_path / "wt")
    tip = release(fx)
    (tmp_path / "wt" / "docs/reports/stray.txt").write_text("x")
    with pytest.raises(reconcile.ReconcileError, match="uncommitted"):
        reconcile.refreshReplacement(fx.root, "2026-44", tmp_path / "wt", tip, number=2157, originalHead=original)
    (tmp_path / "wt" / "docs/reports/stray.txt").unlink()
    with pytest.raises(reconcile.ReconcileError, match="not available locally"):
        reconcile.refreshReplacement(fx.root, "2026-44", tmp_path / "wt", "e" * 40, number=2157, originalHead=original)
    with pytest.raises(reconcile.ReconcileError, match="ISO week"):
        reconcile.refreshReplacement(fx.root, "../x", tmp_path / "wt", tip, number=2157, originalHead=original)
    assert made.commit
