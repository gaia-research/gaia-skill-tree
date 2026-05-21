## 2025-02-28 - Command Injection in triage.py
**Vulnerability:** Found a command injection vulnerability in `.agents/skills/graphify-triage/scripts/triage.py` where `subprocess.run` was called with `shell=True` and string interpolated arguments for `gh issue create`.
**Learning:** `shell=True` allows injection via specially crafted string inputs (like issue titles or bodies).
**Prevention:** Avoid using `shell=True` unless absolutely necessary, and construct subprocess commands safely using an argument list instead of string interpolation to rely on argument escaping.
