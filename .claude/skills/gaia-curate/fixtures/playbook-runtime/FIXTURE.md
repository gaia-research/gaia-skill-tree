# Playbook execution fixture

This fixture exists only for `scripts/run_fixture_dry_run.py`. The harness copies
the bounded [`workspace/registry/gaia.json`](workspace/registry/gaia.json),
[`workspace/registry/embeddings.json`](workspace/registry/embeddings.json), and
[`workspace/registry/schema/meta.json`](workspace/registry/schema/meta.json) to
its caller-supplied temporary output before invoking the live Gaia CLI.

[`source/UPSTREAM_SKILL.md`](source/UPSTREAM_SKILL.md) represents the fetched
upstream `SKILL.md` artifact without exposing the fixture as a discoverable
project skill.
[`python/sentence_transformers/__init__.py`](python/sentence_transformers/__init__.py)
provides one deterministic query vector, avoiding network or model-cache access
while leaving the live prefill command, ranking, packet, and validator code in
the execution path.
