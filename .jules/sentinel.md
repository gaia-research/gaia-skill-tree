## 2025-05-24 - [Medium] Pin Dependency Versions in GitHub Actions
**Vulnerability:** Several GitHub actions and the composite action in packages/cli-npm/github-action/action.yml were using `pip install requests pyyaml jsonschema` without pinning versions.
**Learning:** This exposes the pipeline to supply chain attacks. If a compromised package update is pushed to PyPI, the action automatically installs the latest vulnerable version, leading to potential RCE on the GitHub runner.
**Prevention:** Always pin dependencies using `==` to known secure versions in CI pipelines or use a lockfile (like `uv.lock`).

## 2024-05-20 - Fix Command Injection in triage.py
**Vulnerability:** Critical Command Injection vulnerability found in `.agents/skills/graphify-triage/scripts/triage.py` where `subprocess.run` was executed with `shell=True` and string concatenation containing unsanitized input (`p['title']`, `p['body']`).
**Learning:** Shell utilities or scripting tools that call CLI programs like `gh` are prone to this when wrapping shell commands for convenience without sanitizing arguments.
**Prevention:** Always use a list of arguments for `subprocess.run` instead of string interpolation and never use `shell=True` unless absolutely necessary (and with properly sanitized inputs).
## 2025-02-28 - Command Injection in triage.py
**Vulnerability:** Found a command injection vulnerability in `.agents/skills/graphify-triage/scripts/triage.py` where `subprocess.run` was called with `shell=True` and string interpolated arguments for `gh issue create`.
**Learning:** `shell=True` allows injection via specially crafted string inputs (like issue titles or bodies).
**Prevention:** Avoid using `shell=True` unless absolutely necessary, and construct subprocess commands safely using an argument list instead of string interpolation to rely on argument escaping.

## 2026-05-23 - XSS Vulnerability in skill-graph.js Tooltips
**Vulnerability:** Found multiple instances of `innerHTML` being set with unsanitized data (e.g. `skill.name`, `skill.id`) in `docs/js/skill-graph.js`, specifically when rendering tooltips, neighbor cards, and the skill panel.
**Learning:** While the primary data source (`graph/gaia.json`) is considered trusted registry data, relying solely on upstream data trust creates a defense-in-depth gap. If the registry data generation is compromised or modified to contain malicious HTML, the UI will execute it.
**Prevention:** Always implement and use an HTML escaping function (like `esc`) when dynamically building HTML strings for `innerHTML`, even if the data source is nominally "trusted".
