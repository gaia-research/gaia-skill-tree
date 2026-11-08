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

### Handler classification: a positive envelope, not a denylist

A handler is route-eligible only when **all** of these are proven, mechanically, by
`handler_escalation_reason` in `src/gaia_cli/steward/exceptionproof.py` (used both at
dispatch and in verification). Anything not proven escalates to engineering.

1. **The `try` body, and its `else` and `finally` clauses, are side-effect-free or
   diagnostic-only.** Allowed: `pass`, docstrings, optional imports, assignment to plain
   local names, `return` and `if` over pure expressions, and trusted logging. A pure
   expression is a constant, name, attribute or item read, operator, comparison, f-string,
   literal container, or a call to:
   - a conversion/read builtin (`int`, `float`, `str`, `len`, `getattr`, `isinstance`, ...);
     builtins that iterate an arbitrary object (`list`, `sorted`, `sum`, `any`, ...) are not;
   - `json.loads`/`json.dumps`, `yaml.safe_load`, or a `re` function, via a trusted
     module-scope import;
   - a read-only method on a value whose type is proven: a `str`, a JSON value (the output
     of `json.loads`/`yaml.safe_load` and its items), or a `re` match. A method on a value
     of unknown type (`session.get(url)`, `requests.get`, `raw.get`) is never classified.
   Writes, network, subprocess, `with`/loops, attribute or item stores, `global`/`nonlocal`
   assignment and any call whose effect cannot be classified are unproven.
2. **No value the `try` binds reaches a mutation or decision** elsewhere in its scope: an
   unclassified call, an attribute or item store, or the test of a branch that performs
   an unclassified call. The swallowed default must not feed a write or a gate.
3. **The context is not a known authorization, budget or overwrite boundary**
   (`is_escalated_try_block` / `is_escalated_security_context`). This list is an extra
   layer of defence, never the safety argument.

As measured on 2026-11-08, **none** of the 88 open swallowed handlers in 41 files meets
the envelope (most `try` bodies read files with `with open(...)`, iterate, or call helpers
whose effect cannot be classified). The route is deliberately inert for them until the
envelope is widened by a proven, independently reviewed rule. It never resolves a handler
by marking it.

### Proving a narrowing and trusting a name

- **Narrowing** is proven against the real class hierarchy (bare `except` is
  `BaseException`): every new class must be a subclass of an old one, and the new set must
  catch strictly less. `except Exception` -> `except KeyboardInterrupt` is refused.
- **Names** (`logger`, `sys`, builtin exception names) are trusted only after every lexical
  binding form in scope is analysed: all argument kinds (positional-only included), local
  imports, tuple/starred unpacking, `for`/`with`/walrus/`except as`/`match` targets, nested
  definitions, and module-scope rebinding or `global` declarations anywhere in the module.
  A name bound more than once, or bound by an untrusted form, is untrusted.

## Mandatory triage: security, budget, overwrite, and mutation boundaries

The swallowed-exception route preserves control flow, so a best-effort marker or fallback
**must never be used to manufacture a resolution for a defect**. Handlers that feed
authorization, budget/spend recording, file overwrite or mutation decisions are
**escalated** and not dispatchable: the positive envelope above refuses them (their `try`
bodies perform or feed effects), and the known-context list refuses the recorded cases
(`authz.py`, `jev.py` `_recordSpend`, `install.py` `load_manifest`, the mutating `gaia dev`
verbs). Authz behavior must not be changed autonomously (founder decision F5 pending).

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
8. The handler's `try` body (or its `else`/`finally`) is not proven side-effect-free under the
   positive envelope, or a value it binds reaches a write, an unclassified call or a decision
   guard: escalate to engineering.

## Proof and verification

Mechanical verification via `prove_exception_edit` in `src/gaia_cli/steward/exceptionproof.py` verifies AST preservation and handler constraints.
The builder must provide:
1. Reproduction of the `swallowed_exception` finding on the subject file.
2. A diff confined to the subject file modifying only except clauses, handler logging, or intent markers.
3. Clean compilation via `python -m py_compile <file>`.
4. Passing focused pytest tests for the package or script.
5. Scan proof via `gaia steward scan` showing the finding count for the subject file is reduced.
6. For a narrowed handler, a focused test that raises the expected error through the `try`
   and shows it is still handled (preserved error-handling semantics).
7. Independent review before integration.
