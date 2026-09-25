---
name: invalid-ordinary-with-playbook-fields
description: "An ordinary skill lacking playbookVersion: 1 but defining playbook fields."
class: B
objective: Not allowed on ordinary skill
steps:
  - id: step-one
    run: gaia dev list --generic
    proves: listed
---

# Invalid Ordinary Skill With Playbook Fields
