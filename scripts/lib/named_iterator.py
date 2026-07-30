"""Compatibility wrapper for :mod:`gaia_registry_lib.named_iterator`."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from gaia_registry_lib.named_iterator import *  # noqa: F401,F403
except ModuleNotFoundError:  # pragma: no cover - checkout fallback before install
    _LIB_SRC = Path(__file__).resolve().parents[2] / "packages" / "gaia-registry-lib" / "src"
    if str(_LIB_SRC) not in sys.path:
        sys.path.insert(0, str(_LIB_SRC))
    from gaia_registry_lib.named_iterator import *  # noqa: F401,F403,E402
