"""gaia_cli.jevAdvisory — Read-only Jev advisory sidecar adapters and runner.

Evaluates candidates, issues, upstream releases, evidence rows, generic nodes,
and steward debts against TypeSafe System One (Jev) choice primitives.
Emits read-only sidecar reports with full fallback visibility to worker-luna.
Never mutates the registry, schemas, decisions, prefill, or steward authority.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from gaia_cli.jev import JevClient

REPORT_SCHEMA_VERSION = "jev-advisory-report-v1"
PINNED_MODEL = "jev-1.13.0"
CONFIDENCE_THRESHOLD = 0.75
MAX_REQUEST_BYTES = 12000
MAX_ITEMS_PER_RUN = 50
MAX_COLLECT_ITEMS = 20
MAX_INPUT_FILE_BYTES = 2_000_000  # ~2MB bounded read
SUPPORTED_MODES = frozenset({"mapping", "issues", "upstream", "evidence", "meta", "steward"})
EXHAUSTION_REASONS = frozenset({"budget_exceeded", "max_calls_exceeded", "limit_reached"})

_STOPWORDS = frozenset({
    "and", "the", "for", "with", "that", "this", "from", "are", "which",
    "can", "has", "have", "not", "use", "used", "uses", "into", "all",
    "skill", "skills", "agent", "agents", "tool", "tools", "via", "over",
    "such", "when", "what", "how", "each", "other", "than", "then",
    "in", "on", "at", "to", "of", "by", "is", "it", "as", "be", "an", "a",
})

_PROTECTED_DIR_PREFIXES = (
    ("registry",),
    ("registry-for-review",),
    (".gaia", "steward"),
    ("src",),
    ("scripts",),
    ("tests",),
    ("docs",),
    (".agents",),
    (".github",),
    (".git",),
)

_PROTECTED_ROOT_FILES = frozenset({
    "named-skills.json",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE",
})


def _get_repo_root() -> str:
    return str(Path(__file__).resolve().parent.parent.parent)


def is_canonical_registry_path(path: str, repo_root: str | None = None) -> bool:
    """Return True if path points inside canonical registry directory or protected source roots."""
    if not path:
        return False
    if repo_root is None:
        repo_root = _get_repo_root()
    try:
        abs_root = os.path.realpath(os.path.abspath(repo_root))
        abs_path = os.path.abspath(path)
        real_path = os.path.realpath(abs_path)

        for check_path in (abs_path, real_path):
            try:
                rel = os.path.relpath(check_path, abs_root)
            except ValueError:
                continue
            if rel.startswith("..") or rel == ".":
                continue
            parts = rel.split(os.sep)
            if parts[0] in _PROTECTED_ROOT_FILES and len(parts) == 1:
                return True
            for prefix in _PROTECTED_DIR_PREFIXES:
                if len(parts) >= len(prefix) and tuple(parts[: len(prefix)]) == prefix:
                    return True
    except Exception:
        pass
    return False


def validate_paths(
    input_path: str | None,
    output_path: str | None,
    repo_root: str | None = None,
    state_dir: str | None = None,
) -> None:
    """Validate that input, output, and state paths are safe, distinct, and non-canonical."""
    if repo_root is None:
        repo_root = _get_repo_root()
    abs_root = os.path.realpath(os.path.abspath(repo_root))

    real_in = os.path.realpath(os.path.abspath(input_path)) if input_path else None
    real_out = os.path.realpath(os.path.abspath(output_path)) if output_path else None

    # Symlink check on output_path and existing parents
    if output_path:
        if os.path.islink(output_path):
            raise ValueError(f"Output path cannot be a symlink: {output_path}")
        p = Path(output_path).parent
        while str(p) not in (".", "/", ""):
            if p.is_symlink():
                raise ValueError(f"Output path parent cannot be a symlink: {output_path}")
            p = p.parent

    # Input and output distinct (including realpath aliases)
    if input_path and output_path:
        if os.path.abspath(input_path) == os.path.abspath(output_path) or real_in == real_out:
            raise ValueError(f"Input and output path must not be the same: {input_path}")

    # Output cannot be canonical or in protected roots
    if output_path:
        if is_canonical_registry_path(output_path, repo_root) or (real_out and is_canonical_registry_path(real_out, repo_root)):
            raise ValueError(f"Output path cannot be a canonical registry path: {output_path}")

        # Check if inside repo_root: output must be in generated-output or allowed scratch
        if real_out and (real_out == abs_root or real_out.startswith(abs_root + os.sep)):
            rel_out = os.path.relpath(real_out, abs_root)
            out_parts = rel_out.split(os.sep)
            if out_parts[0] not in ("generated-output", ".gaia"):
                raise ValueError(f"Output path must be under generated-output or scratch, got: {output_path}")
            if out_parts[0] == ".gaia" and len(out_parts) > 1 and out_parts[1] == "steward":
                raise ValueError(f"Output path cannot be inside .gaia/steward: {output_path}")

    # State directory validation
    if state_dir:
        if os.path.islink(state_dir):
            raise ValueError(f"State directory cannot be a symlink: {state_dir}")
        abs_state = os.path.abspath(state_dir)
        real_state = os.path.realpath(abs_state)
        if is_canonical_registry_path(state_dir, repo_root) or is_canonical_registry_path(real_state, repo_root):
            raise ValueError(f"State directory cannot be inside canonical registry or protected root: {state_dir}")

        if real_state == abs_root or real_state.startswith(abs_root + os.sep):
            rel_state = os.path.relpath(real_state, abs_root)
            state_parts = rel_state.split(os.sep)
            if state_parts[0] not in (".gaia", "generated-output") or (state_parts[0] == ".gaia" and len(state_parts) > 1 and state_parts[1] == "steward"):
                raise ValueError(f"State directory inside repo must be in ignored scratch directory: {state_dir}")

        # Guard state ledger/cache files against colliding with input or output
        for fname in ("cache.json", "budget.json", "jev.lock"):
            sf = os.path.realpath(os.path.join(abs_state, fname))
            if real_in and sf == real_in:
                raise ValueError(f"Input path cannot be the state directory file: {input_path}")
            if real_out and sf == real_out:
                raise ValueError(f"Output path cannot be the state directory file: {output_path}")


def load_generic_nodes(repo_root: str | None = None) -> dict[str, dict[str, Any]]:
    """Load generic capability nodes from registry/nodes/{basic,fusion}/."""
    if repo_root is None:
        repo_root = _get_repo_root()
    nodes_dir = os.path.join(repo_root, "registry", "nodes")
    generics: dict[str, dict[str, Any]] = {}
    if not os.path.isdir(nodes_dir):
        return generics

    for sub in ("basic", "fusion"):
        sub_dir = os.path.join(nodes_dir, sub)
        if not os.path.isdir(sub_dir):
            continue
        for fname in sorted(os.listdir(sub_dir)):
            if fname.endswith(".json"):
                fpath = os.path.join(sub_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    gid = data.get("id")
                    if gid:
                        generics[gid] = {
                            "id": gid,
                            "name": data.get("name", gid),
                            "description": str(data.get("description", ""))[:500],
                            "summary": str(data.get("summary", ""))[:300],
                            "type": data.get("type", sub),
                        }
                except (OSError, json.JSONDecodeError):
                    continue
    return generics


def _tokenize(text: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return words - _STOPWORDS


def lexical_shortlist(
    name: str,
    description: str,
    generic_nodes: Mapping[str, Mapping[str, Any]],
    limit: int = 3,
) -> list[str]:
    """Deterministically rank generic capabilities by token overlap.

    Returns up to `limit` generic IDs sorted by descending match score,
    breaking ties alphabetically.
    """
    cand_tokens = _tokenize(f"{name} {description}")
    if not cand_tokens:
        return []

    scored: list[tuple[int, str]] = []
    for gid, gdata in generic_nodes.items():
        name_tokens = _tokenize(str(gdata.get("name", "")))
        desc_tokens = _tokenize(f"{gdata.get('description', '')} {gdata.get('summary', '')}")
        name_overlap = len(cand_tokens & name_tokens)
        desc_overlap = len(cand_tokens & desc_tokens)
        total_score = name_overlap * 3 + desc_overlap
        if total_score > 0:
            scored.append((total_score, gid))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [gid for _, gid in scored[:limit]]


def rank_duplicate_issue_candidates(
    current_issue: dict[str, Any],
    all_issues: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank duplicate issue candidates by lexical title and body overlap with bounded excerpts."""
    cur_num = current_issue.get("number", 0)
    cur_title = str(current_issue.get("title", ""))
    cur_body = str(current_issue.get("body", ""))
    cur_title_tokens = _tokenize(cur_title)
    cur_body_tokens = _tokenize(cur_body)
    cur_tokens = cur_title_tokens | cur_body_tokens

    if not cur_tokens:
        return []

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for other in all_issues:
        other_num = other.get("number", 0)
        if other_num == cur_num:
            continue
        other_title = str(other.get("title", ""))
        other_body = str(other.get("body", ""))
        other_title_tokens = _tokenize(other_title)
        other_body_tokens = _tokenize(other_body)

        title_overlap = len(cur_title_tokens & other_title_tokens)
        body_overlap = len(cur_tokens & (other_title_tokens | other_body_tokens))
        score = title_overlap * 3 + body_overlap
        if score > 0:
            excerpt = other_body.strip().replace("\n", " ")[:120]
            scored.append((score, other_num, {
                "number": other_num,
                "title": other_title[:100],
                "excerpt": excerpt,
                "score": score,
            }))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, _, c in scored[:limit]]


