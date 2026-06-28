# Privacy Notice

**Gaia — AI Agent Skill Registry** is an open, public project. We are committed to keeping it free of personal data by design.

---

## What We Store

| Item | Stored? | Notes |
|------|---------|-------|
| Public GitHub usernames | ✅ Yes | Only when you explicitly submit a named skill under your handle |
| Public repository URLs | ✅ Yes | `links.github` pointing to your public skill repo |
| Skill descriptions | ✅ Yes | Generalised capability summaries, not personal narratives |
| Code or file contents | ❌ No | We store only a skill's *type*, *level*, and *evidence class* |
| Personal details | ❌ Never | Names, emails, locations, DMs, private repo paths — none of this enters the registry |
| In-skill implementation details | ❌ No | The CLI summarises what a skill *does*; it does not capture or transmit prompt contents, conversation history, or output |

---

## How Skills Are Recorded

`gaia scan` analyses your repository structure to detect evidence of agent capabilities. It:

- Reads **file shapes and patterns** (tool calls, function signatures, test coverage) to infer skill presence.
- Records a **capability summary** — the *type* of skill and its evidence class (A / B / C).
- Does **not** read, store, or transmit file contents, prompt text, or any personal information.

When you run `gaia push`, only the summarised skill metadata (skill id, level, evidence class, and your chosen public GitHub repo URL) is included in the draft batch sent for review. Reviewers never see raw source.

---

## Named Skills

A *named skill* (2★+) attaches a public GitHub username as the skill's credited author. This is:

- **Opt-in**: you run `gaia propose` or `gaia push` to submit your name.
- **Public-only**: only your GitHub handle and a public repo URL are recorded — never an email, real name, or any private identifier.
- **Generalised by default**: the description field captures the capability category, not personal details about you or your agent's behaviour.

---

## What We Do Not Collect

- Email addresses
- IP addresses or device identifiers
- Conversation history or LLM outputs
- Private repository contents or paths
- Any data from users who have not explicitly submitted a skill

---

## Third Parties

The Gaia registry is a static GitHub repository. We do not operate any backend server, database, or analytics service. The public website (`gaia.tiongson.co`) is a static site hosted on GitHub Pages and does not set tracking cookies or collect telemetry.

---

## Changes

This notice lives in `PRIVACY.md` at the root of the repository. Any changes will be recorded in the git history and visible to everyone.

---

*Questions? Open an issue at [github.com/gaia-research/gaia-skill-tree](https://github.com/gaia-research/gaia-skill-tree/issues).*
