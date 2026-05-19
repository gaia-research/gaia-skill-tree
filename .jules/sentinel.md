## 2025-05-24 - [Medium] Pin Dependency Versions in GitHub Actions
**Vulnerability:** Several GitHub actions and the composite action in packages/cli-npm/github-action/action.yml were using `pip install requests pyyaml jsonschema` without pinning versions.
**Learning:** This exposes the pipeline to supply chain attacks. If a compromised package update is pushed to PyPI, the action automatically installs the latest vulnerable version, leading to potential RCE on the GitHub runner.
**Prevention:** Always pin dependencies using `==` to known secure versions in CI pipelines or use a lockfile (like `uv.lock`).
