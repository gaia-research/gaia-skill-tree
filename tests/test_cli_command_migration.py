"""Test the canonical `gaia dev` command namespace.

The deprecated top-level shims (`gaia release`, `gaia _hook`, `gaia docs build`,
`gaia mcp`, `gaia validate`, `gaia test`) were retired in v7.0.0. These tests
verify the canonical `gaia dev X` forms still dispatch and that the retired
top-level forms no longer resolve (argparse exits non-zero).
"""

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
# Retired top-level shims no longer resolve (argparse rejects the choice).
# ---------------------------------------------------------------------------
class TestRetiredTopLevelShims:
    @pytest.mark.parametrize(
        "argv",
        [
            ["release", "patch"],
            ["mcp"],
            ["validate"],
            ["test", "all"],
            ["docs", "build"],
            ["_hook"],
        ],
    )
    def test_retired_shim_errors(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path, argv):
        """test retired top-level shim exits non-zero (unknown command)."""
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--registry", str(tmp_path), *argv])
        # argparse rejects an unknown subcommand with exit code 2.
        assert exc.value.code != 0
        err = capsys.readouterr().err
        assert "invalid choice" in err


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
# Cycle 3: gaia dev release bumps version
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


# ---------------------------------------------------------------------------
# Cycle 4: gaia dev test
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


# ---------------------------------------------------------------------------
# Cycle 5: gaia dev docs
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


# ---------------------------------------------------------------------------
# Cycle 6: gaia dev mcp
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


# ---------------------------------------------------------------------------
# Cycle 8: gaia dev hook
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
