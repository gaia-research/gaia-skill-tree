# Epic #780 — Agent Testing Handover

**Created:** 2026-06-22
**Purpose:** Instructions for an agent to run comprehensive testing on the Epic #780 architectural changes.

## Context

Epic #780 restructured the CLI from a monolithic 4,078-line `main.py` into ~15 autodiscovered command modules, migrated dev-only commands under `gaia dev`, removed generated files from Git tracking, added skill quality gates, and introduced a Taskfile for cross-language orchestration.

## Testing Checklist

### 1. CLI Behavioral Parity (CRITICAL)

The most important test: every command must produce identical output before and after the refactor.

```bash
# Capture baseline (run on main BEFORE merging)
git checkout main
mkdir -p /tmp/epic780-baseline
gaia --help > /tmp/epic780-baseline/help.txt 2>&1
gaia dev --help > /tmp/epic780-baseline/dev-help.txt 2>&1
gaia version > /tmp/epic780-baseline/version.txt 2>&1
gaia tree --check > /tmp/epic780-baseline/tree-check.txt 2>&1

# Capture post-refactor (run on integration branch)
git checkout dev/improve-codebase-architecture
mkdir -p /tmp/epic780-after
gaia --help > /tmp/epic780-after/help.txt 2>&1
gaia dev --help > /tmp/epic780-after/dev-help.txt 2>&1
gaia version > /tmp/epic780-after/version.txt 2>&1
gaia tree --check > /tmp/epic780-after/tree-check.txt 2>&1

# Diff
diff -u /tmp/epic780-baseline/ /tmp/epic780-after/
```

**Expected:** Zero diff on help output. Version may differ (expected).

### 2. Deprecation Shim Verification

Test that old top-level commands still work but warn:

```bash
for cmd in "release patch --sync --no-push" "validate" "test all" "docs build --check"; do
  echo "=== Testing: gaia $cmd ==="
  gaia $cmd 2>&1 | head -3
  echo "---"
done
```

**Expected:** Each prints a deprecation warning to stderr, then runs successfully.

### 3. Command Discovery Smoke Test

Verify autodiscovery found all commands:

```python
# Run in Python
from gaia_cli.main import _discover_commands
cmds = _discover_commands()
expected = {"init", "scan", "fetch", "pull", "update", "install", "uninstall",
            "share", "tree", "push", "propose", "version", "whoami", "login",
            "logout", "reset", "graph", "stats", "appraise", "promote",
            "fuse", "lookup", "path", "skills", "dev"}
missing = expected - set(cmds.keys())
extra = set(cmds.keys()) - expected
print(f"Missing: {missing}")
print(f"Extra: {extra}")
assert not missing, f"Missing commands: {missing}"
```

### 4. Full Test Suite

```bash
pip install -e ".[dev,embeddings,docs]"
python -m pytest tests/ -v --timeout=120
```

**Expected:** All 61 test files pass.

### 5. Generated Artifact Verification

```bash
# Verify generated files not tracked
tracked=$(git ls-files -- registry/gaia.json docs/graph/gaia.json base_gaia.json | wc -l)
echo "Tracked generated files: $tracked (should be 0)"

# Verify build regenerates them
gaia dev build
ls -la registry/gaia.json docs/graph/gaia.json
```

### 6. Skill Quality Gates

```bash
python scripts/validate_skills.py
echo "Exit code: $? (should be 0)"

# Deliberately break a SKILL.md to test the gate
echo "---" > /tmp/test-broken-skill.md
echo "broken: true" >> /tmp/test-broken-skill.md
echo "---" >> /tmp/test-broken-skill.md
# (Don't actually commit this — just verify the validator catches it)
```

### 7. Taskfile

```bash
# Install task: https://taskfile.dev/installation/
task validate
task test
task build
```

### 8. Interactive Selector

```bash
# This requires a TTY — run manually:
gaia
# Expected: interactive command selector appears with all public commands
```

### 9. MCP Daemon

```bash
gaia dev mcp start
gaia dev mcp status   # should say "running"
gaia dev mcp stop
gaia dev mcp status   # should say "stopped"
```

## Reporting

After running all tests, create a summary:

```markdown
## Epic #780 Agent Test Report — [DATE]

| Test | Result | Notes |
|---|---|---|
| CLI behavioral parity | ✅/❌ | diff output if any |
| Deprecation shims | ✅/❌ | |
| Command discovery | ✅/❌ | missing/extra commands |
| Full test suite | ✅/❌ | failures if any |
| Generated artifacts | ✅/❌ | |
| Skill quality gates | ✅/❌ | |
| Taskfile | ✅/❌ | |
| Interactive selector | ✅/❌ | |
| MCP daemon | ✅/❌ | |
```

Write the report to `founder/reports/EPIC780_TEST_REPORT.md`.
