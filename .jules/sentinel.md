## 2025-05-24 - [Medium] Pin Dependency Versions in GitHub Actions
**Vulnerability:** Several GitHub actions and the composite action in packages/cli-npm/github-action/action.yml were using `pip install requests pyyaml jsonschema` without pinning versions.
**Learning:** This exposes the pipeline to supply chain attacks. If a compromised package update is pushed to PyPI, the action automatically installs the latest vulnerable version, leading to potential RCE on the GitHub runner.
**Prevention:** Always pin dependencies using `==` to known secure versions in CI pipelines or use a lockfile (like `uv.lock`).

## 2024-05-20 - Fix Command Injection in triage.py
**Vulnerability:** Critical Command Injection vulnerability found in `.agents/skills/graphify-triage/scripts/triage.py` where `subprocess.run` was executed with `shell=True` and string concatenation containing unsanitized input (`p['title']`, `p['body']`).
**Learning:** Shell utilities or scripting tools that call CLI programs like `gh` are prone to this when wrapping shell commands for convenience without sanitizing arguments.
**Prevention:** Always use a list of arguments for `subprocess.run` instead of string interpolation and never use `shell=True` unless absolutely necessary (and with properly sanitized inputs).
