# Gaia Evidence Checkpoints

Use these paths and commands to verify issue status in the `gaia-skill-tree` repository.

## CLI Commands
- Implementation: `src/gaia_cli/commands/`
- Logic: `src/gaia_cli/core/`
- Entry point: `src/gaia_cli/main.py`

## Documentation
- Source: `docs/`
- Generated: Check if `python scripts/build_docs.py --check` passes.
- README: `README.md` (check for usage examples).

## Testing
- Unit/Integration: `tests/`
- To verify a fix: `pytest tests/test_<module>.py`

## Registry & Skills
- Registry data: `registry/gaia.json`
- Skill definitions: `skills/`
- Validation: `python scripts/validate_registry.py` (if it exists)

## Common Issue Patterns

| Issue Type | Where to Verify |
| :--- | :--- |
| **New Command** | `src/gaia_cli/commands/` and `README.md` |
| **Bug in Scan** | `src/gaia_cli/commands/scan.py` and `tests/test_scan.py` |
| **Dependency** | `pyproject.toml` and `uv.lock` |
| **Docs Drift** | `scripts/build_docs.py` |
| **Skill Metadata** | `registry/gaia.json` |
