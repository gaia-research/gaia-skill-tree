---
name: pr-easy-wins
description: "Scan PR comments for reported bugs, triage by fix complexity, implement the easiest ones first (CSS, 1-3 line JS, sed across files), Playwright-verify each fix on a local server, commit+push to the PR branch, and post a one-line comment per fix on the PR. Use when asked to find easy wins or quick fixes from a PR's review comments."
argument-hint: "[PR number]"
user-invocable: true
---

Reads a PR's issue list from comments, ranks by effort, ships the easiest fixes with browser verification.

## Workflow

### 1. Read the PR comments

```
mcp__github__pull_request_read method=get_comments owner=<owner> repo=<repo> pullNumber=<N>
```

Extract every 🔴/🟡 item. Categorise by effort:
- **Easy** (< 30 min): 1-5 line CSS or JS changes, sed across files, label/text renames
- **Medium**: logic rewrites, new UI states, multi-file coordination
- **Hard**: architectural changes, missing data, new pages

Work **easy first**, skip hard ones.

### 2. Explore before touching

For each easy fix, read the exact file and line before editing. Never guess line numbers.

```bash
grep -n "<symptom>" docs/js/<file>.js
```

Use parallel Explore agents for independent lookups.

### 3. Fix

Make the minimal change. Prefer:
- `Edit` tool for single-file patches
- `python3 -c "..."` for multi-file replacements (safer than sed with special chars)

### 4. Playwright-verify every fix

Start a local server:
```bash
python3 -m http.server 8766 --directory docs &
```

Then for each fix, write a targeted assertion:
```python
from playwright.sync_api import sync_playwright
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    page = browser.new_page()
    page.set_viewport_size({'width': 1440, 'height': 900})
    page.goto('http://localhost:8766/u/ruvnet/')
    # assert the fix
    browser.close()
```

If PASS → proceed. If FAIL → fix before committing.

### 5. Commit and push

```bash
git add <changed files>
git commit -m "fix(<scope>): <summary of all easy wins>"
git push -u origin <pr-branch>
```

### 6. Comment on the PR

One comment listing each fix as a one-liner:

```
mcp__github__add_issue_comment issue_number=<N> body="<list>"
```

Format:
```
- footer version bump v3.9.2 → v3.25.2 (index.html:397)
- back-button footgun guarded with history.length>1 (40 profile pages)
- ...
```

## Triage cheatsheet

| Symptom | Likely file | Typical fix |
|---------|-------------|-------------|
| Wrong version in footer | docs/index.html | grep for old version, replace |
| back() sends to about:blank | docs/u/*/index.html | guard history.length > 1 |
| .join() TypeError on tags | docs/js/named-skills.js | Array.isArray guard |
| Hardcoded hex colors in JS | docs/js/profile-timeline.js | getComputedStyle + CSS var |
| Font 404 in network | docs/css/styles.css | remove url() keep local() |
| Misleading button label | docs/js/*.js HTML | text node rename |
| Silent empty grid | docs/js/profile-filter.js | inject empty-state p element |
| Sidebar invisible desktop | docs/css/plaque.css | @media min-width: right:0 |

## Notes

- Verify with Playwright at 1440×900 (desktop) AND 375×812 (mobile) for layout fixes
- Kill the local server after tests: `kill $(lsof -ti:8766)`
- Never skip the Playwright step — "looks right in code" is not the same as "renders correctly"
- Post fixes in the same branch the PR is tracking (check `git branch`)
