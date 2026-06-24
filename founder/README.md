# Founder Orchestrator

Three ways to launch Marcus's personal orchestrator persona in Claude Code.
The orchestrator plans and delegates — it never writes code itself.

---

## Approach 1 — Standalone (clean slate)

```bash
alias founder='claude --system-prompt-file ~/gaia-skill-tree/founder/ORCHESTRATOR.md'
```

**What it does:** Replaces the default system prompt entirely with `founder/ORCHESTRATOR.md`.
No BASE harness, no repo CLAUDE.md — just the stripped orchestrator persona.

**Use when:** Long strategic sessions where you want maximum signal-to-noise.
The BASE harness rules (recipes, /start, /stop, MCP scaffolding) are NOT active here.

---

## Approach 2 — Layered (recommended daily driver)

```bash
alias founder='claude --append-system-prompt-file ~/gaia-skill-tree/founder/FOUNDER_APPEND.md'
```

**What it does:** Appends `founder/FOUNDER_APPEND.md` on top of the existing BASE harness
and repo CLAUDE.md. All existing project context, skills, and rules stay active.

**Use when:** Day-to-day orchestration where you still want /start, /stop, /sync,
gaia-* skills, branch rules, and SAP environment reminders in play.

---

## Approach 3 — Native agent

```bash
alias founder-agent='claude --agent founder'
```

**What it does:** Loads `.claude/agents/founder.md` as a named Claude Code agent.
Tool-gated: Write/Edit are omitted from the agent's tool list, so the no-code rule
is enforced at the harness level, not just by instruction.

**Use when:** You want the no-code constraint to be structurally enforced, or you want
to invoke the founder persona as a callable subagent from within another session
(`Agent(subagent_type: "founder")`).

---

## Shell alias setup (Git Bash on Windows)

Add to `~/.bashrc`:

```bash
# === Founder Orchestrator aliases ===

# Approach 1: stripped standalone (no BASE harness)
alias founder-clean='claude --system-prompt-file ~/gaia-skill-tree/founder/ORCHESTRATOR.md'

# Approach 2: layered on top of BASE harness (recommended)
alias founder='claude --append-system-prompt-file ~/gaia-skill-tree/founder/FOUNDER_APPEND.md'

# Approach 3: native agent (tool-gated no-code enforcement)
alias founder-agent='claude --agent founder'
```

Ensure `~/.bash_profile` sources `~/.bashrc` (Git Bash on Windows sometimes uses
`.bash_profile` as the login entrypoint):

```bash
# In ~/.bash_profile — add if not already present:
[ -f ~/.bashrc ] && source ~/.bashrc
```

Reload: `source ~/.bashrc`

---

## Files

| File | Role |
|---|---|
| `founder/ORCHESTRATOR.md` | Full standalone system prompt (Approach 1) |
| `founder/FOUNDER_APPEND.md` | Append layer for Approach 2 |
| `.claude/agents/founder.md` | Native agent definition (Approach 3) |
| `founder/CLAUDE.md` | Orchestrator workspace rules (always active in the repo) |
| `founder/MEMORY.md` | Orchestrator session memory |

---

## Tradeoffs at a glance

| | Standalone | Layered | Native agent |
|---|---|---|---|
| BASE harness active | No | Yes | Depends on launch |
| No-code enforced by | Instruction | Instruction | Tool gating |
| Callable as subagent | No | No | Yes |
| Best for | Pure strategy sessions | Daily driver | Structural enforcement |
