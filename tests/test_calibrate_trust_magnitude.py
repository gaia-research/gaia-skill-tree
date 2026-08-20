"""Tests for `gaia dev calibrate-trust-magnitude` (Issue #1600).

Covers:
- Dry-run reports old -> new without writing
- Live run writes trustMagnitude/overallTrustGrade/trustMagnitudeInputHash
  and appends a recalibrate_trust_magnitude timeline event
- A skill whose cached hash is already valid is left untouched (no-op)
- --skill against a nonexistent id fails the pre-flight
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.calibrate import calibrate_trust_magnitude_command
from gaia_cli.trustMagnitude import computeTrustMagnitude, computeTrustMagnitudeInputHash

pytestmark = [pytest.mark.integration]


def _write_component(named_dir: Path, slug: str, grade: str = "B") -> None:
    contributor, name = slug.split("/", 1)
    skill_dir = named_dir / contributor
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / f"{name}.md").write_text(
        f"---\nid: {slug}\ncontributor: {contributor}\nstatus: named\nlevel: 2★\n"
        f"overallTrustGrade: {grade}\n---\n## Installation\n",
        encoding="utf-8",
    )


def _write_suite_skill(named_dir: Path, slug: str, components: list[str], **frontmatter) -> Path:
    contributor, name = slug.split("/", 1)
    skill_dir = named_dir / contributor
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / f"{name}.md"
    lines = [
        f"id: {slug}",
        f"contributor: {contributor}",
        "status: named",
        "level: 4★",
    ]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {value}")
    lines.append("suiteComponents:")
    lines.extend(f"  - {c}" for c in components)
    path.write_text("---\n" + "\n".join(lines) + "\n---\n## Installation\n", encoding="utf-8")
    return path


def _make_registry(tmp_path: Path) -> str:
    named_dir = tmp_path / "registry" / "named"
    _write_component(named_dir, "acme/comp-a", grade="B")
    _write_component(named_dir, "acme/comp-b", grade="C")
    _write_suite_skill(
        named_dir, "acme/suite", ["acme/comp-a", "acme/comp-b"],
        trustMagnitude=999.0, overallTrustGrade="S",
        trustMagnitudeInputHash="deliberately-wrong-hash",
    )
    return str(tmp_path)


def _args(registry_root: str, **overrides) -> SimpleNamespace:
    base = dict(
        registry=registry_root, skill=["acme/suite"], all=False,
        dry_run=False, yes=True, no_build=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _read_frontmatter(path: Path) -> dict:
    import yaml
    text = path.read_text(encoding="utf-8")
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm)


def test_live_run_writes_recomputed_fields_and_timeline(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "mbtiongson1")
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.calibrate.append_skill_event",
        lambda skill_id, action, contributor, details, registry_path=".": events.append(
            (skill_id, action, contributor, details)
        ),
    )

    calibrate_trust_magnitude_command(_args(root))

    path = Path(root) / "registry" / "named" / "acme" / "suite.md"
    fm = _read_frontmatter(path)
    assert fm["trustMagnitude"] != 999.0
    assert fm["overallTrustGrade"] != "S" or fm["trustMagnitude"] != 999.0
    assert fm["trustMagnitudeInputHash"] == computeTrustMagnitudeInputHash(fm)

    assert len(events) == 1
    skill_id, action, contributor, details = events[0]
    assert skill_id == "acme/suite"
    assert action == "recalibrate_trust_magnitude"
    assert contributor == "mbtiongson1"
    assert "999.0" in details


def test_dry_run_does_not_write(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "mbtiongson1")
    monkeypatch.setattr(
        "gaia_cli.commands.dev.calibrate.append_skill_event",
        lambda *a, **kw: pytest.fail("append_skill_event must not run in --dry-run"),
    )

    calibrate_trust_magnitude_command(_args(root, dry_run=True))

    path = Path(root) / "registry" / "named" / "acme" / "suite.md"
    fm = _read_frontmatter(path)
    assert fm["trustMagnitude"] == 999.0


def test_already_valid_hash_is_a_noop(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "mbtiongson1")
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.calibrate.append_skill_event",
        lambda *a, **kw: events.append(a),
    )

    # First run brings the cache in sync.
    calibrate_trust_magnitude_command(_args(root))
    assert len(events) == 1

    # Second run against the now-correct cache must be a no-op.
    calibrate_trust_magnitude_command(_args(root))
    assert len(events) == 1


def test_missing_skill_fails_preflight(tmp_path, monkeypatch, capsys):
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "mbtiongson1")

    with pytest.raises(SystemExit) as excinfo:
        calibrate_trust_magnitude_command(_args(root, skill=["acme/does-not-exist"]))

    assert excinfo.value.code == 1
    assert "does-not-exist" in capsys.readouterr().err
