"""Test CLI Command Migration under gaia dev namespace and deprecation warnings."""

import sys
import os
import pytest
from pathlib import Path
pytestmark = [pytest.mark.integration]


# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers import strip_ansi
from gaia_cli.main import main, PUBLIC_COMMANDS, get_parser

def run_cli(monkeypatch, argv: list[str]):
    """Invoke main() with the given argv."""
    monkeypatch.setattr(sys, "argv", ["gaia", *argv])
    main()

# ---------------------------------------------------------------------------
# Cycle 1: gaia dev validate invokes validation pipeline
# ---------------------------------------------------------------------------
class TestDevValidate:
    def test_dev_validate_invokes_pipeline(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """test 'gaia dev validate' invokes validation pipeline and exits 0."""
        # Setup registry path and config
        registry_path = tmp_path
        (registry_path / "registry").mkdir(parents=True, exist_ok=True)
        (registry_path / "registry" / "gaia.json").write_text('{"skills": []}', encoding="utf-8")
        
        # Mock subprocess.call inside main.py to verify it's called with validate.py
        called_cmds = []
        import subprocess
        monkeypatch.setattr(subprocess, "call", lambda cmd, **kwargs: called_cmds.append(cmd) or 0)
        
        # Mock sys.exit to raise instead of terminating the test runner
        monkeypatch.setattr(sys, "exit", lambda code: pytest.fail(f"sys.exit called with {code}") if code != 0 else None)
        
        # We also need to avoid calling redaction_script/timeline_script if they don't exist
        # actually, validate_command checks for existence of scripts, which is good.
        
        # Run command: gaia dev validate
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(registry_path), "dev", "validate"])
        
        assert exc.value.code == 0
        assert any("validate.py" in str(cmd) for cmd in called_cmds)


# ---------------------------------------------------------------------------
# Cycle 2: gaia validate prints deprecation warning and delegates
# ---------------------------------------------------------------------------
class TestShimValidate:
    def test_validate_deprecation_warning(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """test 'gaia validate' prints deprecation warning and runs validation."""
        registry_path = tmp_path
        (registry_path / "registry").mkdir(parents=True, exist_ok=True)
        (registry_path / "registry" / "gaia.json").write_text('{"skills": []}', encoding="utf-8")
        
        called_cmds = []
        import subprocess
        monkeypatch.setattr(subprocess, "call", lambda cmd, **kwargs: called_cmds.append(cmd) or 0)
        monkeypatch.setattr(sys, "exit", lambda code: pytest.fail(f"sys.exit called with {code}") if code != 0 else None)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(registry_path), "validate"])
            
        assert exc.value.code == 0
        assert any("validate.py" in str(cmd) for cmd in called_cmds)
        
        # Verify deprecation warning was printed to stderr
        err = capsys.readouterr().err
        assert "DEPRECATED" in err or "deprecated" in err
        assert "gaia dev validate" in err


# ---------------------------------------------------------------------------
# Cycle 3: gaia dev release bumps version, gaia release prints warning
# ---------------------------------------------------------------------------
class TestReleaseMigration:
    def test_dev_release(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """test 'gaia dev release patch' delegates to release_command."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_release(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "release_command", mock_release)
        
        # Mock authz require_operator
        from gaia_cli import authz
        monkeypatch.setattr(authz, "require_operator", lambda *a, **kw: None)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "dev", "release", "patch", "--no-push"])
        assert exc.value.code == 0
        assert len(called) == 1
        assert called[0].release_type == "patch"

    def test_release_deprecation(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """test 'gaia release patch' warns and delegates."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_release(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "release_command", mock_release)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "release", "patch", "--no-push"])
        
        assert exc.value.code == 0
        assert len(called) == 1
        err = capsys.readouterr().err
        assert "DEPRECATED" in err or "deprecated" in err
        assert "gaia dev release" in err


# ---------------------------------------------------------------------------
# Cycle 4: gaia dev test and gaia test shim
# ---------------------------------------------------------------------------
class TestTestMigration:
    def test_dev_test(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """test 'gaia dev test all' delegates to test_command."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_test(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "test_command", mock_test)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "dev", "test", "all"])
        assert exc.value.code == 0
        assert len(called) == 1
        assert called[0].suite == "all"

    def test_test_deprecation(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """test 'gaia test all' warns and delegates."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_test(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "test_command", mock_test)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "test", "all"])
        
        assert exc.value.code == 0
        assert len(called) == 1
        err = capsys.readouterr().err
        assert "DEPRECATED" in err or "deprecated" in err
        assert "gaia dev test" in err


# ---------------------------------------------------------------------------
# Cycle 5: gaia dev docs and gaia docs build shim
# ---------------------------------------------------------------------------
class TestDocsMigration:
    def test_dev_docs(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """test 'gaia dev docs --check' delegates to docs_command."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_docs(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "docs_command", mock_docs)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "dev", "docs", "--check"])
        assert exc.value.code == 0
        assert len(called) == 1
        assert called[0].check is True

    def test_docs_deprecation(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """test 'gaia docs build' warns and delegates."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_docs(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "docs_command", mock_docs)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "docs", "build"])
        
        assert exc.value.code == 0
        assert len(called) == 1
        err = capsys.readouterr().err
        assert "DEPRECATED" in err or "deprecated" in err
        assert "gaia dev docs" in err


# ---------------------------------------------------------------------------
# Cycle 6: gaia dev mcp and gaia mcp shim
# ---------------------------------------------------------------------------
class TestMcpMigration:
    def test_dev_mcp(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """test 'gaia dev mcp' delegates to mcp_command."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_mcp(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "mcp_command", mock_mcp)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "dev", "mcp"])
        assert exc.value.code == 0
        assert len(called) == 1

    def test_mcp_deprecation(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """test 'gaia mcp' warns and delegates."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_mcp(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "mcp_command", mock_mcp)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "mcp"])
        
        assert exc.value.code == 0
        assert len(called) == 1
        err = capsys.readouterr().err
        assert "DEPRECATED" in err or "deprecated" in err
        assert "gaia dev mcp" in err


# ---------------------------------------------------------------------------
# Cycle 8: gaia dev hook and gaia _hook shim
# ---------------------------------------------------------------------------
class TestHookMigration:
    def test_dev_hook(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """test 'gaia dev hook' delegates to hook_command."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_hook(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "hook_command", mock_hook)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "dev", "hook", "--event", "test"])
        assert exc.value.code == 0
        assert len(called) == 1
        assert called[0].event == "test"

    def test_hook_deprecation(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """test 'gaia _hook' warns and delegates."""
        called = []
        import gaia_cli.main as gaia_main
        def mock_hook(args):
            called.append(args)
            raise SystemExit(0)
        monkeypatch.setattr(gaia_main, "hook_command", mock_hook)
        
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), "_hook", "--event", "test"])
        
        assert exc.value.code == 0
        assert len(called) == 1
        err = capsys.readouterr().err
        assert "DEPRECATED" in err or "deprecated" in err
        assert "gaia dev hook" in err

