# METASHIFT: May 2026 Programmatic Registry Audit

This audit restores registry integrity by enforcing hardened prestige rules from **META.md** and canonical terms from **CONTEXT.md**. All rank shifts are executed via the `gaia` CLI to ensure timeline logging.

## 1. Reclassifications (Schema Integrity)

Unique skills demoted below 4★ must be reclassified to **Basics** to pass validation.

| Skill ID | Current Rank | Action | CLI Command |
|---|---|---|---|
| `few-shot-learning` | 4★ | Reclassify to Basic | `gaia dev reclassify few-shot-learning basic` |
| `self-consistency` | 4★ | Reclassify to Basic | `gaia dev reclassify self-consistency basic` |

## 2. Star Bar Enforcement (3★+ GitHub Requirement)

Demoted to **Named** (2★) rank due to missing verified GitHub implementation links.

| Skill ID | Rank | CLI Command |
|---|---|---|
| `code-review-pipeline` | 2★ | `gaia dev calibrate code-review-pipeline 2★` |
| `content-moderation` | 2★ | `gaia dev calibrate content-moderation 2★` |
| `function-calling` | 2★ | `gaia dev calibrate function-calling 2★` |
| `multimodal-reasoning` | 2★ | `gaia dev calibrate multimodal-reasoning 2★` |
| `text-to-sql-pipeline` | 2★ | `gaia dev calibrate text-to-sql-pipeline 2★` |
| `translation-pipeline` | 2★ | `gaia dev calibrate translation-pipeline 2★` |
| `vision-qa` | 2★ | `gaia dev calibrate vision-qa 2★` |
| `multi-agent-debate` | 2★ | `gaia dev calibrate multi-agent-debate 2★` |
| `skill-security-analysis` | 2★ | `gaia dev calibrate skill-security-analysis 2★` |
| `few-shot-learning` | 2★ | `gaia dev calibrate few-shot-learning 2★` |
| `self-consistency` | 2★ | `gaia dev calibrate self-consistency 2★` |
| `pexp13/sentiment-analysis` | 2★ | `gaia dev calibrate pexp13/sentiment-analysis 2★` |

## 3. Elite Rank & Evidence Adjustments

| Skill ID | Rank | CLI Command |
|---|---|---|
| `autonomous-debug` | 3★ | `gaia dev calibrate autonomous-debug 3★` |
| `mattpocock-skills` | 6★ | `gaia dev calibrate mattpocock-skills 6★` |
| `mattpocock-engineering`| 5★ | `gaia dev calibrate mattpocock-engineering 5★` |
| `superpowers` | 5★ | `gaia dev calibrate superpowers 5★` |

## 4. Pruning & Unnamed Demotions

Skills with placeholder or non-verifiable evidence demoted to **Awakened** (1★) rank.

| Target ID | Rank | Action | CLI Command |
|---|---|---|---|
| `Taoidle/plan-decompose-gh-plan-cascade` | 1★ | Demote & Unname | `gaia dev update-named Taoidle/plan-decompose-gh-plan-cascade --status awakened` |
| `changkun/plan-decompose-gh-wallfacer` | 1★ | Demote & Unname | `gaia dev update-named changkun/plan-decompose-gh-wallfacer --status awakened` |

## 5. Contributor Suite Promotions

Promoting the **IntelligentCode-AI** suite to **Named** (2★) rank with behavioral titles.

| Named Skill ID | Action | CLI Command |
|---|---|---|
| `intelligentcode-ai/*` | Promote (8 skills) | `gaia dev update-named intelligentcode-ai/<id> --status named` |

## 6. Evidence Health Demotions (Liveness Heartbeat)

Automated demotions based on `scripts/verify_evidence.py` results. Affected skills are demoted by one level and assigned the `broken-evidence` demerit.

| Skill ID | Previous Rank | New Rank | Demerit |
|---|---|---|---|
| `audience-model` | 1★ | 0★ | `broken-evidence` |
| `autonomous-debug` | 2★ | 1★ | `broken-evidence` |
| `conversational-agent` | 2★ | 1★ | `broken-evidence` |
| `document-analyst` | 2★ | 1★ | `broken-evidence` |
| `grill-with-docs` | 2★ | 1★ | `broken-evidence` |
| `grounding` | 2★ | 1★ | `broken-evidence` |
| `mcp-debugger-control` | 3★ | 2★ | `broken-evidence` |
| `research` | 2★ | 1★ | `broken-evidence` |
| `stealth-browser-interaction` | 3★ | 2★ | `broken-evidence` |
| `ubiquitous-language` | 3★ | 2★ | `broken-evidence` |
| `web-scrape` | 2★ | 1★ | `broken-evidence` |
| `...` | ... | ... | `broken-evidence` |

*(Note: Total of 35 skills processed for evidence rot.)*

## 7. Execution protocol

1. Commit METASHIFT.md.
2. Execute batch CLI commands.
3. Validate and Build.