def handle_evaluation_result(
    base_result: dict[str, Any],
    eval_res: dict[str, Any],
    state: dict[str, Any],
    questions: dict[str, Any],
    primary_question_key: str,
    result_field_name: str,
    *,
    shortlist: list[str] | None = None,
    uncertain_choices: frozenset[str] = frozenset({"UNCERTAIN", "uncertain"}),
    recommendation_builder: Callable[[str, float], str] | None = None,
    luna_instruction_builder: Callable[[str, float, str], str] | None = None,
    extra_advisory_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Uniformly handle Jev client evaluation response across all 6 modes.

    Enforces CONFIDENCE_THRESHOLD (0.75) and UNCERTAIN choice checks, attaching
    allowlisted bounded context and questions to fallback records. Unused questions
    do not gate.
    """
    usage = eval_res.get("usage", {})
    est_cost = float(eval_res.get("estimatedCostUsd", 0.0))
    reserved = float(eval_res.get("reservedUsd", 0.0))
    cached = bool(eval_res.get("cached", False))

    if eval_res.get("status") == "fallback":
        reason = str(eval_res.get("reason", "client_fallback"))
        inst = eval_res.get("fallback", {}).get("instruction") or f"Evaluation fell back with reason: {reason}."
        fb_data: dict[str, Any] = {
            "agent": "worker-luna",
            "instruction": inst,
            "context": state,
            "questions": questions,
        }
        if shortlist is not None:
            fb_data["shortlist"] = shortlist

        base_result.update({
            "status": "fallback",
            "reason": reason,
            "advisoryResult": None,
            "fallback": fb_data,
            "usage": usage,
            "estimatedCostUsd": est_cost,
            "reservedUsd": reserved,
            "cached": cached,
        })
        return base_result

    answers = eval_res.get("answers", {})
    ans = answers.get(primary_question_key, {})
    choice = ans.get("choice")
    confidence = float(ans.get("confidence", 0.0))
    probabilities = ans.get("probabilities", {})

    is_uncertain = (choice in uncertain_choices) or (choice is None)
    is_low_conf = (confidence < CONFIDENCE_THRESHOLD)

    if is_uncertain or is_low_conf:
        if choice in ("NONE_OF_SHORTLIST", "none_of_shortlist"):
            reason = "none_of_shortlist"
        elif is_uncertain:
            reason = str(choice).lower() if choice else "uncertain"
        else:
            reason = "low_confidence"

        if luna_instruction_builder is not None:
            inst = luna_instruction_builder(choice or "NONE", confidence, reason)
        else:
            inst = (
                f"Advisory evaluation for '{primary_question_key}' returned '{choice}' "
                f"(confidence: {confidence:.2f}, threshold: {CONFIDENCE_THRESHOLD}). "
                f"Worker Luna review or manual triage required."
            )

        fb_data = {
            "agent": "worker-luna",
            "instruction": inst,
            "context": state,
            "questions": questions,
        }
        if shortlist is not None:
            fb_data["shortlist"] = shortlist

        advisory_data: dict[str, Any] = {
            result_field_name: choice,
            "confidence": confidence,
            "probabilities": probabilities,
            "recommendation": (
                "worker-luna-new-generic" if choice == "NONE_OF_SHORTLIST" else "worker-luna-review"
            ),
        }
        if extra_advisory_fields:
            advisory_data.update(extra_advisory_fields)

        base_result.update({
            "status": "fallback",
            "reason": reason,
            "advisoryResult": advisory_data,
            "fallback": fb_data,
            "usage": usage,
            "estimatedCostUsd": est_cost,
            "reservedUsd": reserved,
            "cached": cached,
        })
        return base_result

    # Status: advisory OK
    advisory_data = {
        result_field_name: choice,
        "confidence": confidence,
        "probabilities": probabilities,
    }
    if recommendation_builder is not None:
        advisory_data["recommendation"] = recommendation_builder(choice, confidence)
    if extra_advisory_fields:
        advisory_data.update(extra_advisory_fields)

    base_result.update({
        "status": "advisory",
        "reason": "ok",
        "advisoryResult": advisory_data,
        "fallback": None,
        "usage": usage,
        "estimatedCostUsd": est_cost,
        "reservedUsd": reserved,
        "cached": cached,
    })
    return base_result


def _dispatch_evaluate(
    client: Any,
    state: dict[str, Any],
    questions: dict[str, Any],
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Call client.evaluate or synthesize fallback when limits are already exhausted."""
    if exhaustion_reason is not None:
        return {
            "status": "fallback",
            "reason": exhaustion_reason,
            "answers": {},
            "model": PINNED_MODEL,
            "cached": False,
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
            "fallback": {
                "agent": "worker-luna",
                "instruction": f"Evaluation fell back due to earlier {exhaustion_reason}. Preserved row requires offline maintainer or Luna triage.",
            },
        }
    return client.evaluate(state, questions)


def evaluate_mapping_item(
    item: dict[str, Any],
    client: Any,
    generic_nodes: Mapping[str, Mapping[str, Any]],
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Evaluate one candidate skill mapping against generic capabilities.

    Advisory only; never modifies input, genericSnapshot, matchTier, or decision.
    Uses frozen descriptions from genericSnapshot.generics if available.
    If mappingOptions == [] -> no paid call, handoff Luna to check broader registry and draft generic only if needed.
    Duplicated, deterministically rejected, or already resolved packets do not burn calls.
    """
    candidate_id = (
        item.get("candidateId")
        or item.get("id")
        or (item.get("normalized", {}) or {}).get("name")
        or "unknown_candidate"
    )
    normalized = item.get("normalized") or {}
    source_fm = (item.get("source") or {}).get("frontmatter") or {}

    name = (
        normalized.get("name")
        or source_fm.get("name")
        or item.get("name")
        or candidate_id
    )
    description = (
        normalized.get("description")
        or source_fm.get("description")
        or item.get("description")
        or ""
    )

    base_state = {
        "candidateId": str(candidate_id)[:100],
        "name": str(name)[:100],
        "description": str(description)[:1000],
    }

    # 1. Deterministic check: already duplicated
    exact_dedupe = item.get("exactDedupe")
    is_duplicate = (
        (isinstance(exact_dedupe, dict) and exact_dedupe.get("matched") is True)
        or item.get("duplicate") is True
        or item.get("deduped") is True
    )
    if is_duplicate:
        return {
            "candidateId": candidate_id,
            "name": name,
            "advisoryShortlist": [],
            "advisoryShortlistIncomplete": False,
            "status": "fallback",
            "reason": "already_duplicated",
            "advisoryResult": None,
            "fallback": {
                "agent": "worker-luna",
                "instruction": f"Candidate '{candidate_id}' is already identified as duplicate; skipping paid evaluation.",
                "context": base_state,
                "questions": {},
            },
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
        }

    # 2. Deterministic check: deterministically rejected
    artifact_gate = item.get("artifactGate")
    decision_val = (
        (item.get("decision", {}) or {}).get("value")
        if isinstance(item.get("decision"), dict)
        else item.get("decision")
    )
    is_rejected = (
        (isinstance(artifact_gate, str) and (artifact_gate.startswith("invalid") or artifact_gate.startswith("rejected")))
        or decision_val == "REJECTED"
        or item.get("rejected") is True
    )
    if is_rejected:
        return {
            "candidateId": candidate_id,
            "name": name,
            "advisoryShortlist": [],
            "advisoryShortlistIncomplete": False,
            "status": "fallback",
            "reason": "deterministically_rejected",
            "advisoryResult": None,
            "fallback": {
                "agent": "worker-luna",
                "instruction": f"Candidate '{candidate_id}' is deterministically rejected (artifactGate={artifact_gate}); skipping paid evaluation.",
                "context": base_state,
                "questions": {},
            },
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
        }

    # 3. Deterministic check: already resolved
    if decision_val and str(decision_val).upper() not in ("PENDING", "REVIEW_READY", "REVIEW-READY"):
        return {
            "candidateId": candidate_id,
            "name": name,
            "advisoryShortlist": [],
            "advisoryShortlistIncomplete": False,
            "status": "fallback",
            "reason": "already_resolved",
            "advisoryResult": None,
            "fallback": {
                "agent": "worker-luna",
                "instruction": f"Candidate '{candidate_id}' already has resolved decision '{decision_val}'; skipping paid evaluation.",
                "context": dict(base_state, decision=str(decision_val)),
                "questions": {},
            },
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
        }

    shortlist_options: list[str] = []
    shortlist_incomplete = False
    raw_mapping_options = item.get("mappingOptions")

    if isinstance(raw_mapping_options, list):
        if len(raw_mapping_options) == 0:
            # Supplied empty mappingOptions -> no paid lexical fallback!
            return {
                "candidateId": candidate_id,
                "name": name,
                "advisoryShortlist": [],
                "advisoryShortlistIncomplete": False,
                "status": "fallback",
                "reason": "no_shortlist_options",
                "advisoryResult": None,
                "fallback": {
                    "agent": "worker-luna",
                    "instruction": (
                        f"No generic capabilities shortlisted for '{candidate_id}'. "
                        f"Worker Luna should research candidate capability in broader registry and propose a new generic capability draft only if needed."
                    ),
                    "context": base_state,
                    "questions": {},
                    "shortlist": [],
                },
                "usage": {},
                "estimatedCostUsd": 0.0,
                "reservedUsd": 0.0,
            }
        for opt in raw_mapping_options[:3]:
            if isinstance(opt, dict) and opt.get("genericId"):
                shortlist_options.append(str(opt["genericId"]))
            elif isinstance(opt, str):
                shortlist_options.append(opt)
    else:
        # Raw intake lacking options: deterministically compute lexical shortlist
        shortlist_options = lexical_shortlist(str(name), str(description), generic_nodes, limit=3)
        shortlist_incomplete = True

    base_result: dict[str, Any] = {
        "candidateId": candidate_id,
        "name": name,
        "advisoryShortlist": shortlist_options,
        "advisoryShortlistIncomplete": shortlist_incomplete,
    }

    if not shortlist_options:
        base_result.update({
            "status": "fallback",
            "reason": "no_shortlist_options",
            "advisoryResult": None,
            "fallback": {
                "agent": "worker-luna",
                "instruction": (
                    f"No generic capabilities shortlisted for '{candidate_id}'. "
                    f"Worker Luna should research candidate capability in broader registry and propose a new generic capability draft only if needed."
                ),
                "context": base_state,
                "questions": {},
                "shortlist": [],
            },
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
        })
        return base_result

    # Build snapshot lookup from genericSnapshot.generics if available
    snapshot_generics: dict[str, dict[str, Any]] = {}
    for g in (item.get("genericSnapshot") or {}).get("generics", []):
        if isinstance(g, dict) and g.get("id"):
            snapshot_generics[str(g["id"])] = g

    opt_descriptions: dict[str, str] = {}
    if isinstance(raw_mapping_options, list):
        for opt in raw_mapping_options:
            if isinstance(opt, dict) and opt.get("genericId"):
                gid = str(opt["genericId"])
                desc = opt.get("description") or opt.get("rationale") or opt.get("name")
                if desc:
                    opt_descriptions[gid] = str(desc)

    criteria: dict[str, str] = {}
    for gid in shortlist_options:
        desc_snap = None
        g_snap = snapshot_generics.get(gid)
        if g_snap:
            desc_snap = g_snap.get("description") or g_snap.get("summary") or g_snap.get("name")

        desc_opt = opt_descriptions.get(gid)

        gdata = generic_nodes.get(gid)
        desc_reg = None
        if gdata:
            desc_reg = gdata.get("description") or gdata.get("summary") or gdata.get("name")

        final_desc = desc_snap or desc_opt or desc_reg or f"Generic capability {gid}"
        criteria[gid] = str(final_desc)[:300]

    criteria["NONE_OF_SHORTLIST"] = "None of the shortlisted generic capabilities represent this candidate skill."
    criteria["UNCERTAIN"] = "Insufficient or ambiguous evidence to determine whether any of the candidate generic capabilities fit."

    questions = {
        "generic_mapping": {
            "type": "choice",
            "instructions": f"Which generic capability best represents candidate skill '{name}' ({candidate_id})?",
            "criteria": criteria,
        }
    }

    state = {
        "candidateId": str(candidate_id)[:100],
        "name": str(name)[:100],
        "description": str(description)[:1000],
    }

    eval_res = _dispatch_evaluate(client, state, questions, exhaustion_reason)

    return handle_evaluation_result(
        base_result=base_result,
        eval_res=eval_res,
        state=state,
        questions=questions,
        primary_question_key="generic_mapping",
        result_field_name="choice",
        shortlist=shortlist_options,
        uncertain_choices=frozenset({"NONE_OF_SHORTLIST", "UNCERTAIN"}),
        recommendation_builder=lambda c, conf: f"map-to-{c}",
        luna_instruction_builder=lambda c, conf, r: (
            f"Advisory mapping returned '{c}' (confidence: {conf:.2f}). "
            f"Worker Luna should research candidate '{candidate_id}' and propose a new generic capability draft or manual resolution."
        ),
    )


def evaluate_issues_item(
    item: dict[str, Any],
    client: Any,
    all_issues: list[dict[str, Any]] | None = None,
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Evaluate one issue for priority P0-P4 and duplicate recommendation.

    Advisory only; NEVER labels or closes issues.
    Ranks duplicate candidates by lexical overlap and marks shortlist incomplete (not proof of uniqueness).
    """
    number = item.get("number", 0)
    title = str(item.get("title", ""))[:200]
    body = str(item.get("body", ""))[:1500]
    labels_raw = item.get("labels", [])

    labels: list[str] = []
    if isinstance(labels_raw, list):
        for lbl in labels_raw:
            if isinstance(lbl, dict) and "name" in lbl:
                labels.append(str(lbl["name"]))
            elif isinstance(lbl, str):
                labels.append(lbl)

    is_upstream = False
    upstream_tag = None
    for lbl in labels:
        if lbl.startswith("upstream:"):
            is_upstream = True
            upstream_tag = lbl
            break
    if not is_upstream:
        if "[upstream:" in title:
            is_upstream = True
            m = re.search(r"\[upstream:([^\]]+)\]", title)
            if m:
                upstream_tag = f"upstream:{m.group(1)}"
        elif "<!-- gaia-upstream-payload" in body:
            is_upstream = True
            upstream_tag = "upstream:release"

    candidate_dupes = rank_duplicate_issue_candidates(item, all_issues) if all_issues else []

    questions: dict[str, Any] = {
        "priority": {
            "type": "choice",
            "instructions": f"Recommend priority level P0-P4 for issue #{number}: '{title}'.",
            "criteria": {
                "P0": "Critical blocker, security incident, data corruption, broken release/main pipeline.",
                "P1": "High impact regression, broken core developer workflow, major unhandled error.",
                "P2": "Standard feature, normal bug fix, routine curation or maintenance task.",
                "P3": "Minor polish, non-blocking cosmetic improvement, minor documentation tweak.",
                "P4": "Nice-to-have suggestion, low-priority backlog item, speculative idea.",
                "UNCERTAIN": "Ambiguous or insufficient details to determine priority.",
            },
        }
    }

    if candidate_dupes:
        dup_criteria = {
            f"issue_{d['number']}": f"Issue #{d['number']}: {d['title']} (excerpt: '{d['excerpt']}')"
            for d in candidate_dupes
        }
        dup_criteria["NONE_OF_SHORTLIST"] = "This issue does not duplicate any of the shortlisted candidate issues (shortlist is lexically ranked and incomplete; not proof of uniqueness)."
        dup_criteria["UNCERTAIN"] = "Ambiguous or insufficient details to determine if this is a duplicate."
        questions["duplicate_check"] = {
            "type": "choice",
            "instructions": f"Does issue #{number} duplicate any of the shortlisted candidate issues?",
            "criteria": dup_criteria,
        }

    state = {
        "number": number,
        "title": title,
        "bodySnippet": body[:800],
        "labels": labels[:10],
        "isUpstream": is_upstream,
    }

    base_result: dict[str, Any] = {
        "number": number,
        "title": title,
        "isUpstream": is_upstream,
        "upstreamTag": upstream_tag,
        "duplicateShortlistIncomplete": True,
        "proofOfUniqueness": False,
    }

    eval_res = _dispatch_evaluate(client, state, questions, exhaustion_reason)

    answers = eval_res.get("answers", {})
    d_ans = answers.get("duplicate_check", {})
    dup_choice = d_ans.get("choice", "NONE_OF_SHORTLIST") if candidate_dupes else "NONE_OF_SHORTLIST"
    dup_conf = float(d_ans.get("confidence", 1.0)) if candidate_dupes else 1.0

    extra_fields = {
        "duplicateRecommendation": dup_choice,
        "duplicateConfidence": dup_conf,
        "duplicateCandidateCount": len(candidate_dupes),
        "duplicateCandidates": [d["number"] for d in candidate_dupes],
        "duplicateShortlistIncomplete": True,
        "proofOfUniqueness": False,
        "action": "none_read_only",
    }

    return handle_evaluation_result(
        base_result=base_result,
        eval_res=eval_res,
        state=state,
        questions=questions,
        primary_question_key="priority",
        result_field_name="priorityRecommendation",
        uncertain_choices=frozenset({"UNCERTAIN"}),
        recommendation_builder=None,
        luna_instruction_builder=lambda c, conf, r: (
            f"Issue #{number} priority triage returned '{c}' (confidence: {conf:.2f}). "
            f"Worker Luna or maintainer triage required."
        ),
        extra_advisory_fields=extra_fields,
    )


def evaluate_upstream_item(
    item: dict[str, Any],
    client: Any,
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Evaluate one upstream watcher finding for release impact.

    Advisory only; never replaces deterministic finding/liveness.
    Includes bounded deterministic facts (componentAdds/Removes/linkLiveness) and previousVersion alias.
    If source repository/URL is missing -> no paid call, fallback to Luna.
    """
    skill_id = str(item.get("skillId") or item.get("id") or "unknown_skill")
    finding_type = str(item.get("finding_type") or item.get("findingType") or "update")
    cur_ver = item.get("currentVersion") or item.get("previousVersion")
    if cur_ver in ("none", "None"):
        cur_ver = None
    new_ver = str(item.get("newVersion") or "")
    release_notes = str(item.get("releaseNotes") or item.get("notes") or "")[:2000]
    source_url = item.get("sourceUrl") or item.get("source_url") or item.get("sourceRepo") or item.get("source")

    component_adds = item.get("componentAdds") or []
    component_removes = item.get("componentRemoves") or []
    link_liveness = item.get("linkLiveness") or []

    base_result: dict[str, Any] = {
        "skillId": skill_id,
        "findingType": finding_type,
        "currentVersion": cur_ver,
        "previousVersion": cur_ver,
        "newVersion": new_ver,
        "componentAdds": component_adds,
        "componentRemoves": component_removes,
        "linkLiveness": link_liveness,
    }

    # Deterministic check: missing source -> no paid call
    has_source = bool(source_url) or ("/" in skill_id and skill_id not in ("unknown_skill", "", "none"))
    if not has_source:
        state = {
            "skillId": skill_id[:100],
            "findingType": finding_type[:50],
            "currentVersion": str(cur_ver)[:50] if cur_ver else None,
            "previousVersion": str(cur_ver)[:50] if cur_ver else None,
            "newVersion": new_ver[:50],
        }
        base_result.update({
            "status": "fallback",
            "reason": "missing_source",
            "advisoryResult": None,
            "fallback": {
                "agent": "worker-luna",
                "instruction": f"Upstream finding for '{skill_id}' is missing source URL or repository; no paid call permitted. Luna triage required.",
                "context": state,
                "questions": {},
            },
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
        })
        return base_result

    questions = {
        "release_impact": {
            "type": "choice",
            "instructions": f"Assess likely impact of upstream release {new_ver} for skill '{skill_id}' (current: {cur_ver}).",
            "criteria": {
                "breakage": "Breaking changes, removed APIs, backwards-incompatible schema or behavior changes requiring immediate repair.",
                "changed_capability": "New capabilities, features, or minor behavioural improvements that can be curated or updated.",
                "docs_only": "Documentation, comments, readme, internal chores, or packaging metadata with no runtime effect.",
                "uncertain": "Ambiguous or missing release notes; cannot determine impact.",
            },
        }
    }

    state = {
        "skillId": skill_id[:100],
        "sourceUrl": str(source_url)[:200] if source_url else None,
        "findingType": finding_type[:50],
        "currentVersion": str(cur_ver)[:50] if cur_ver else None,
        "previousVersion": str(cur_ver)[:50] if cur_ver else None,
        "newVersion": new_ver[:50],
        "componentAdds": [str(c)[:50] for c in component_adds][:20] if isinstance(component_adds, list) else [],
        "componentRemoves": [str(c)[:50] for c in component_removes][:20] if isinstance(component_removes, list) else [],
        "linkLiveness": [str(l)[:100] for l in link_liveness][:20] if isinstance(link_liveness, list) else str(link_liveness)[:200],
        "releaseNotesSnippet": release_notes[:1000],
    }

    eval_res = _dispatch_evaluate(client, state, questions, exhaustion_reason)

    return handle_evaluation_result(
        base_result=base_result,
        eval_res=eval_res,
        state=state,
        questions=questions,
        primary_question_key="release_impact",
        result_field_name="impact",
        uncertain_choices=frozenset({"uncertain", "UNCERTAIN"}),
        recommendation_builder=None,
        luna_instruction_builder=lambda c, conf, r: (
            f"Upstream release impact triage returned '{c}' (confidence: {conf:.2f}). "
            f"Worker Luna inspection required."
        ),
    )


def evaluate_evidence_item(
    item: dict[str, Any],
    client: Any,
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Evaluate one evidence row for semantic concerns.

    Advisory semantic routing only; NOT verification, NOT grade or HTTP check.
    """
    source = str(item.get("source") or item.get("url") or "")[:200]
    ev_type = str(item.get("type") or "unknown")[:50]
    notes = str(item.get("notes") or "")[:1000]

    questions = {
        "semantic_concern": {
            "type": "choice",
            "instructions": f"Evaluate semantic claim for evidence row of type '{ev_type}': {notes[:200]}",
            "criteria": {
                "plausible_claim": "Concrete, verifiable evidence claim with factual assertions directly supporting the skill.",
                "methodology_mismatch": "Claim or metrics do not match the specified evidence type or registry methodology.",
                "needs_investigation": "Contains marketing hyperbole, subjective unverified claims ('elite', 'best'), or questionable attribution requiring auditor review.",
                "uncertain": "Insufficient or ambiguous notes to make a determination.",
            },
        }
    }

    state = {
        "source": source,
        "type": ev_type,
        "notes": notes[:800],
        "evaluator": str(item.get("evaluator") or "")[:50],
        "grade": str(item.get("grade") or item.get("class") or "")[:10],
    }

    base_result: dict[str, Any] = {
        "source": source,
        "type": ev_type,
    }

    eval_res = _dispatch_evaluate(client, state, questions, exhaustion_reason)

    return handle_evaluation_result(
        base_result=base_result,
        eval_res=eval_res,
        state=state,
        questions=questions,
        primary_question_key="semantic_concern",
        result_field_name="semanticConcern",
        uncertain_choices=frozenset({"uncertain", "UNCERTAIN"}),
        recommendation_builder=None,
        luna_instruction_builder=lambda c, conf, r: (
            f"Evidence semantic concern triage returned '{c}' (confidence: {conf:.2f}). "
            f"Worker Luna investigation required."
        ),
    )


def evaluate_meta_item(
    item: dict[str, Any],
    client: Any,
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Evaluate one generic node for vendor coupling and scoping.

    Advisory review route only.
    """
    node_id = str(item.get("id") or "unknown_generic")
    name = str(item.get("name") or node_id)[:100]
    description = str(item.get("description") or "")[:1500]
    summary = str(item.get("summary") or "")[:500]

    questions = {
        "review_route": {
            "type": "choice",
            "instructions": f"Evaluate generic skill '{node_id}' ({name}) for vendor neutrality and abstraction scope.",
            "criteria": {
                "vendor_coupling_suspect": "Mentions vendor-specific tools, proprietary brands, or company-specific terminology instead of vendor-neutral abstractions.",
                "overly_broad": "Scope is excessively broad or umbrella-like, combining multiple distinct capabilities into one.",
                "well_scoped": "Vendor-neutral, precise, and well-scoped capability definition.",
                "uncertain": "Ambiguous or insufficient description to evaluate abstraction quality.",
            },
        }
    }

    state = {
        "id": node_id[:100],
        "name": name,
        "description": description[:1000],
        "summary": summary[:300],
    }

    base_result: dict[str, Any] = {
        "id": node_id,
        "name": name,
    }

    eval_res = _dispatch_evaluate(client, state, questions, exhaustion_reason)

    return handle_evaluation_result(
        base_result=base_result,
        eval_res=eval_res,
        state=state,
        questions=questions,
        primary_question_key="review_route",
        result_field_name="reviewRoute",
        uncertain_choices=frozenset({"uncertain", "UNCERTAIN"}),
        recommendation_builder=None,
        luna_instruction_builder=lambda c, conf, r: (
            f"Meta abstraction review returned '{c}' (confidence: {conf:.2f}). "
            f"Worker Luna maintainer review required."
        ),
    )


def evaluate_steward_item(
    item: dict[str, Any],
    client: Any,
    exhaustion_reason: str | None = None,
) -> dict[str, Any]:
    """Evaluate one steward debt/finding item for offline review hints.

    Inspects real Steward models/scan shapes (Debt, Observation).
    Avoids fake clean bill when missing fields -> fallback to worker-luna.
    """
    debt_id = str(item.get("id") or item.get("debt_id") or "unknown_debt")
    kind = str(item.get("kind") or "")
    subject = item.get("subject")
    current_state = item.get("currentState") or item.get("current_state")
    observed_state = item.get("observedState") or item.get("observed_state")
    status = str(item.get("status") or "")
    source = str(item.get("source") or "")
    priority = item.get("priority")
    authority = item.get("authority")

    base_result: dict[str, Any] = {
        "id": debt_id,
        "kind": kind,
    }

    has_valid_states = (current_state is not None or observed_state is not None)
    has_subject = (subject is not None and subject != "")
    has_kind = bool(kind.strip())

    if not (has_kind and has_subject and has_valid_states):
        state = {
            "id": debt_id[:100],
            "kind": kind[:50],
            "raw": {k: str(v)[:100] for k, v in item.items() if k not in ("_malformed",)},
        }
        base_result.update({
            "status": "fallback",
            "reason": "missing_required_state_fields",
            "advisoryResult": None,
            "fallback": {
                "agent": "worker-luna",
                "instruction": (
                    f"Steward debt/finding item '{debt_id}' does not match real debt or observation shape "
                    f"(missing kind/subject/state). Maintainer inspection required; no automated clean bill permitted."
                ),
                "context": state,
                "questions": {},
            },
            "usage": {},
            "estimatedCostUsd": 0.0,
            "reservedUsd": 0.0,
        })
        return base_result

    questions = {
        "steward_hint": {
            "type": "choice",
            "instructions": f"Provide offline advisory review hint for detected debt '{debt_id}' of kind '{kind}'.",
            "criteria": {
                "prioritize_triage": "High-impact drift or schema violation that should be reviewed promptly by a maintainer.",
                "routine_maintenance": "Expected drift or standard maintenance debt suitable for routine batch repair.",
                "monitor_only": "Low-severity or transient state that does not require immediate action; continue monitoring.",
                "uncertain": "Insufficient or incomplete observed/current state to make a clear recommendation.",
            },
        }
    }

    subj_str = (
        f"{subject.get('type')}:{subject.get('id')}"
        if isinstance(subject, dict) and "type" in subject
        else str(subject)
    )

    state = {
        "id": debt_id[:100],
        "kind": kind[:50],
        "subject": subj_str[:200],
        "currentState": str(current_state)[:400] if current_state else "",
        "observedState": str(observed_state)[:400] if observed_state else "",
        "status": status[:20],
        "source": source[:100],
    }
    if isinstance(priority, dict):
        state["priorityScore"] = priority.get("score")
    if isinstance(authority, dict):
        state["authorityClass"] = authority.get("class")

    eval_res = _dispatch_evaluate(client, state, questions, exhaustion_reason)

    return handle_evaluation_result(
        base_result=base_result,
        eval_res=eval_res,
        state=state,
        questions=questions,
        primary_question_key="steward_hint",
        result_field_name="reviewHint",
        uncertain_choices=frozenset({"uncertain", "UNCERTAIN"}),
        recommendation_builder=None,
        luna_instruction_builder=lambda c, conf, r: (
            f"Steward debt review hint returned '{c}' (confidence: {conf:.2f}). "
            f"Worker Luna maintainer triage required."
        ),
    )


class _ItemList(list):
    """List of items preserving metadata for actionable overflow and pagination."""
    omitted_ids: list[str]
    offset: int
    total_available: int

    def __init__(
        self,
        iterable=(),
        omitted_ids: list[str] | None = None,
        offset: int = 0,
        total_available: int = 0,
    ):
        super().__init__(iterable)
        self.omitted_ids = omitted_ids or []
        self.offset = offset
        self.total_available = total_available


def load_input(
    mode: str,
    input_path: str | None = None,
    collect_repo: bool = False,
    repo_root: str | None = None,
    offset: int = 0,
    limit: int = MAX_ITEMS_PER_RUN,
) -> tuple[list[dict[str, Any]], bool, int]:
    """Load items for evaluation, returning (items, overflow_reported, total_available)."""
    if repo_root is None:
        repo_root = _get_repo_root()

    offset = max(0, offset)

    if collect_repo:
        if mode == "mapping":
            packets_dir = os.path.join(repo_root, "registry-for-review", "discovery-packets")
            if not os.path.isdir(packets_dir):
                return _ItemList(), False, 0
            all_files = sorted([
                f for f in os.listdir(packets_dir)
                if f.endswith(".json") and not f.startswith(".")
            ])
            total_available = len(all_files)
            max_batch = min(limit, MAX_COLLECT_ITEMS)
            sliced_files = all_files[offset : offset + max_batch]
            overflow_reported = total_available > (offset + len(sliced_files))
            omitted_ids = [
                f.replace(".packet.json", "").replace(".json", "")
                for f in all_files[offset + len(sliced_files) :]
            ]
            items: list[dict[str, Any]] = []
            for fname in sliced_files:
                fpath = os.path.join(packets_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    items.append(data)
                except (OSError, json.JSONDecodeError):
                    continue
            return (
                _ItemList(items, omitted_ids=omitted_ids, offset=offset, total_available=total_available),
                overflow_reported,
                total_available,
            )

        elif mode == "meta":
            nodes_map = load_generic_nodes(repo_root)
            total_available = len(nodes_map)
            all_ids = sorted(nodes_map.keys())
            max_batch = min(limit, MAX_COLLECT_ITEMS)
            sliced_ids = all_ids[offset : offset + max_batch]
            overflow_reported = total_available > (offset + len(sliced_ids))
            omitted_ids = all_ids[offset + len(sliced_ids) :]
            items = [nodes_map[gid] for gid in sliced_ids]
            return (
                _ItemList(items, omitted_ids=omitted_ids, offset=offset, total_available=total_available),
                overflow_reported,
                total_available,
            )

        elif mode == "issues":
            raise ValueError(
                "--collect-repo does not fetch GitHub issues automatically. "
                "Collect open issues via 'gh issue list --json number,title,body,labels' and provide via --input."
            )
        else:
            raise ValueError(f"--collect-repo is not supported for mode '{mode}'. Provide input via --input.")

    if not input_path:
        raise ValueError("Either --input or --collect-repo must be specified.")

    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    file_size = os.path.getsize(input_path)
    if file_size > MAX_INPUT_FILE_BYTES:
        raise ValueError(
            f"Input file size {file_size} exceeds maximum {MAX_INPUT_FILE_BYTES} bytes: {input_path}"
        )

    with open(input_path, "r", encoding="utf-8") as fp:
        content = fp.read(MAX_INPUT_FILE_BYTES + 1)
        if len(content) > MAX_INPUT_FILE_BYTES:
            raise ValueError(
                f"Input file content exceeds maximum {MAX_INPUT_FILE_BYTES} bytes: {input_path}"
            )
        try:
            raw_data = json.loads(content)
        except json.JSONDecodeError as err:
            raise ValueError(f"Invalid JSON in input file: {err}") from err

    if not isinstance(raw_data, (list, dict)):
        raise ValueError(f"Input JSON must be an object or array, got {type(raw_data).__name__}")

    raw_items: list[Any] = []
    if isinstance(raw_data, list):
        raw_items = raw_data
    else:
        if mode == "mapping":
            if raw_data.get("contractVersion") == "discovery-packet-v2":
                raw_items = [raw_data]
            elif "proposedSkills" in raw_data and isinstance(raw_data["proposedSkills"], list):
                raw_items = raw_data["proposedSkills"]
            elif "skills" in raw_data and isinstance(raw_data["skills"], list):
                raw_items = raw_data["skills"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                raw_items = raw_data["items"]
            else:
                raw_items = [raw_data]
        elif mode == "issues":
            if "issues" in raw_data and isinstance(raw_data["issues"], list):
                raw_items = raw_data["issues"]
            else:
                raw_items = [raw_data]
        elif mode == "upstream":
            if "findings" in raw_data and isinstance(raw_data["findings"], list):
                raw_items = raw_data["findings"]
                top_rn = raw_data.get("releaseNotes")
                if top_rn:
                    for f in raw_items:
                        if isinstance(f, dict) and not f.get("releaseNotes"):
                            f["releaseNotes"] = top_rn
            else:
                raw_items = [raw_data]
        elif mode == "evidence":
            if "evidence" in raw_data and isinstance(raw_data["evidence"], list):
                raw_items = raw_data["evidence"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                raw_items = raw_data["items"]
            else:
                raw_items = [raw_data]
        elif mode == "meta":
            if "skills" in raw_data and isinstance(raw_data["skills"], list):
                raw_items = raw_data["skills"]
            elif "nodes" in raw_data and isinstance(raw_data["nodes"], list):
                raw_items = raw_data["nodes"]
            else:
                raw_items = [raw_data]
        elif mode == "steward":
            if "debts" in raw_data and isinstance(raw_data["debts"], list):
                raw_items = raw_data["debts"]
            elif "observations" in raw_data and isinstance(raw_data["observations"], list):
                raw_items = raw_data["observations"]
            elif "findings" in raw_data and isinstance(raw_data["findings"], list):
                raw_items = raw_data["findings"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                raw_items = raw_data["items"]
            else:
                raw_items = [raw_data]
        else:
            raw_items = [raw_data]

    # Process all rows: never silently drop malformed rows
    all_items: list[dict[str, Any]] = []
    for idx, x in enumerate(raw_items):
        if isinstance(x, dict):
            all_items.append(x)
        else:
            all_items.append({
                "id": f"malformed_row_{idx}",
                "candidateId": f"malformed_row_{idx}",
                "_malformed": True,
                "malformedError": f"Malformed row at index {idx}: expected object, got {type(x).__name__}",
                "raw": str(x)[:200],
            })

    total_available = len(all_items)
    sliced_items = all_items[offset : offset + limit]
    overflow_reported = total_available > (offset + len(sliced_items))

    omitted_ids: list[str] = []
    for i in range(offset + len(sliced_items), total_available):
        item_obj = all_items[i]
        oid = item_obj.get("candidateId") or item_obj.get("id") or item_obj.get("number") or f"row_{i}"
        omitted_ids.append(str(oid))

    return (
        _ItemList(sliced_items, omitted_ids=omitted_ids, offset=offset, total_available=total_available),
        overflow_reported,
        total_available,
    )


def run_advisory(
    mode: str,
    items: list[dict[str, Any]],
    client: Any,
    repo_root: str | None = None,
    overflow_reported: bool = False,
    total_available: int | None = None,
    offset: int = 0,
    omitted_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Execute advisory evaluations for a batch of items in the specified mode."""
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: '{mode}'. Must be one of {sorted(SUPPORTED_MODES)}")

    generic_nodes = load_generic_nodes(repo_root) if mode == "mapping" else {}

    item_reports: list[dict[str, Any]] = []
    advisory_count = 0
    fallback_count = 0
    total_calls = 0
    total_reserved_usd = 0.0
    total_estimated_cost_usd = 0.0
    exhaustion_reason: str | None = None

    if omitted_ids is None:
        omitted_ids = getattr(items, "omitted_ids", [])
    if offset == 0 and hasattr(items, "offset"):
        offset = items.offset
    if total_available is None:
        total_available = getattr(items, "total_available", len(items))

    for item in items:
        if item.get("_malformed"):
            item_id = item.get("candidateId") or item.get("id") or "malformed_item"
            res = {
                "candidateId": item_id,
                "status": "fallback",
                "reason": "malformed_input_row",
                "advisoryResult": None,
                "fallback": {
                    "agent": "worker-luna",
                    "instruction": str(item.get("malformedError") or "Malformed input row"),
                    "context": {"raw": item.get("raw")},
                    "questions": {},
                },
                "usage": {},
                "estimatedCostUsd": 0.0,
                "reservedUsd": 0.0,
            }
            item_reports.append(res)
            fallback_count += 1
            continue

        if mode == "mapping":
            res = evaluate_mapping_item(item, client, generic_nodes, exhaustion_reason=exhaustion_reason)
        elif mode == "issues":
            res = evaluate_issues_item(item, client, all_issues=items, exhaustion_reason=exhaustion_reason)
        elif mode == "upstream":
            res = evaluate_upstream_item(item, client, exhaustion_reason=exhaustion_reason)
        elif mode == "evidence":
            res = evaluate_evidence_item(item, client, exhaustion_reason=exhaustion_reason)
        elif mode == "meta":
            res = evaluate_meta_item(item, client, exhaustion_reason=exhaustion_reason)
        elif mode == "steward":
            res = evaluate_steward_item(item, client, exhaustion_reason=exhaustion_reason)
        else:
            raise ValueError(f"Unhandled mode: {mode}")

        if res.get("status") == "advisory":
            advisory_count += 1
        else:
            fallback_count += 1

        reserved = float(res.get("reservedUsd", 0.0))
        if reserved > 0.0:
            total_reserved_usd += reserved
            total_calls += 1

        if not res.get("cached", False):
            total_estimated_cost_usd += float(res.get("estimatedCostUsd", 0.0))

        reason = res.get("reason")
        if reason in EXHAUSTION_REASONS:
            exhaustion_reason = reason

        item_reports.append(res)

    processed_count = len(item_reports)
    next_offset = (offset + processed_count) if (offset + processed_count < total_available) else None
    omitted_count = max(0, total_available - (offset + processed_count))

    report = {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": mode,
        "advisoryOnly": True,
        "summary": {
            "totalAvailable": total_available,
            "processedCount": processed_count,
            "advisoryCount": advisory_count,
            "fallbackCount": fallback_count,
            "totalCalls": total_calls,
            "totalReservedUsd": round(total_reserved_usd, 6),
            "totalEstimatedCostUsd": round(total_estimated_cost_usd, 6),
            "overflowReported": overflow_reported,
            "offset": offset,
            "nextOffset": next_offset,
            "omittedCount": omitted_count,
            "omittedIdentifiers": omitted_ids[:50],
        },
        "items": item_reports,
    }
    return report
