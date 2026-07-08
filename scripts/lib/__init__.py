"""
scripts.lib — shared infrastructure primitives for Gaia registry scripts.

Design contract (upstream-watcher design §9):
  Primitives belong here only when used by ≥2 scripts.
  This is not a dumping ground for one-script helpers.

Public sub-modules:
  frontmatter     — regex-based frontmatter parse/rewrite
  github_api      — GitHub API client + URL parser
  named_iterator  — walk registry/named/**/*.md

Import each sub-module directly:
  from scripts.lib.frontmatter import split_frontmatter
  from scripts.lib.github_api import parse_owner_repo, fetch_json, head_check
  from scripts.lib.named_iterator import iter_named_skills

Do NOT import from this package-level __init__ — doing so would trigger all
sub-module loads regardless of which primitive you actually need.
"""

__version__ = "0.1.0"
