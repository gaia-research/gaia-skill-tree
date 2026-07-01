"""Preflight coverage for gaia dev verify."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.verify import meta_verify_command

pytestmark = [pytest.mark.integration]


def _make_registry(tmp_path: Path, evidence: list) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}), encoding="utf-8")
    (nodes / "demo-skill.json").write_text(
        json.dumps(
            {
                "id": "demo-skill",
                "name": "Demo Skill",
                "type": "basic",
                "description": "A demo skill for verify tests.",
                "evidence": evidence,
                "timeline": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(tmp_path)


def _load_node(root: str) -> dict:
    return json.loads(
        (Path(root) / "registry" / "nodes" / "basic" / "demo-skill.json").read_text(
            encoding="utf-8"
        )
    )


def _args(root: str, **kw) -> SimpleNamespace:
    base = dict(
        registry=root,
        skill_id="demo-skill",
        index=0,
        dispute=False,
        notes=None,
        source=None,
        no_build=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.verify._get_contributor", lambda: "verifier")
    monkeypatch.setattr("gaia_cli.commands.dev.verify._is_verifier", lambda *a, **kw: True)
    monkeypatch.setattr("gaia_cli.commands.dev.verify._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.verify.append_skill_event", lambda *a, **kw: None)


def test_verify_negative_index_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path, [{"source": "https://example.com/a"}])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_verify_command(_args(root, index=-1))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "Evidence index -1 out of range" in capsys.readouterr().err


def test_verify_invalid_source_url_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path, [{"source": "https://example.com/a"}])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_verify_command(_args(root, source="not-a-url"))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "absolute http(s) URL" in capsys.readouterr().err


def test_verify_rejects_already_verified_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path, [{"source": "https://example.com/a", "verified": True}])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_verify_command(_args(root))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "already verified" in capsys.readouterr().err


def test_dispute_rejects_already_disputed_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path, [{"source": "https://example.com/a", "disputed": True}])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        meta_verify_command(_args(root, dispute=True))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "already disputed" in capsys.readouterr().err


def test_verify_happy_path_marks_verified(tmp_path):
    root = _make_registry(tmp_path, [{"source": "https://example.com/a"}])

    meta_verify_command(_args(root, source="https://example.com/review"))

    entry = _load_node(root)["evidence"][0]
    assert entry["verified"] is True
    assert entry["disputed"] is False
    assert entry["verificationSource"] == "https://example.com/review"
