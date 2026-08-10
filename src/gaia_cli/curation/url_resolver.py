"""GitHub URL resolution helpers for the scaffolded curate command."""

from __future__ import annotations


def normalize_github_url(url: str) -> str:
    """Normalize a GitHub URL into the canonical blob URL for a skill file.

    Future implementation responsibilities:
    - Accept repository roots, tree URLs, blob URLs, raw GitHub URLs, and known
      shorthand forms where safe.
    - Resolve branch names to immutable commits so the curation ledger can record
      a stable source artifact.
    - Prefer actual ``SKILL.md`` files; reject unrelated markdown files unless the
      caller explicitly selected them.
    - Preserve owner/repo casing only where GitHub requires it, and emit a
      canonical ``https://github.com/<owner>/<repo>/blob/<commit>/.../SKILL.md``
      URL.
    - Raise clear, actionable errors for unsupported hosts, missing repos,
      ambiguous multiple skill files, and non-existent paths.
    """
    raise NotImplementedError("GitHub URL normalization is not implemented yet.")


def find_skill_files(repo: str) -> list:
    """Return candidate ``SKILL.md`` files for a GitHub repository.

    Future implementation responsibilities:
    - Accept an ``owner/repo`` string or a normalized repository URL.
    - Query the repository tree at the resolved default branch or commit.
    - Return deterministic candidate records for every plausible skill file,
      including path, blob URL, raw URL, content SHA, and resolved commit.
    - Ignore generated/vendor directories and apply Gaia curation heuristics for
      duplicated examples or template files.
    - Leave selection to the orchestrator/interactive layer when multiple valid
      candidates are discovered.
    """
    raise NotImplementedError("GitHub skill-file discovery is not implemented yet.")
