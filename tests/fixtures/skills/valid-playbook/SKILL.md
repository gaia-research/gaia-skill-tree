---
name: valid-playbook
description: A valid Gaia agent playbook fixture for quick validation and contract checking.
playbookVersion: 1
class: B
objective: Produce a bounded fixture result.
capability: Apply bounded repository judgment without routing authority.
preconditions:
  - the fixture directory exists
steps:
  - id: inspect-fixture
    run: gaia dev list --generic --json > {snapshot}
    proves: snapshot captured
stopConditions:
  - escalation to founder queue required
proof:
  - snapshot exists
done: Bounded fixture review complete.
---

# Valid Playbook Fixture

This fixture tests that quick validation recognizes playbookVersion: 1 fields.
