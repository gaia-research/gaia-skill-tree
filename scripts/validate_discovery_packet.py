#!/usr/bin/env python3
"""Run the canonical gaia-curate discovery-packet validator."""

from __future__ import annotations

import runpy
from pathlib import Path


VALIDATOR = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "gaia-curate"
    / "scripts"
    / "validate_discovery_packet.py"
)


if __name__ == "__main__":
    runpy.run_path(str(VALIDATOR), run_name="__main__")
