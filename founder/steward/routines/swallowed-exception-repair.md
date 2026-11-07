# Routine — Swallowed-exception repair

| | |
|---|---|
| **Policy rule** | `swallowed-exception-repair` |
| **Sensor** | `code-error-handling` / Routine 3 |
| **Debt kind** | `swallowed_exception` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Worth looking on a normal scan |
| **Routine catalog** | #3 — Error, Diagnostics, and Incident Learner |
| **Decision** | `steward-swallowed-exception-route` |

---

## What it is for

Repair broad or bare exception handlers (`except:`, `except Exception:`, `except BaseException:`) that silently discard failures with trivial bodies (`pass`, `continue`, `return`, `return None`, `...`, or bare docstrings). One debt is one source file; the builder edits that file and nothing else.

## What the finding means

A `swallowed_exception` finding indicates that code caught a broad exception and discarded it without diagnostic trace or documented rationale. Silent swallowing can mask bugs, unexpected I/O errors, or type errors. Intentional best-effort degradations must be explicitly marked.

## The 3 valid fix shapes

Every repair must be confined to the except clause and its handler body:

1. **Narrowing the exception type:** Narrow from `Exception`, `BaseException`, or bare `except` to the specific exception types that the `try` block is realistically expected to encounter (e.g. `except (OSError, json.JSONDecodeError):`).
2. **Adding contextual logging:** Add safe diagnostic logging (e.g. `logger.debug(...)`, `log.warning(...)`, `sys.stderr.write(...)`) with pure, side-effect-free arguments before the terminal statement (`pass`, `continue`, `return`), explaining what failed and why while keeping the existing fallback behavior.
3. **Documenting intentional degradation (best-effort marker):** If swallowing the error is intentional and graceful fallback is desired without narrowing or logging, mark the handler with `# steward: best-effort: <reason>` on the `except` line or directly inside the handler body above the first statement, provided the handler does NOT feed authorization, budget, overwrite, or mutation decisions.

## Note on Structured Loader Migrations (PR #2376 `gaia_cli.structuredRead`)

49% of swallowed-exception handlers wrap file reads (`open`, `json.load`, `read_text`).
While PR #2376 introduced canonical readers (`readText`, `readJson`, `readYaml`, `readFrontmatter`), **refactoring `try` blocks into loader calls (shapes LS-1a and LS-1b) modifies `try` bodies and introduces new module imports**.

Because mechanical verification for `swallowed-exception-repair` strictly forbids modifying `try` bodies or adding module imports, **LS-1a and LS-1b loader replacements are NOT permitted within autonomous `swallowed-exception-repair` dispatches**.
Handlers requiring whole-function reader refactoring remain engineering tasks. Under this autonomous lane route, handlers must be repaired in-place:
1. Narrow the exception type to concrete exceptions (e.g. `except (OSError, json.JSONDecodeError):`).
2. Add safe diagnostic logging (`sys.stderr.write` or `logger.debug` with pure arguments).
3. Add a valid `# steward: best-effort: <reason>` marker on the except line or first body statement (for non-escalated contexts).

### Handler classification: lane repair vs escalation
- **Route-eligible for in-place lane repair:**
  - Files where handlers can be safely narrowed or logged in-place without altering `try` bodies:
    `scripts/environment/smoke.py:86`, `src/gaia_cli/localContext.py:105, 159, 206, 483`, `src/gaia_cli/treeManager.py:170, 616`, `doctor.py:46, 246`, `migrateTrustMagnitude.py:71`, `curation/evaluation.py:213`, `graph.py:402`, `impl.py:1814, 1855`, `install.py:649`, `trustFreshness.py:864`, `scanner.py:171`.
- **Escalate (never repaired by autonomous lane):**
  - **ESC-AUTH** (authority inputs): `src/gaia_cli/authz.py:55, 76`, `src/gaia_cli/commands/dev/helpers.py:726` (F5 pending).
  - **ESC-MUT** (lookups in mutating `gaia dev` verbs): `src/gaia_cli/commands/dev/calibrate.py:113, 161`, `src/gaia_cli/commands/dev/helpers.py:1424`, `src/gaia_cli/commands/dev/timeline.py:21, 43`.
  - **ESC-OVW** (feeds later file overwrite): `src/gaia_cli/impl.py:1023, 1689`, `src/gaia_cli/install.py:68`.
  - **ENG** (published artifacts, CI validators): `build_docs.py:1094, 1143, 1225`, `generateLeaderboardData.py:80`, `syncDocsGraphAssets.py:126`, `trust_appraise.py:235, 249`, `validate.py:699`, `validate_skills.py:138`, `resolver.py:19`, `push.py:277`, `challenge_watch.py:1224`, `add_post.py:439`, `scanner.py:81`, `trustFreshness.py:389`.

## Mandatory triage: security, budget, overwrite, and mutation boundaries

The swallowed-exception route preserves control flow, so a best-effort marker or fallback **must never be used to manufacture a resolution for a defect**.

Handlers that feed:
1. **Authorization and access control:** (e.g. `src/gaia_cli/authz.py:55` `_registry_has_any_verifier`, where swallowing errors fails open into bootstrap mode).
2. **Budget and spend recording:** (e.g. `src/gaia_cli/jev.py:838` `_recordSpend`, where silent errors leave spend unrecorded).
3. **File overwrite and manifest state:** (e.g. `src/gaia_cli/install.py:68` `load_manifest`, where treating corrupt manifests as empty causes total overwrite on save).
4. **Mutation decisions:** (e.g. lookup loops in `calibrate.py` or `timeline.py`).

**Such handlers are ESCALATED to engineering and are NOT dispatchable.**
Mechanical verification (`exceptionproof.py`) strictly rejects any attempt to resolve these handlers with `# steward: best-effort`. Authz behavior must not be changed autonomously (founder decision F5 pending).

## What is strictly forbidden

1. **Altering the `try` body:** The body of every `try` block must remain strictly identical in AST structure.
2. **Changing control flow or return values:**
   - If the handler had `return <val>`, that exact return value must be preserved.
   - If the handler had `continue`, it must not be replaced with `pass` or `break`.
   - If the handler had `break`, it must not be replaced with `pass` or `continue`.
   - If the handler had `pass`, it must not introduce `raise`, `return`, `continue`, or `break`.
3. **Introducing new `raise` statements:** The handler must not introduce new unhandled exceptions.
4. **Editing code outside except handlers:** Any edits outside `ast.ExceptHandler` nodes are forbidden and rejected by mechanical AST verification.
5. **Touching other files:** The diff must touch strictly the subject file.

## Stop conditions

1. The diff touches any file other than the debt's subject file.
2. The diff modifies lines outside except clauses, their comments, or handler logging.
3. The change alters control flow, return values, loop continuation, or raises new unhandled exceptions.
4. Syntax checking or compilation of the subject file fails (`python -m py_compile <file>`).
5. Focused tests for the subject file fail or regress (`python -m pytest`).
6. The finding does not reproduce on the current head.
7. The finding count for the subject file does not decrease.

## Proof and verification

Mechanical verification via `prove_exception_edit` in `src/gaia_cli/steward/exceptionproof.py` verifies AST preservation and handler constraints.
The builder must provide:
1. Reproduction of the `swallowed_exception` finding on the subject file.
2. A diff confined to the subject file modifying only except clauses, handler logging, or intent markers.
3. Clean compilation via `python -m py_compile <file>`.
4. Passing focused pytest tests for the package or script.
5. Scan proof via `gaia steward scan` showing the finding count for the subject file is reduced.
6. Independent review before integration.
