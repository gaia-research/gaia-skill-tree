"""Golden wreaths identify only skills that hold Origin."""

import json
import subprocess
from pathlib import Path

from scripts.generateProfilePages import _field_avatar


ROOT = Path(__file__).resolve().parents[1]
WREATH = "plaque__avatar-wreath"
HEROES_JS = (ROOT / "docs" / "heroes" / "heroes.js").read_text(encoding="utf-8")
LEADERBOARD_JS = (ROOT / "docs" / "trust" / "leaderboard" / "leaderboard.js").read_text(encoding="utf-8")


def _js_avatar(skill: dict) -> str:
    program = """
const fs = require('fs');
global.window = {};
eval(fs.readFileSync('docs/js/plaque.js', 'utf8'));
process.stdout.write(window.plaque._fields.avatar(JSON.parse(process.argv[1])));
"""
    result = subprocess.run(
        ["node", "-e", program, json.dumps(skill)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _skill(origin: bool) -> dict:
    return {
        "id": "alice/example",
        "contributor": "alice",
        "level": "2★",
        "origin": origin,
        "links": {"github": "https://github.com/alice/example"},
    }


def test_client_avatar_wreath_requires_origin_true():
    assert WREATH not in _js_avatar(_skill(False))
    assert WREATH in _js_avatar(_skill(True))


def test_profile_avatar_wreath_requires_origin_true():
    assert WREATH not in _field_avatar(_skill(False))
    assert WREATH in _field_avatar(_skill(True))


def test_hero_and_leaderboard_wreaths_require_origin():
    assert "var wreathHtml = isOrigin" in HEROES_JS
    assert "function appendAvatarWreath(parent, cx, cy, r, isOrigin)" in LEADERBOARD_JS
    assert "if (!isOrigin) return;" in LEADERBOARD_JS
    assert "appendAvatarWreath(barGroup, avatarCx, avatarCy, avatarR, !!ult.origin);" in LEADERBOARD_JS
    assert "appendAvatarWreath(barGroup, avatarCx, avatarCy, avatarR, !!suite.origin);" in LEADERBOARD_JS
    assert "appendAvatarWreath(barGroup, avatarCx, avatarCy, avatarR, !!skill.origin);" in LEADERBOARD_JS
    # #1435 perf refactor: origin membership is now cached per-contributor
    # option in buildContributorOptions() rather than recomputed inline.
    # The invariant is preserved: hasOrigin is only set true when a skill
    # carries origin, and renderList() gates the wreath on opt.hasOrigin.
    assert "if (s.origin === true) byContributor[c].hasOrigin = true;" in LEADERBOARD_JS
    assert "(opt.hasOrigin ? '<img class=\"lb-ms-avatar-wreath\"" in LEADERBOARD_JS
