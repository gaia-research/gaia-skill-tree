"""GaiaApp — root Textual application."""

from __future__ import annotations

import os

from textual.app import App, ComposeResult

from gaia_cli.tui.screens.hero import HeroScreen


def _load_meta() -> tuple[str, str, str]:
    """Return (registry_path, username, version)."""
    from gaia_cli.scanner import load_config
    from gaia_cli.registry import resolve_registry_path

    cfg = load_config() or {}
    username = cfg.get("gaiaUser", cfg.get("user", ""))
    registry_path = resolve_registry_path()

    version = "?"
    try:
        from importlib.metadata import version as _ver
        version = _ver("gaia-cli")
    except Exception:
        try:
            import tomllib  # type: ignore
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                tomllib = None
        if tomllib:
            _here = os.path.dirname(os.path.abspath(__file__))
            _root = os.path.dirname(os.path.dirname(os.path.dirname(_here)))
            _pp = os.path.join(_root, "pyproject.toml")
            if os.path.exists(_pp):
                with open(_pp, "rb") as f:
                    _data = tomllib.load(f)
                version = _data.get("project", {}).get("version", "?")

    return registry_path, username, version


class GaiaApp(App):
    """Gaia skill registry TUI."""

    CSS_PATH = os.path.join(os.path.dirname(__file__), "theme.tcss")
    TITLE = "Gaia"

    def on_mount(self) -> None:
        registry_path, username, version = _load_meta()
        self.push_screen(HeroScreen(registry_path, username, version))
