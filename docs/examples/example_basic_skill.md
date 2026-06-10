# Example: New Basic Skill Submission

This is a filled-out example of a `new_basic_skill.md` PR for reference.

---

## New Basic Skill

### Skill Details
- **ID:** `parseCsv`
- **Name:** Parse CSV
- **Level:** II
- **Description:** Extracts structured tabular data from CSV-formatted input, handling delimiters, quoted fields, headers, and encoding variants.

### Evidence
| Class | Source | Evaluator | Date | Notes |
|---|---|---|---|---|
| C | https://github.com/example/csv-demo/blob/main/README.md | mbtiongson1 | 2026-04-26 | Demonstrated CSV parsing across 5 edge-case files with correct output. |

### Checklist

**Contributor:**
- [x] Skill ID uses `camelCase` with no vendor references.
- [x] Description is precise, falsifiable, and non-overlapping with existing skills.
- [x] Evidence meets the minimum threshold for the claimed level (2★ = Evidence Tier C+).
- [x] `prerequisites` array is empty (basic skills have no parents).
- [x] `derivatives` array lists known child skills: `documentAnalyst`.
- [x] I have run `python scripts/validate.py` locally and it passes.
- [x] I have NOT edited any files in `skills/`, `registry.md`, or `combinations.md`.

### Changes to `gaia.json`

Added to `skills` array:

```json
{
  "id": "parseCsv",
  "name": "Parse CSV",
  "type": "basic",
  "level": "2★",
  "description": "Extracts structured tabular data from CSV-formatted input, handling delimiters, quoted fields, headers, and encoding variants.",
  "prerequisites": [],
  "derivatives": ["documentAnalyst"],
  "conditions": "",
  "evidence": [
    {
      "class": "C",
      "source": "https://github.com/example/csv-demo/blob/main/README.md",
      "evaluator": "mbtiongson1",
      "date": "2026-04-26",
      "notes": "Demonstrated CSV parsing across 5 edge-case files with correct output."
    }
  ],
  "knownAgents": [],
  "status": "provisional",
  "createdAt": "2026-04-26",
  "updatedAt": "2026-04-26",
  "version": "0.1.0"
}
```
