# Handover — installing Skill Heaven and Skill Hell

**2026-08-08.** Everything below was run end to end before being written down. Where a
path does not work, that is stated rather than smoothed over.

Both products are a **working prototype, actively tested for public use**. Interfaces,
flags, and command surfaces may change.

---

## 1. Install everything — one command (recommended)

```sh
curl -fsSL https://gaia-research.github.io/skill-heaven/install.sh | sh
```

Installs the five launcher doors, the Claude plugin (`/skill-heaven` and `/skill-hell`),
and the `skill-hell` summon engine. Then add the bin directory to your PATH — the
installer deliberately does **not** edit your shell rc files:

```sh
export PATH="$HOME/.local/share/skill-heaven/bin:$PATH"
```

Verify:

```sh
claude-heaven --print     # → posture=product-floor, command=claude, skills=0
pi-heaven --print
codex-heaven --print
hermes-heaven --print
grok-heaven --print
skill-hell summon "code review" --card
```

Re-run the same one-liner to update; it is idempotent. Uninstall with
`~/.local/share/skill-heaven/uninstall.sh`.

**It never installs a harness.** Each door execs your own `claude` / `pi` / `codex` /
`hermes` / `grok`, and the installer prints which ones it detected.

---

## 2. npx — works for the summon engine, not for the doors

### What works

`@gaia-research/mcp` is published (0.3.0) and ships the `skill-hell` binary, so no install
is needed to summon:

```sh
npx -y -p @gaia-research/mcp skill-hell summon "code review" --card
npx -y -p @gaia-research/mcp skill-hell sessions
npx -y -p @gaia-research/mcp gaia-mcp          # the MCP server
```

Verified: the command above summoned `garrytan/qa` (3★, TM 63.73) in 3.4s cold, with path
and inspect link.

### Coming: `npx skill-hell` (one founder step away)

The name `skill-hell` is **free on npm**, and a pointer package claiming it is merged to
`gaia-research/gaia-mcp` main. Once published, the obvious command works:

```sh
npx skill-hell summon "code review" --card
```

It ships no code — one pinned dependency and a README. npm links the engine's own binary on
install, so npx reaches the real thing directly. Verified from a packed tarball in a clean
directory before merging.

**It is not published yet, and that step is yours**: npm trusted publishing is configured
per package, and a package that does not exist has no publisher to trust. One manual
`npm publish --access public` from `alias/skill-hell/`, then point the trusted publisher at
this repo's `release.yml` / `npm` environment. Full steps: `alias/skill-hell/PUBLISHING.md`.

Claiming the name has value beyond ergonomics — it is a product name you said you intend to
keep.

### The flag that matters

**`-p` is required, and `npx @gaia-research/mcp` alone fails:**

```
$ npx -y @gaia-research/mcp
npm error could not determine executable to run
```

The package ships **two** binaries — `gaia-mcp` and `skill-hell` — and neither is named
after the package, so npx cannot choose. Use `-p <package> <binary>`. This is not a bug to
route around; it is how npx behaves for any multi-bin package.

Pin the version when it matters: `npx -y -p @gaia-research/mcp@0.3.0 skill-hell …`

**Note:** `skill-hell --help` prints correct usage but exits 1 with `Unknown command:
--help`. Cosmetic; the usage text is right. Fix belongs in `gaia-research/gaia-mcp`.

### What does NOT work

**There is no npx path for the five doors.** `npx claude-heaven`, `npx pi-heaven` and the
rest will fail: those packages are **not published to npm**. They carry `0.1.0` version
numbers and are packaging-ready, but publishing them has not happened.

Do not put an `npx <door>` line in any public doc until that changes — it would be a
broken instruction on a page whose whole point is that installing should be easy.

Until then, use the one-liner in §1, or a source checkout:

```sh
git clone https://github.com/gaia-research/skill-heaven
cd skill-heaven && npm install
node packages/claude-heaven/bin/claude-heaven.mjs --print
```

---

## 3. Claude plugin only

If you want just `/skill-heaven` and `/skill-hell` inside Claude Code:

```sh
claude plugin marketplace add gaia-research/skill-heaven
claude plugin install claude-heaven@skill-heaven
npm install -g @gaia-research/mcp@^0.3.0     # /skill-hell needs the engine
```

The `@skill-heaven` suffix is the marketplace qualifier and is required.

`0.1.0` shipped **no** `skill-hell` binary at all, which is why the version floor is not
cosmetic — on `0.1.0`, `/skill-hell` cannot work for anyone.

---

## 4. Where things live

| Thing | Where |
|---|---|
| Landing page | https://gaia-research.github.io/skill-heaven/ |
| Installer script | https://gaia-research.github.io/skill-heaven/install.sh |
| Product monorepo | `gaia-research/skill-heaven` — `main` |
| Summon engine | `gaia-research/gaia-mcp` — npm `@gaia-research/mcp` |
| Install dir | `~/.local/share/skill-heaven/` |
| Session roots | OS temp, `skill-hell-*` — never your repo, never `~/.claude` |

No custom domain yet; the Pages URL is the address for now.

---

## 5. Known gaps

- **Windows is untested.** No `iex` variant ships. Writing one without being able to run it
  would be worse than shipping none. Tracked by `gaia-research/skill-heaven#41`.
- **The doors are unpublished**, so npx covers the engine only (§2).
- **`skill-hell --help` exits 1** while printing correct usage.
- Benchmarks and ranking tuning are deliberately not done — they belong to the Hell Heaven
  Index, not to the prototype.
