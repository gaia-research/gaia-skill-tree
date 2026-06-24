---
name: update-suite-instructions
description: Sync suite skill installation instructions with upstream sources and ensure Gaia-compliant styling.
---

# update-suite-instructions

Sync suite skill installation instructions with upstream sources and ensure Gaia-compliant styling.

## Context
Suite skills (like `ruvnet/ruflo`, `garrytan/gstack`, and `obra/superpowers`) often have detailed installation instructions in their upstream READMEs. This skill automates the synchronization of these instructions into the Gaia registry while enforcing consistency and adherence to `DESIGN.md`.

## Instructions
1. Run `python3 scripts/update_suite_instructions.py` to fetch, standardize, and inject the latest instructions.
2. The script will:
   - Fetch sections from upstream READMEs (e.g., "Installation", "Quick Start").
   - Standardize code blocks to use `bash` syntax.
   - Apply the Matt Pocock suite template to all Matt Pocock skills.
   - Run `scripts/generateNamedIndex.py` to update the generated `named-skills.json`.
3. Verify the changes in the relevant `.md` files in `registry/named/` and the resulting `registry/named-skills.json`.
4. If a suite is missing instructions, refer to the tracking issue created for undocumented suites.

## Resource
- `scripts/update_suite_instructions.py`: The automation script.
- `scripts/generateNamedIndex.py`: The registry indexer.
- `DESIGN.md`: Visual design language and styling rules.
- `registry/named/`: Source markdown files for named skills.
