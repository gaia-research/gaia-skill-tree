from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.knowledge_contracts import (
    AUTHORITY_MAP,
    MAX_INPUT_BYTES,
    TRUST_SURFACES,
    check_trust_guidance,
)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_inputs(root: Path) -> None:
    _write(root, AUTHORITY_MAP, "# Active map\n")
    for surface in TRUST_SURFACES:
        _write(root, surface, "See curation-authority-map.md for authority.\n")


def test_clean_active_contract_is_healthy(tmp_path: Path) -> None:
    _valid_inputs(tmp_path)
    assert check_trust_guidance(tmp_path) == []


@pytest.mark.parametrize("missing", [AUTHORITY_MAP, TRUST_SURFACES[0]])
def test_missing_required_semantic_input_raises(tmp_path: Path, missing: str) -> None:
    _valid_inputs(tmp_path)
    (tmp_path / missing).unlink()
    with pytest.raises(OSError, match="required trust guidance input unavailable"):
        check_trust_guidance(tmp_path)


def test_unreadable_required_input_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _valid_inputs(tmp_path)
    original_open = Path.open
    blocked = tmp_path / TRUST_SURFACES[0]

    def reject_target(path: Path, *args, **kwargs):
        if path == blocked:
            raise PermissionError("fixture unreadable")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_target)
    with pytest.raises(OSError, match="required trust guidance input unavailable"):
        check_trust_guidance(tmp_path)


def test_oversized_input_fails_closed_as_truncated(tmp_path: Path) -> None:
    _valid_inputs(tmp_path)
    (tmp_path / AUTHORITY_MAP).write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="possibly truncated"):
        check_trust_guidance(tmp_path)


@pytest.mark.parametrize("empty", ["", "   ", "\n\t  \n"])
@pytest.mark.parametrize("required", [AUTHORITY_MAP, TRUST_SURFACES[0]])
def test_empty_required_semantic_input_fails_closed(tmp_path: Path, required: str, empty: str) -> None:
    _valid_inputs(tmp_path)
    _write(tmp_path, required, empty)
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        check_trust_guidance(tmp_path)


def test_archives_and_handover_history_are_not_scanned(tmp_path: Path) -> None:
    _valid_inputs(tmp_path)
    retired_claim = "`github-stars-own` and `repo-own` pointing to the same URL → deduped"
    for relative in (
        "founder/handovers/old.md",
        "founder/retros/archive.md",
        "docs/agents/archive/old.md",
    ):
        _write(tmp_path, relative, retired_claim)
    assert check_trust_guidance(tmp_path) == []


def test_active_surface_retired_claim_is_detected(tmp_path: Path) -> None:
    _valid_inputs(tmp_path)
    target = TRUST_SURFACES[0]
    _write(
        tmp_path,
        target,
        "See curation-authority-map.md. `github-stars-own` and `repo-own` pointing to the same URL → deduped.\n",
    )
    violations = check_trust_guidance(tmp_path)
    assert any(v["source"] == target and v["rule"] == "retired-trust-claim" for v in violations)


@pytest.mark.parametrize(
    "text",
    [
        "There is no mothership discount. See curation-authority-map.md.",
        'Warning: the old phrase "mothership discount" is retired. See curation-authority-map.md.',
        "Warning: the old phrase `mothership discount` is retired. See curation-authority-map.md.",
    ],
)
def test_mothership_warning_and_negation_are_not_mistaken_for_claim(tmp_path: Path, text: str) -> None:
    _valid_inputs(tmp_path)
    _write(tmp_path, TRUST_SURFACES[0], text)
    assert not any(
        v["source"] == TRUST_SURFACES[0] and v["rule"] == "retired-trust-claim"
        for v in check_trust_guidance(tmp_path)
    )


@pytest.mark.parametrize(
    "claim",
    [
        "A mothership discount applies.",
        'A \'mothership discount\' applies.',
    ],
)
def test_mothership_discount_claim_is_detected(tmp_path: Path, claim: str) -> None:
    _valid_inputs(tmp_path)
    _write(tmp_path, TRUST_SURFACES[0], f"{claim} See curation-authority-map.md.")
    violations = check_trust_guidance(tmp_path)
    assert any(v["source"] == TRUST_SURFACES[0] and v["rule"] == "retired-trust-claim" for v in violations)


def test_authority_map_link_is_required_on_each_active_surface(tmp_path: Path) -> None:
    _valid_inputs(tmp_path)
    _write(tmp_path, TRUST_SURFACES[-1], "Trust policy reference omitted.\n")
    violations = check_trust_guidance(tmp_path)
    assert any(v["source"] == TRUST_SURFACES[-1] and v["rule"] == "trust-authority-map-link" for v in violations)
