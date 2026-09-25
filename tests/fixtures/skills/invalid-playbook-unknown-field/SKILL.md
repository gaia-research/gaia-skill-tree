---
name: invalid-playbook-unknown-field
description: A playbook containing an unexpected frontmatter field.
playbookVersion: 1
class: B
objective: Produce a bounded result.
capability: Apply bounded repository judgment.
preconditions:
  - precondition met
steps:
  - id: step-one
    run: gaia dev list --generic
    proves: listed
stopConditions:
  - stop
proof:
  - proof
done: done
inventedPlaybookField: illegal
---

# Invalid Playbook Unknown Field Fixture
