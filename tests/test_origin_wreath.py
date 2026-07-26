"""Golden wreaths identify only skills that hold Origin."""

import json
import subprocess
from pathlib import Path

from scripts.generateProfilePages import _field_avatar


ROOT = Path(__file__).resolve().parents[1]
WREATH = "plaque__avatar-wreath"


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
