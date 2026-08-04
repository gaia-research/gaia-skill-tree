"""Share-card medallion rasterization safeguards."""

import base64
import re

import pytest

PIL_Image = pytest.importorskip("PIL.Image")

from scripts import generateOgCards


def test_og_medallion_inliner_transcodes_webp_to_png_data_uri():
    href = "/assets/ascension-overdrive/aov4-c5-suite-ultimate-hero.webp"
    svg = f'<svg><image href="{href}" xlink:href="{href}"/></svg>'

    inlined = generateOgCards._inline_medallion_assets(svg)

    assert href not in inlined
    assert "data:application/octet-stream" not in inlined
    assert "data:image/png;base64," in inlined

    match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", inlined)
    assert match, "expected an inlined PNG data URI"
    assert base64.b64decode(match.group(1))[:8] == b"\x89PNG\r\n\x1a\n"
