import os
import pytest
from unittest.mock import patch
from pathlib import Path

from gaia_cli.commands.dev.rename_named import meta_rename_named_command
from gaia_cli.timeline import _parse_md

class MockArgs:
    def __init__(self, registry, old_id, new_id):
        self.registry = registry
        self.old_id = old_id
        self.new_id = new_id

@pytest.fixture
def mock_registry(tmp_path):
    registry = tmp_path / "registry"
    named_dir = registry / "named" / "acme"
    named_dir.mkdir(parents=True)
    
    # old_slug.md
    old_content = """---
id: acme/old-slug
catalogRef: acme-old-slug
timeline: []
---
Body text
"""
    (named_dir / "old-slug.md").write_text(old_content, encoding="utf-8")
    
    # other.md
    other_content = """---
id: acme/other
suiteComponents:
  - acme/old-slug
  - acme/another-slug
suiteRef: acme/old-slug
genericSkillRef: acme/old-slug
timeline: []
---
Body text 2
"""
    (named_dir / "other.md").write_text(other_content, encoding="utf-8")
    
    os.environ["GAIA_OPERATOR_OVERRIDE"] = "1"
    yield registry
    if "GAIA_OPERATOR_OVERRIDE" in os.environ:
        del os.environ["GAIA_OPERATOR_OVERRIDE"]

def test_rename_named_success(mock_registry):
    args = MockArgs(registry=str(mock_registry.parent), old_id="acme/old-slug", new_id="acme/new-slug")
    
    with patch("gaia_cli.commands.dev.rename_named._run_docs_build") as mock_build:
        meta_rename_named_command(args)
        
        mock_build.assert_called_once()
        
    named_dir = mock_registry / "named" / "acme"
    
    assert not (named_dir / "old-slug.md").exists()
    assert (named_dir / "new-slug.md").exists()
    
    # Verify new file
    meta, _ = _parse_md(named_dir / "new-slug.md")
    assert meta["id"] == "acme/new-slug"
    assert meta["catalogRef"] == "acme-new-slug"
    
    # Verify timeline event
    assert "timeline" in meta
    assert len(meta["timeline"]) == 1
    assert meta["timeline"][0]["action"] == "rename"
    assert "acme/old-slug" in meta["timeline"][0]["details"]
    
    # Verify cross references in other.md
    meta_other, _ = _parse_md(named_dir / "other.md")
    assert "acme/new-slug" in meta_other["suiteComponents"]
    assert "acme/old-slug" not in meta_other["suiteComponents"]
    assert meta_other["suiteRef"] == "acme/new-slug"
    assert meta_other["genericSkillRef"] == "acme/new-slug"

def test_rename_named_invalid_new_id(mock_registry):
    args = MockArgs(registry=str(mock_registry.parent), old_id="acme/old-slug", new_id="no-slash-id")
    
    with pytest.raises(SystemExit) as excinfo:
        meta_rename_named_command(args)
        
    assert excinfo.value.code == 1
