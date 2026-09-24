#!/usr/bin/env python3
"""Upstream-compatible quick skill validation script for Gaia.

Reconciles generic skill-creator quick validation with Gaia playbook frontmatter.
Delegates to scripts/quick_validate_skill.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.quick_validate_skill import (
    ALLOWED_BASE_PROPERTIES,
    GAIA_METADATA_PROPERTIES,
    PLAYBOOK_PROPERTIES,
    adapt_upstream_validator,
    main,
    validate_frontmatter_dict,
    validate_skill,
)

__all__ = [
    "ALLOWED_BASE_PROPERTIES",
    "GAIA_METADATA_PROPERTIES",
    "PLAYBOOK_PROPERTIES",
    "adapt_upstream_validator",
    "main",
    "validate_frontmatter_dict",
    "validate_skill",
]

if __name__ == "__main__":
    raise SystemExit(main())
