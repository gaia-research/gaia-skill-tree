"""Compatibility wrapper for :mod:`gaia_registry_lib.github_api`."""

from __future__ import annotations

import sys
from pathlib import Path


def _prefer_checkout_shared_lib() -> None:
    """Prefer the adjacent shared-lib checkout over any installed wheel."""
    lib_src = Path(__file__).resolve().parents[2] / "packages" / "gaia-registry-lib" / "src"
    if not lib_src.is_dir():
        return

    lib_src_str = str(lib_src)
    try:
        sys.path.remove(lib_src_str)
    except ValueError:
        pass
    sys.path.insert(0, lib_src_str)


_prefer_checkout_shared_lib()

from gaia_registry_lib.github_api import *  # noqa: F401,F403,E402
from gaia_registry_lib.github_api import _CACHE  # noqa: F401,E402
