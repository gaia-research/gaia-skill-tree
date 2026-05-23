try:
    from gaia_cli.tui.app import GaiaApp
    __all__ = ["GaiaApp"]
except ImportError as _e:
    raise ImportError(
        "TUI requires the 'textual' package. Install with: pip install 'gaia-cli[tui]'"
    ) from _e
