---
id: mattpocock/obsidian-vault
name: Obsidian Vault Manager
contributor: mattpocock
origin: false
genericSkillRef: personal-knowledge-management
status: named
title: The Obsidian Vault Mapper
level: 3★
description: Manage notes and organization in a specific Obsidian vault using Title
  Case and wikilinks.
createdAt: '2026-05-21'
updatedAt: '2026-06-04'
suiteRef: mattpocock/personal
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-22'
  notes: Obsidian vault management and PKM automation.
---

## Installation

This skill is included in the Matt Pocock skills suite:

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required.

### Setup Requirements

The vault maintains "a mostly flat structure at root level" without folder-based organization.

Configure your Obsidian vault path as part of the personal knowledge management setup.

### How to Use

**Naming & Structure:**
- All notes use **Title Case** formatting
- Index notes aggregate related topics (example: "RAG Index.md")
- Organization relies on **wikilinks** rather than folders

**Linking Convention:**
- Use "Obsidian `[[wikilinks]]` syntax" for related notes
- List dependencies and connected notes at the bottom of each note

### Core Operations

**1. Searching notes** — Use find commands for filenames or grep to search content across markdown files

**2. Creating notes** — Write content as a self-contained learning unit:
   - Add wikilinks to related topics
   - Apply title case to filenames
   - Include backlinks at the bottom

**3. Finding connections** — Search for backlinks by grepping for specific `[[Note Title]]` references throughout the vault

**4. Locating indexes** — Use find commands to identify all `*Index*` files that serve as topic aggregators

### Key Principle

The system prioritizes **interconnected content discovery** through wikilinks over hierarchical folder structures. This creates a web of related information accessible from any note.
