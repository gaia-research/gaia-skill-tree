#!/usr/bin/env python3
"""Operator and driver entrypoint for routine PR maintenance (routine 19). See `python scripts/steward_pr.py --help`.

Deliberately a script, like steward_issue_close.py: it adds no public `gaia` verb, so `gaia help` is unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gaia_cli.steward.prmaintenance.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
