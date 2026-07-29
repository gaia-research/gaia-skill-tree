"""`gaia dev evidence-seed <skill-id>` — emit the RFC2 Gap C evidence-seed.

Ungated (writes under ``evidence/``, not the canonical registry — consistent
with ``gaia dev prefill`` which writes to ``registry-for-review/``, and unlike
``gaia dev evidence`` which mutates registry frontmatter and is Verifier-gated).
This is the L4-approved-intake -> evidence-collection handoff (#1148 §2).
"""

import sys

from gaia_cli.evidenceSeed import emitEvidenceSeed


def _parseSource(spec):
    """Parse a ``--source`` spec ``url::type[::scope]`` into a source dict.

    Uses ``::`` as the separator so URLs (which contain single ':') are not
    split mid-scheme. Returns ``{url, type[, scope]}`` or raises ValueError.
    """
    parts = spec.split("::")
    if len(parts) < 2:
        raise ValueError(
            f"--source {spec!r}: expected 'url::type' or 'url::type::scope'"
        )
    url = parts[0].strip()
    evType = parts[1].strip()
    if not url or not evType:
        raise ValueError(f"--source {spec!r}: url and type are both required")
    source = {"url": url, "type": evType}
    if len(parts) >= 3 and parts[2].strip():
        source["scope"] = parts[2].strip()
    return source


def evidenceSeedCommand(args):
    """Entry point for ``gaia dev evidence-seed``."""
    skillId = args.skill_id
    if not getattr(args, "sources", None):
        print(
            "ERROR: at least one --source URL::TYPE is required.",
            file=sys.stderr,
        )
        return 1

    try:
        sources = [_parseSource(s) for s in args.sources]
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        result = emitEvidenceSeed(
            skillId,
            sources,
            attributionScope=getattr(args, "scope", "standalone"),
            appendCollectors=not getattr(args, "no_collectors", False),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Emitted evidence-seed for '{skillId}': {len(result['rows'])} row(s).")
    for path in result["artifactPaths"]:
        print(f"  artifact -> {path}")
    for path in sorted(result["collectorPaths"]):
        print(f"  collector -> {path}")
    return 0
