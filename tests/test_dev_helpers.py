"""Tests for dev helpers."""

import json
from pathlib import Path

import pytest
from gaia_cli.commands.dev import helpers


def test_parse_write_md(tmp_path: Path):
    md_file = tmp_path / "test.md"
    
    meta = {"id": "test_id", "level": "1★"}
    body = "\n# Title\nSome content."
    
    # Write
    helpers._write_md(md_file, meta, body)
    
    # Read
    read_meta, read_body = helpers._parse_md(md_file)
    
    assert read_meta["id"] == "test_id"
    assert read_meta["level"] == "1★"
    assert read_body == body


def test_replace_section():
    original = "## Section A\ncontent A\n## Section B\ncontent B"
    
    # Replace existing
    replaced = helpers._replace_section(original, "Section A", "new A")
    assert "## Section A\nnew A\n\n## Section B" in replaced
    
    # Append new
    appended = helpers._replace_section(original, "Section C", "new C")
    assert "## Section C\n\nnew C" in appended


def test_is_generated():
    assert helpers._is_generated("docs/index.html") is True
    assert helpers._is_generated("registry/gaia.json") is False  # Not in the exact list or suffix
    assert helpers._is_generated("registry/named-skills.json") is True
    assert helpers._is_generated("src/main.py") is False


def test_parse_named_frontmatter():
    content = "---\nid: test\nlevel: 2★\n---\nbody"
    meta = helpers._parse_named_frontmatter(content)
    assert meta["id"] == "test"
    assert meta["level"] == "2★"
