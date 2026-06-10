import os
import sys
import pytest
from unittest.mock import patch, MagicMock

def test_tui_flag_exists():
    from gaia_cli.main import get_parser
    parser, _ = get_parser()
    args = parser.parse_args(['--tui'])
    assert args.tui is True

def test_tui_usage_mentions_gaia():
    from gaia_cli.main import COMMAND_USAGE
    from helpers import strip_ansi
    plain = strip_ansi(COMMAND_USAGE)
    assert "Open command selector" in plain

def test_force_color_formatting():
    from gaia_cli.formatting import _use_color
    
    # Test FORCE_COLOR
    with patch.dict(os.environ, {"FORCE_COLOR": "1"}):
        with patch.dict(os.environ, {"NO_COLOR": ""}):
            assert _use_color() is True
    
    # Test CLICOLOR_FORCE
    with patch.dict(os.environ, {"CLICOLOR_FORCE": "1", "NO_COLOR": ""}):
        assert _use_color() is True

    # Test NO_COLOR (should take precedence)
    with patch.dict(os.environ, {"NO_COLOR": "1", "FORCE_COLOR": "1"}):
        assert _use_color() is False

def test_tui_flag_execs_skills():
    """--tui flag causes main() to call os.execvp to replace process with 'gaia skills'."""
    from gaia_cli.main import main

    # Record the arguments passed to os.execvp
    execvp_calls = []

    def mock_execvp(program, args):
        execvp_calls.append((program, args))
        # Raise SystemExit to mimic process replacement
        raise SystemExit(0)

    with patch.object(sys, "argv", ["gaia", "--tui"]):
        with patch("os.execvp", mock_execvp):
            with pytest.raises(SystemExit) as exc_info:
                main()

    # Verify execvp was called
    assert len(execvp_calls) == 1
    program, args = execvp_calls[0]
    # The final element of args should be 'skills'
    assert args[-1] == "skills"
    assert exc_info.value.code == 0

def test_resolve_registry_path_usage_in_formatting():
    from gaia_cli import formatting
    with patch('gaia_cli.formatting.resolve_registry_path') as mock_resolve:
        mock_resolve.return_value = os.getcwd()
        try:
            formatting._load_palette_from_registry()
        except Exception:
            pass
        mock_resolve.assert_called()

def test_resolve_registry_path_usage_in_tokens():
    try:
        from gaia_cli.tui import tokens
        with patch('gaia_cli.tui.tokens.resolve_registry_path') as mock_resolve:
            mock_resolve.return_value = os.getcwd()
            try:
                tokens._load_meta()
            except Exception:
                pass
            mock_resolve.assert_called()
    except ImportError:
        pytest.skip("textual not installed")

def test_scan_screen_ansi_passthrough():
    try:
        from gaia_cli.tui.screens.scan import ScanScreen
        from rich.text import Text
        
        screen = ScanScreen(registry_path=".")
        test_line = "\x1b[31mRed Text\x1b[0m"
        result = screen._style_line(test_line)
        
        assert isinstance(result, Text)
        assert len(result.spans) > 0
        assert "Red Text" in result.plain
    except ImportError:
        pytest.skip("textual/rich not installed")
