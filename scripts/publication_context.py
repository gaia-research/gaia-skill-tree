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
import sysconfig
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
    "docs-graph-assets": ("syncDocsGraphAssets.py", ("docs/graph/gaia.json", "docs/graph/gaia.gexf", "docs/schema/")),
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
# These legacy scripts write in place rather than to --out temp candidates.
# Successful invocation alone cannot prove that they did not skip their work.
FRESH_OUTPUTS = {
    "assembly": ("registry/gaia.json",),
    "tree-md": ("generated-output/tree.md", "generated-output/layouts.json", "registry/registry.md"),
    "gexf": ("registry/gaia.gexf",),
    "docs-graph-assets": ("docs/graph/gaia.json", "docs/graph/gaia.gexf"),
}
_active = None
_executions = []
_before_stage = {}
_before_stats = {}
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


def source_revision(source_root):
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source_root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


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


def _native_runtime_identity():
    # A clean interpreter avoids binding unrelated libraries imported by the
    # calling test runner. Hash the actual loaded native dependency bytes,
    # including system Cairo/BLAS/libc when the optional renderers are usable.
    probe = r'''
import hashlib, importlib, json, os, sys
from pathlib import Path
imports = {}
for name in ("numpy", "scipy.linalg", "PIL.Image", "cairosvg", "wand.image"):
    try:
        importlib.import_module(name)
        imports[name] = "available"
    except Exception as exc:
        imports[name] = type(exc).__name__
maps = Path("/proc/self/maps")
if not maps.is_file():
    raise RuntimeError("native runtime binding currently requires Linux procfs")
paths = {line.split(None, 5)[5] for line in maps.read_text().splitlines() if len(line.split(None, 5)) == 6}
libraries = {}
for raw in sorted(paths):
    path = Path(raw)
    if ".so" in path.name:
        if not path.is_file():
            raise RuntimeError("loaded native library is not readable")
        libraries.setdefault(path.name, []).append(hashlib.sha256(path.read_bytes()).hexdigest())
fonts = {}
if imports["cairosvg"] == "available" or imports["wand.image"] == "available":
    for key in ("FONTCONFIG_FILE", "FONTCONFIG_PATH", "MAGICK_CONFIGURE_PATH"):
        if os.environ.get(key):
            raise RuntimeError("unbound native renderer configuration override: " + key)
    for label, directory in (("system-fonts", Path("/usr/share/fonts")), ("android-fonts", Path("/system/fonts")),
                             ("prefix-fonts", Path(sys.prefix) / "share/fonts"),
                             ("system-fontconfig", Path("/etc/fonts")),
                             ("prefix-fontconfig", Path(sys.prefix) / "etc/fonts"),
                             ("user-fonts", Path.home() / ".fonts"),
                             ("user-local-fonts", Path.home() / ".local/share/fonts")):
        contents = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(directory.rglob("*")) if p.is_file()}
        fonts[label] = hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()
print(json.dumps({"imports": imports, "libraries": libraries, "fontData": fonts}, sort_keys=True))
'''
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def runtime_identity() -> dict:
    """Bind interpreter and actual installed dependency bytes, not host paths."""
    from packaging.requirements import Requirement
    packages = {}
    pending = {"jinja2", "jsonschema", "pyyaml", "questionary", "numpy", "scipy", "networkx",
               "packaging", "python-frontmatter", "pillow", "cairosvg", "wand"}
    while pending:
        name = sorted(pending)[0]
        pending.remove(name)
        if name in packages:
            continue
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "unavailable"
            continue
        for requirement in dist.requires or []:
            requirement = Requirement(requirement)
            if requirement.marker is None or requirement.marker.evaluate():
                dependency = re.sub(r"[-_.]+", "-", requirement.name).lower()
                if dependency not in packages:
                    pending.add(dependency)
        files = {}
        for item in sorted(dist.files or [], key=str):
            if "__pycache__" in str(item) or str(item).endswith(".pyc"):
                continue
            path = dist.locate_file(item)
            if path.is_file():
                files[str(item)] = _digest(path.read_bytes())
        packages[name] = {"version": dist.version, "filesDigest": _digest(json.dumps(files, sort_keys=True).encode())}
    stdlib = Path(sysconfig.get_path("stdlib"))
    stdlib_files = {}
    for directory, subdirs, filenames in os.walk(stdlib):
        subdirs[:] = sorted(d for d in subdirs if d not in ("site-packages", "dist-packages", "__pycache__"))
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if path.suffix in (".py", ".so", ".pyd"):
                stdlib_files[path.relative_to(stdlib).as_posix()] = _digest(path.read_bytes())
    return {"python": sys.version, "implementation": platform.python_implementation(),
            "platform": platform.platform(), "interpreter": _digest(Path(sys.executable).read_bytes()),
            "stdlibDigest": _digest(json.dumps(stdlib_files, sort_keys=True).encode()),
            "nativeRuntime": _native_runtime_identity(),
            "packages": packages, "environment": {k: os.environ.get(k) for k in
            ("LANG", "LC_ALL", "TZ", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")}, "hashSeed": "0"}


def _validate_context(payload: dict) -> dict:
    expected_keys = {"mode", "approval", "snapshotId", "evaluationAtUTC", "sourceRevision", "inputDigests",
                     "runtimeIdentity", "engineIdentity", "policyIdentity"}
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("invalid publication rehearsal context fields")
    if payload.get("mode") != MODE or payload.get("approval") != APPROVAL:
        raise ValueError("invalid publication rehearsal context")
    if not isinstance(payload.get("sourceRevision"), str) or not re.fullmatch(r"(?:[0-9a-f]{40}|unavailable)", payload["sourceRevision"]):
        raise ValueError("invalid source revision")
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
    path = Path(path).absolute()
    _safe_path(path.parent, path.name)
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
    if not path:
        return None
    expected = Path(__file__).resolve().parents[1] / "publication-context.json"
    if Path(path).absolute() != expected or Path(path).is_symlink():
        raise ValueError("publication context must belong to this isolated scratch source")
    return load_context(path)


def create_context(source_root: Path, output_root: Path, evaluation_at_utc: str | None = None) -> dict:
    source_root = source_root.resolve(strict=True)
    output_root = output_root.expanduser().absolute()
    if output_root.exists() or output_root.is_symlink():
        raise ValueError("publication output root must be a new non-symlink path")
    if any(p.is_symlink() for p in (output_root, *output_root.parents)):
        raise ValueError("publication output root must not be under a symlink path")
    resolved = output_root.resolve(strict=False)
    if (any(resolved == root or root in resolved.parents or resolved in root.parents for root in _worktree_roots(source_root))
            or any((parent / ".git").exists() for parent in resolved.parents)):
        raise ValueError("publication output root must be disjoint from every repository worktree")
    instant = _utc(evaluation_at_utc) if evaluation_at_utc else datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    inputs = _inventory(source_root)
    if REPORTS & inputs.keys():
        raise ValueError("source contains reserved publication report paths")
    revision = source_revision(source_root)
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


def _write_signature(path):
    if not path.is_file():
        return None
    stat = path.stat()
    return stat.st_ino, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size


def begin_stage(name, root):
    global _active, _executions, _before_stage, _before_stats
    _active, _executions = name, []
    _before_stage = _inventory(root, True)
    _before_stats = {rel: _write_signature(root / rel) for rel in FRESH_OUTPUTS.get(name, ())}
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
    for rel, before in _before_stats.items():
        after_signature = _write_signature(root / rel)
        if after_signature is None or after_signature == before:
            raise ValueError(f"required generator skipped output write: {name}: {rel}")
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
            "freshWrites": sorted(_before_stats),
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
        if not isinstance(stage, dict) or set(stage) - {"status", "outputs", "executions", "freshWrites", "changedOutputs", "removedOutputs"}:
            raise ValueError("invalid generator execution record")
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
        if set(stage.get("freshWrites", [])) != set(FRESH_OUTPUTS.get(name, ())):
            raise ValueError("rehearsal incomplete: required in-place writes unobserved")
        for rel in stage["outputs"]:
            _safe_path(Path("/"), rel)
            if not any(rel.startswith(s) if s.endswith("/") else rel == s for s in spec[1]):
                raise ValueError("mixed generator output attribution")


def _mutable_output(rel):
    if (rel == "README.md" or rel == "docs/css/tokens.css"
            or rel == "docs/experiments/ml-graph-viz/layouts_3d.json"
            or rel.startswith("docs/") and rel.endswith(".html")
            or rel.startswith("skill-trees/") and rel.endswith("/skill-tree.md")):
        return True
    return any(rel.startswith(selector) if selector.endswith("/") else rel == selector
               for name, (_, selectors) in {**STAGE_SPECS, **AUXILIARY_SPECS}.items() if name != "json-ld"
               for selector in selectors)


def _check_source_preservation(inventory, context):
    inputs = context["inputDigests"]
    for rel in sorted(set(inputs) | set(inventory)):
        if inputs.get(rel) != inventory.get(rel) and not _mutable_output(rel):
            raise ValueError("builder mutated or introduced source input: " + rel)


def _artifact_inventory(inventory, stages):
    generated = {rel for stage in stages.values()
                 for rel in {*stage.get("outputs", {}), *stage.get("changedOutputs", {})}}
    produced = {rel for name, stage in stages.items() if name not in ("json-ld", "html-cache-busting")
                for rel in stage.get("outputs", {})}
    artifacts = {rel: digest for rel, digest in inventory.items()
                 if (rel.startswith("docs/") or rel in generated) and not rel.startswith("docs/reports/DRAFT/")}
    classes = {rel: ("generated" if rel in produced else "transformed-static" if rel in generated else "copied-static")
               for rel in artifacts}
    return artifacts, classes


def stamp_outputs(output_root: Path, context: dict, stages: dict | None = None) -> dict:
    _validate_context(context)
    _validate_stages(stages)
    inventory = _inventory(output_root, True)
    if not set(GENERATED_OUTPUTS) <= inventory.keys():
        raise ValueError("rehearsal incomplete: required generated output missing")
    _check_semantic_parity(output_root)
    if _inventory(output_root, True) != inventory:
        raise ValueError("parity oracle mutated inspected output/source bytes")
    # Full post-build inventory binds generated AND copied static deploy assets;
    # operational DRAFT records remain external to publication artifact identity.
    artifacts, classes = _artifact_inventory(inventory, stages)
    _check_source_preservation(inventory, context)
    manifest = {"mode": MODE, "approval": APPROVAL, "snapshotId": context["snapshotId"],
                "evaluationAtUTC": context["evaluationAtUTC"], "stages": stages,
                "artifacts": artifacts, "artifactClasses": classes, "postBuildDigests": inventory,
                "challengeProjection": "unavailable", "standing": "stored-source-revision"}
    for filename, payload in (("publication-context.json", context), ("publication-stages.json", stages),
                              ("publication-artifacts.json", manifest)):
        temporary = output_root / (filename + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output_root / filename)
    return manifest


def verify_outputs(output_root: Path, expected_snapshot_id: str | None = None) -> bool:
    """Integrity only. Caller must retain expected identity; no authentication claim."""
    try:
        if output_root.is_symlink() or any(p.is_symlink() for p in output_root.parents):
            return False
        manifest_path = _safe_path(output_root, "publication-artifacts.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_keys = {"mode", "approval", "snapshotId", "evaluationAtUTC", "stages", "artifacts", "artifactClasses",
                         "postBuildDigests", "challengeProjection", "standing"}
        if not isinstance(manifest, dict) or set(manifest) != expected_keys:
            return False
        context = load_context(output_root / "publication-context.json")
        if (manifest.get("mode"), manifest.get("approval")) != (MODE, APPROVAL):
            return False
        if not expected_snapshot_id or context["snapshotId"] != expected_snapshot_id:
            return False
        if manifest.get("snapshotId") != context["snapshotId"] or manifest.get("evaluationAtUTC") != context["evaluationAtUTC"]:
            return False
        _validate_stages(manifest.get("stages"))
        actual = _inventory(output_root, True)
        if actual != manifest.get("postBuildDigests"):
            return False
        _check_source_preservation(actual, context)
        if manifest.get("challengeProjection") != "unavailable" or manifest.get("standing") != "stored-source-revision":
            return False
        stage_path = _safe_path(output_root, "publication-stages.json")
        if not stage_path.is_file() or json.loads(stage_path.read_text(encoding="utf-8")) != manifest["stages"]:
            return False
        expected_artifacts, expected_classes = _artifact_inventory(actual, manifest["stages"])
        if manifest.get("artifacts") != expected_artifacts or manifest.get("artifactClasses") != expected_classes:
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
