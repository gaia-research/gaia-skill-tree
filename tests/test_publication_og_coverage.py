"""Strict OG publication must reconcile the entire freshly rendered tree."""
import json
from pathlib import Path

import pytest

from scripts import build_docs, generateOgCards, publication_parity


def test_rehearsal_removes_orphan_png_and_refreshes_real_render(tmp_path, monkeypatch):
    pytest.importorskip("cairosvg")
    named = tmp_path / "named.json"
    named.write_text(json.dumps({"buckets": {"fixture": [{
        "id": "example/card", "contributor": "example", "name": "Card",
        "level": "2★", "type": "basic", "branch": "unique", "rankWord": "Common",
    }]}}))
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    monkeypatch.setattr(build_docs, "SCRIPTS", Path(generateOgCards.__file__).parent)
    monkeypatch.setattr(build_docs, "_STRICT_REHEARSAL", True, raising=False)

    def generate(script, args):
        generateOgCards.generate_og_cards(named, Path(args[1]))
        return 0, ""

    monkeypatch.setattr(build_docs, "_run_script", generate)
    committed = tmp_path / "docs/og"
    generateOgCards.generate_og_cards(named, committed)
    card = committed / "example/card.png"
    rendered = card.read_bytes()
    assert rendered.startswith(b"\x89PNG\r\n\x1a\n")
    orphan = committed / "retired/orphan.png"
    orphan.parent.mkdir()
    orphan.write_bytes(rendered)
    card.write_bytes(b"stale")

    # Ordinary builders retain the historical non-destructive PNG behavior.
    monkeypatch.setattr(build_docs, "_STRICT_REHEARSAL", False)
    assert not build_docs.build_og_cards(False)
    assert orphan.exists() and card.read_bytes() == b"stale"
    monkeypatch.setattr(build_docs, "_STRICT_REHEARSAL", True)
    # SVGs are unchanged: the old early return previously left orphan PNGs.
    assert build_docs.build_og_cards(False)
    assert not orphan.exists()
    assert card.read_bytes() == rendered
    reference = tmp_path / "reference"
    generateOgCards.generate_og_cards(named, reference)
    publication_parity._tree(committed, reference, ".png")
    card.write_bytes(b"stale")
    with pytest.raises(ValueError, match="semantic mismatch"):
        publication_parity._tree(committed, reference, ".png")
    card.write_bytes(rendered)
    orphan.write_bytes(rendered)
    with pytest.raises(ValueError, match="coverage mismatch"):
        publication_parity._tree(committed, reference, ".png")


@pytest.mark.parametrize("old_png", [False, True])
def test_rehearsal_rejects_missing_raster(tmp_path, monkeypatch, old_png):
    named = tmp_path / "named.json"
    named.write_text(json.dumps({"buckets": {"fixture": [{
        "id": "example/card", "contributor": "example", "name": "Card", "level": "2★",
        "branch": "unique", "rankWord": "Common",
    }]}}))
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    monkeypatch.setattr(build_docs, "SCRIPTS", Path(generateOgCards.__file__).parent)
    monkeypatch.setattr(build_docs, "_STRICT_REHEARSAL", True, raising=False)
    monkeypatch.setattr(generateOgCards, "try_render_png", lambda *args: False)
    def generate(script, args):
        generateOgCards.generate_og_cards(named, Path(args[1]))
        return 0, ""
    monkeypatch.setattr(build_docs, "_run_script", generate)
    stale = tmp_path / "docs/og/example/card.png"
    if old_png:
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"stale")
    with pytest.raises(RuntimeError, match="incomplete OG PNG coverage"):
        build_docs.build_og_cards(False)
    assert stale.read_bytes() == b"stale" if old_png else not stale.exists()
