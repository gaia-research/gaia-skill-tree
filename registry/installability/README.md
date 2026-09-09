# Tree-scoped installability

This directory owns the optional, operator-generated installability contract.
It is deliberately separate from the named-skill registry and does not change
star levels or admission.

## Observation

The standalone parity probe can write a bounded observation for a selected
scope:

```bash
python scripts/install_parity.py \
  --only garrytan/health --jobs 1 \
  --observation /tmp/garrytan-health-observation.json
```

The existing parity report, verdict, and exit code remain unchanged. The
observation records Gaia-side health separately from the npm comparator and
includes source route (with both the raw entrypoint and the actual Gaia
install subpath), canonical registry content hash, the revision actually
resolved in Gaia's clone cache, delivered-content digest when a real local
skill tree was observed, tool context, and bounded/redacted diagnostics.
Operational failures have no positive installability meaning.

An observation becomes publishable under `observations/<sha256>.json` only
after the required human/evidence gate. Do not copy an agent-authored probe
there and label it human evidence. The initial projection may therefore be an
honest all-`unknown` snapshot. Pre-fix scratch records are not migrated or
silently rewritten; if a future contract revision changes route fields, old
immutable records remain on their original schema and are ignored or rejected
until an explicit migration policy exists.

## Projection

`docs/graph/installability/index.json` is generated offline by the docs build.
It reads only canonical registry content and committed observations; it never
runs `install_parity.py`, invokes a network, or invents a TTL. It includes the
current source route and content hash for each skill in the current named-tree
scope. A route/content mismatch, stale observation, unobserved skill,
operational failure, or equally-current conflict is `unknown`.

`materializable` means Gaia positively materialized a real local skill tree for
the exact observed route/content scope. `not-materializable` is reserved for
a correct no-source refusal or direct local intrinsic-content evidence.
Unknown is not an admission whitelist, and absence from this tree does not
speak for another candidate source.
