---
id: mattpocock/caveman
name: Caveman Mode
contributor: mattpocock
origin: false
genericSkillRef: context-compression
status: named
title: "The Caveman Console"
level: 3★
description: An ultra-compressed communication mode designed to save tokens by dropping
  articles and filler words.
createdAt: '2026-05-21'
updatedAt: '2026-06-04'
suiteRef: "mattpocock/productivity"
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/caveman
---

## Installation

This skill is included in the Matt Pocock skills suite:

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required.

### How to Activate

Trigger with any of these phrases:

- "caveman mode"
- "talk like caveman"
- "use caveman"
- "less tokens"
- "be brief"
- "/caveman" command

Mode activates immediately upon invocation.

### How It Works

Compresses communication by approximately **75% token reduction**. Maintains technical precision while eliminating unnecessary elements.

**Removed:**
- Articles (a/an/the)
- Padding words (just/really/basically)
- Pleasantries (sure/certainly)
- Hedging language

**Preserved:**
- Exact technical terminology
- Code blocks
- Error messages
- Causal relationships (shown with arrows: X → Y)

**Style:**
- Fragments acceptable
- Short word choices prioritized
- Conjunctions optional

### Example

Instead of: "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by..."

Write: "Bug in auth middleware. Token expiry check use `<` not `<=`. Fix:"

### Deactivation

Mode persists across multiple responses. Disable with explicit commands:

- "stop caveman"
- "normal mode"
