"""Strict offline publication rehearsal. Hashes are integrity checks, NOT approval.

The private staging directory protects against accidental partial publication, not
hostile concurrent filesystem mutation. No receipt issuer is available here.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

MODE = "rehearsal"
APPROVAL = "unavailable"
COPY_IGNORES = {".git", ".gaia", ".pi", "__pycache__", ".pytest_cache", "node_modules"}
REPORTS = {"publication-context.json", "publication-artifacts.json", "publication-stages.json"}
# Retired gaia.svg is a copied static asset, NOT a freshly generated graph.
GENERATED_OUTPUTS = (
    "registry/gaia.json", "registry/named-skills.json", "docs/graph/named/index.json",
    "docs/graph/ledger/data.json", "docs/api/v1/skills/index.json",
    "docs/u/index.html", "docs/badges/registry.json", "docs/graph/gaia.json",
    "docs/graph/gaia.gexf", "docs/api/v1/leaderboard.json", "docs/api/v1/health.json",
)
REQUIRED_OUTPUTS = GENERATED_OUTPUTS
# Existing orchestration owns these surfaces. No second build scheduler.
STAGE_SPECS = {
    "assembly": ("assemble_gaia.py", ("registry/gaia.json",)),
    "named-index": ("generateNamedIndex.py", ("registry/named-skills.json",)),
    "docs-named-index": (None, ("docs/graph/named/index.json",)),
    "trust-ledger": ("generateLeaderboardData.py", ("docs/graph/ledger/data.json",)),
    "api-projection": ("buildApiProjection.py", ("docs/api/v1/skills/", "docs/api/v1/contributors/", "docs/api/v1/leaderboard.json", "docs/api/v1/search-index.json", "docs/api/v1/health.json", "docs/api/v1/evidence-types.json")),
    "profiles": ("generateProfilePages.py", ("docs/u/",)),
    "badges": ("generateBadges.py", ("docs/badges/registry.json", "docs/badges/_assets/", "docs/badges/samples/", "docs/badges/powered-by-gaia.svg", "docs/badges/not-found.svg")),
    "og-cards": ("generateOgCards.py", ("docs/og/",)),
    "tree-md": ("generateProjections.py", ("docs/tree.md", "registry/registry.md", "registry/layouts_3d.json", "generated-output/tree.md", "generated-output/layouts.json", "registry/skills/", "registry/combinations.md")),
    "gexf": ("exportGexf.py", ("registry/gaia.gexf",)),
    "docs-graph-assets": ("syncDocsGraphAssets.py", ("docs/graph/gaia.json", "docs/graph/gaia.gexf")),
}
AUXILIARY_SPECS = {
    "benchmark-projection": ("generateBenchmarkProjection.py", ("docs/api/v1/benchmarks/",)),
    "trending-projection": ("buildTrendingProjection.py", ("docs/api/v1/trending/",)),
    "content-engine": ("generate_weekly_report.py", ("docs/reports/DRAFT/",)),
    "okf-bundle": ("build_okf_bundle.py", ("docs/okf/",)),
    "skills-index": ("buildSkillsIndex.py", ("docs/okf/index.json",)),
    "sitemap": ("generateSitemap.py", ("docs/sitemap.xml",)),
    "json-ld": ("injectJsonLd.py", ("docs/",)),
    "installability-projection": (None, ("docs/graph/installability/index.json",)),
    "arbor-projection": (None, ("docs/graph/arbor/",)),
}
_active = None
_executions = []
_before_stage = {}
_context_cache = {}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_path(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or "\\" in rel:
        raise ValueError("invalid relative inventory path")
    pure = PurePosixPath(rel)
    if pure.is_absolute() or any(p in (".", "..") for p in rel.split("/")) or pure.as_posix() != rel:
        raise ValueError("unsafe inventory path: " + rel)
    path = root / rel
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink in inventory path: " + rel)
    return path


def _inventory(root: Path, exclude_reports=False) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if any(part in COPY_IGNORES for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink in copied source inventory: {rel}")
        if path.is_file() and not (exclude_reports and rel in REPORTS):
            result[rel] = _digest(path.read_bytes())
    return result


def _worktree_roots(source_root: Path) -> list[Path]:
    try:
        raw = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=source_root,
                             check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return [source_root]
    return [Path(line[9:]).resolve() for line in raw.splitlines() if line.startswith("worktree ")] or [source_root]


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("evaluationAtUTC must be an explicit ISO UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("evaluationAtUTC must be an explicit UTC timestamp")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _snapshot_id(inputs, revision, instant, runtime=None) -> str:
    return _digest(json.dumps({"inputs": inputs, "sourceRevision": revision, "evaluationAtUTC": instant,
                               "runtime": runtime}, sort_keys=True, separators=(",", ":")).encode())


def runtime_identity() -> dict:
    """Bind interpreter and actual installed dependency bytes, not host paths."""
    packages = {}
    for name in ("PyYAML", "numpy", "scipy", "networkx", "packaging", "python-frontmatter"):
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "unavailable"
            continue
        files = {}
        for item in sorted(dist.files or [], key=str):
            if "__pycache__" in str(item) or str(item).endswith(".pyc"):
                continue
            path = dist.locate_file(item)
            if path.is_file():
                files[str(item)] = _digest(path.read_bytes())
        packages[name] = {"version": dist.version, "filesDigest": _digest(json.dumps(files, sort_keys=True).encode())}
    return {"python": sys.version, "implementation": platform.python_implementation(),
            "platform": platform.platform(), "interpreter": _digest(Path(sys.executable).read_bytes()),
            "packages": packages, "environment": {k: os.environ.get(k) for k in
            ("LANG", "LC_ALL", "TZ", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")}, "hashSeed": "0"}


def _validate_context(payload: dict) -> dict:
    if payload.get("mode") != MODE or payload.get("approval") != APPROVAL:
        raise ValueError("invalid publication rehearsal context")
    if payload.get("evaluationAtUTC") != _utc(payload.get("evaluationAtUTC", "")):
        raise ValueError("malformed publication rehearsal time")
    inputs = payload.get("inputDigests")
    if not isinstance(inputs, dict) or not isinstance(payload.get("runtimeIdentity"), dict):
        raise ValueError("incomplete publication rehearsal context")
    for rel, digest in inputs.items():
        _safe_path(Path("/"), rel)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid input digest")
    expected = _snapshot_id(inputs, payload.get("sourceRevision"), payload["evaluationAtUTC"], payload["runtimeIdentity"])
    if payload.get("snapshotId") != expected:
        raise ValueError("publication context identity mismatch")
    if payload.get("engineIdentity") != inputs.get("src/gaia_cli/trustMagnitude.py", "missing"):
        raise ValueError("engine identity mismatch")
    if payload.get("policyIdentity") != {k: inputs.get(k, "missing") for k in ("META.md", "GOVERNANCE.md", "registry/schema/meta.json")}:
        raise ValueError("policy identity mismatch")
    return payload


def load_context(path: str | Path) -> dict:
    path = Path(path)
    stat = path.stat()
    key = (str(path.absolute()), stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if key not in _context_cache:
        _context_cache.clear()
        _context_cache[key] = _validate_context(json.loads(path.read_text(encoding="utf-8")))
    return _context_cache[key]


def evaluation_at_utc_from_env():
    context = rehearsal_context_from_env()
    return context["evaluationAtUTC"] if context else None


def evaluation_datetime_from_env():
    value = evaluation_at_utc_from_env()
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def rehearsal_context_from_env():
    path = os.environ.get("GAIA_PUBLICATION_CONTEXT")
    return load_context(path) if path else None


def create_context(source_root: Path, output_root: Path, evaluation_at_utc: str | None = None) -> dict:
    source_root = source_root.resolve(strict=True)
    output_root = output_root.expanduser().absolute()
    if output_root.exists() or output_root.is_symlink():
        raise ValueError("publication output root must be a new non-symlink path")
    if any(p.is_symlink() for p in (output_root, *output_root.parents)):
        raise ValueError("publication output root must not be under a symlink path")
    resolved = output_root.resolve(strict=False)
    if any(resolved == root or root in resolved.parents or resolved in root.parents for root in _worktree_roots(source_root)):
        raise ValueError("publication output root must be disjoint from every repository worktree")
    instant = _utc(evaluation_at_utc) if evaluation_at_utc else datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    inputs = _inventory(source_root)
    if REPORTS & inputs.keys():
        raise ValueError("source contains reserved publication report paths")
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source_root, check=True,
                                  capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    runtime = runtime_identity()
    return {"mode": MODE, "approval": APPROVAL, "snapshotId": _snapshot_id(inputs, revision, instant, runtime),
            "evaluationAtUTC": instant, "sourceRevision": revision, "inputDigests": inputs,
            "runtimeIdentity": runtime,
            "engineIdentity": inputs.get("src/gaia_cli/trustMagnitude.py", "missing"),
            "policyIdentity": {k: inputs.get(k, "missing") for k in ("META.md", "GOVERNANCE.md", "registry/schema/meta.json")}}


def verify_copied_inputs(output_root: Path, context: dict, allow_context=False) -> None:
    _validate_context(context)
    actual = _inventory(output_root)
    if allow_context:
        actual.pop("publication-context.json", None)
    if actual != context["inputDigests"]:
        raise ValueError("copied source input differs from snapshot (missing, extra or changed bytes)")


def _selected(root, selectors):
    return {rel: digest for rel, digest in _inventory(root, True).items()
            if any(rel.startswith(s) if s.endswith("/") else rel == s for s in selectors)}


def begin_stage(name, root):
    global _active, _executions, _before_stage
    _active, _executions = name, []
    _before_stage = _inventory(root, True)
    spec = STAGE_SPECS.get(name) or AUXILIARY_SPECS.get(name)
    script_path = root / "scripts" / ("contentEngine/" if name == "content-engine" else "") / spec[0] if spec and spec[0] else None
    if script_path and not script_path.is_file():
        raise ValueError(f"required generator missing: {spec[0]}")


def record_execution(script, args, returncode, output):
    if returncode or re.search(r"(?im)^\s*(?:warning:|fatal:|error:|.*skipping.*)", output):
        raise ValueError(f"generator failed/warned/skipped: {script.name}: {output[-1500:]}")
    produced = {}
    for flag in ("--out", "--out-dir"):
        if flag in args:
            path = Path(args[args.index(flag) + 1])
            if not path.exists():
                raise ValueError(f"generator did not produce {flag}: {script.name}")
            produced = _inventory(path) if path.is_dir() else {path.name: _digest(path.read_bytes())}
            if not produced:
                raise ValueError(f"generator produced an empty surface: {script.name}")
    _executions.append({"generator": script.name, "status": "success", "candidateOutputs": produced})


def finish_stage(name, root):
    spec = STAGE_SPECS.get(name) or AUXILIARY_SPECS.get(name)
    if spec and spec[0] and not any(e["generator"] == spec[0] for e in _executions):
        raise ValueError(f"required generator skipped: {spec[0]}")
    after = _inventory(root, True)
    changed = {rel: digest for rel, digest in after.items() if _before_stage.get(rel) != digest}
    outputs = {rel: digest for rel, digest in after.items()
               if any(rel.startswith(s) if s.endswith("/") else rel == s for s in spec[1])} if spec else changed
    if name == "json-ld":
        outputs = changed  # transforms HTML; it does not generate every static deploy asset
    if spec and not outputs and name != "json-ld":
        raise ValueError(f"required surface absent: {name}")
    # Unchanged outputs still have actual execution evidence; diff=False is not a failure.
    return {"status": "success", "executions": list(_executions), "outputs": outputs,
            "changedOutputs": changed, "removedOutputs": sorted(set(_before_stage) - set(after))}


def compare_ledger_api(ledger: dict, api: dict) -> list[str]:
    ledger_rows = {str(row.get("skillId")): row for row in ledger.get("rows", []) if row.get("skillId")}
    api_rows = {str(row.get("id")): row for row in api.get("skills", []) if row.get("id")}
    problems = []
    for skill_id in sorted(ledger_rows.keys() & api_rows.keys()):
        lrow, arow = ledger_rows[skill_id], api_rows[skill_id]
        if str(lrow.get("currentStars")) != str(arow.get("level")):
            problems.append(f"{skill_id}: canonical stars differ")
        if round(float(lrow.get("tm", 0)), 2) != round(float(arow.get("trustMagnitude", 0)), 2):
            problems.append(f"{skill_id}: TM differs")
    return problems


def _check_semantic_parity(root: Path) -> None:
    try:
        from publication_parity import check_semantic_parity
    except ModuleNotFoundError:
        from scripts.publication_parity import check_semantic_parity
    check_semantic_parity(root)


def _validate_stages(stages):
    if not isinstance(stages, dict) or not STAGE_SPECS.keys() <= stages.keys():
        raise ValueError("rehearsal incomplete: missing required generator success")
    for name, stage in stages.items():
        if stage.get("status") != "success":
            raise ValueError("generator did not succeed: " + name)
        for field in ("outputs", "changedOutputs"):
            for rel in stage.get(field, {}):
                _safe_path(Path("/"), rel)
        for execution in stage.get("executions", []):
            for rel in execution.get("candidateOutputs", {}):
                _safe_path(Path("/"), rel)
        spec = STAGE_SPECS.get(name) or AUXILIARY_SPECS.get(name)
        if not spec:
            continue
        if stage.get("status") != "success" or (not stage.get("outputs") and name != "json-ld"):
            raise ValueError("rehearsal incomplete: required generator success/output inventory")
        if spec[0] and not any(e.get("generator") == spec[0] and e.get("status") == "success" for e in stage.get("executions", [])):
            raise ValueError("rehearsal incomplete: missing actual generator execution")
        for rel in stage["outputs"]:
            _safe_path(Path("/"), rel)
            if not any(rel.startswith(s) if s.endswith("/") else rel == s for s in spec[1]):
                raise ValueError("mixed generator output attribution")


def stamp_outputs(output_root: Path, context: dict, stages: dict | None = None) -> dict:
    _validate_context(context)
    _validate_stages(stages)
    inventory = _inventory(output_root, True)
    if not set(GENERATED_OUTPUTS) <= inventory.keys():
        raise ValueError("rehearsal incomplete: required generated output missing")
    _check_semantic_parity(output_root)
    # Full post-build inventory binds generated AND copied static deploy assets;
    # all other bytes are bound as source inputs, never stamped in place.
    generated = {rel for stage in stages.values()
                 for rel in {*stage.get("outputs", {}), *stage.get("changedOutputs", {})}}
    artifacts = {rel: digest for rel, digest in inventory.items() if rel.startswith("docs/") or rel in generated}
    produced = {rel for name, stage in stages.items() if name not in ("json-ld", "html-cache-busting")
                for rel in stage.get("outputs", {})}
    classes = {rel: ("generated" if rel in produced else "transformed-static" if rel in generated else "copied-static")
               for rel in artifacts}
    for rel, digest in context["inputDigests"].items():
        if rel.startswith(("src/", "scripts/", "registry/nodes/", "registry/named/", "registry/schema/")) or rel.endswith("skill-tree.json"):
            if inventory.get(rel) != digest:
                raise ValueError("builder mutated source input: " + rel)
    manifest = {"mode": MODE, "approval": APPROVAL, "snapshotId": context["snapshotId"],
                "evaluationAtUTC": context["evaluationAtUTC"], "stages": stages,
                "artifacts": artifacts, "artifactClasses": classes, "postBuildDigests": inventory,
                "challengeProjection": "unavailable", "standing": "stored-source-revision"}
    for filename, payload in (("publication-context.json", context), ("publication-artifacts.json", manifest)):
        temporary = output_root / (filename + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output_root / filename)
    return manifest


def verify_outputs(output_root: Path, expected_snapshot_id: str | None = None) -> bool:
    """Integrity only. Caller must retain expected identity; no authentication claim."""
    try:
        if output_root.is_symlink() or any(p.is_symlink() for p in output_root.parents):
            return False
        manifest = json.loads((output_root / "publication-artifacts.json").read_text(encoding="utf-8"))
        context = load_context(output_root / "publication-context.json")
        if (manifest.get("mode"), manifest.get("approval")) != (MODE, APPROVAL):
            return False
        if expected_snapshot_id and context["snapshotId"] != expected_snapshot_id:
            return False
        if manifest.get("snapshotId") != context["snapshotId"] or manifest.get("evaluationAtUTC") != context["evaluationAtUTC"]:
            return False
        _validate_stages(manifest.get("stages"))
        actual = _inventory(output_root, True)
        if actual != manifest.get("postBuildDigests"):
            return False
        artifacts = manifest.get("artifacts", {})
        if not set(GENERATED_OUTPUTS) <= artifacts.keys() or set(artifacts) != set(manifest.get("artifactClasses", {})):
            return False
        for rel, digest in artifacts.items():
            if _digest(_safe_path(output_root, rel).read_bytes()) != digest:
                return False
        _check_semantic_parity(output_root)
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
