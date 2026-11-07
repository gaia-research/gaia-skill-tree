"""Focused smoke tests for four scripts that previously had no coverage (Refs #2283).

Subjects, each named explicitly below:

* scripts/archive/add_hermes_batch.py
* scripts/archive/fetch_ruflo_skills.py
* scripts/check_rank_vocabulary.py
* scripts/crawlers/huggingface/crawler.py

For every subject the tests (1) assert the file compiles with py_compile in
doraise mode, (2) load it through importlib in a way that is side-effect free,
and (3) exercise real pure functions or CLI paths against tiny synthetic
fixtures. No network is touched (urlopen and requests are stubbed), nothing is
written outside tmp_path, and the live registry is never read or mutated.

The subject scripts are intentionally NOT modified by this change: they still
carry unused imports that Gaia Steward removes in a separate Class B repair,
and these tests are the focused proof that repair needs.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import py_compile
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

repoRoot = Path(__file__).resolve().parent.parent
hermesScript = repoRoot / "scripts" / "archive" / "add_hermes_batch.py"
rufloScript = repoRoot / "scripts" / "archive" / "fetch_ruflo_skills.py"
rankScript = repoRoot / "scripts" / "check_rank_vocabulary.py"
hfScript = repoRoot / "scripts" / "crawlers" / "huggingface" / "crawler.py"
crawlersDir = repoRoot / "scripts" / "crawlers"


def loadScript(path: Path, name: str):
    """Load a script as a throwaway module without registering it in sys.modules."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hasMainGuard(path: Path) -> bool:
    """True when the file has a top-level `if __name__ == "__main__":` block."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False


def topLevelFunctionNames(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


@pytest.mark.parametrize(
    "script",
    [hermesScript, rufloScript, rankScript, hfScript],
    ids=["add_hermes_batch", "fetch_ruflo_skills", "check_rank_vocabulary", "huggingface_crawler"],
)
def test_subject_compiles_and_guards_main(script, tmp_path):
    assert script.is_file()
    # doraise surfaces syntax errors as PyCompileError; cfile keeps output in tmp_path
    py_compile.compile(str(script), cfile=str(tmp_path / "out.pyc"), doraise=True)
    assert hasMainGuard(script), f"{script.name} must guard its entrypoint"


# ---------------------------------------------------------------------------
# scripts/archive/add_hermes_batch.py
# ---------------------------------------------------------------------------


@pytest.fixture
def hermesWorkdir(tmp_path, monkeypatch):
    """Tiny stand-in registry; the script uses cwd-relative paths."""
    (tmp_path / "registry").mkdir()
    gaia = {"skills": [{"id": "zzz-existing", "name": "Existing"}, {"id": "aaa-existing", "name": "Existing A"}]}
    (tmp_path / "registry" / "gaia.json").write_text(json.dumps(gaia), encoding="utf-8")
    named = {"buckets": {"other-bucket": []}}
    (tmp_path / "registry" / "named-skills.json").write_text(json.dumps(named), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_add_hermes_batch_loads_without_touching_registry(hermesWorkdir):
    # Top level only defines functions, so loading must not create or change files.
    before = sorted(p.name for p in hermesWorkdir.rglob("*"))
    module = loadScript(hermesScript, "addHermesBatchUnderTest")
    assert callable(module.patch_gaia) and callable(module.patch_named_skills)
    assert sorted(p.name for p in hermesWorkdir.rglob("*")) == before
    assert json.loads((hermesWorkdir / "registry" / "gaia.json").read_text(encoding="utf-8"))["skills"][0]["id"] == "zzz-existing"


def test_add_hermes_batch_patch_gaia_appends_sorted_valid_skills(hermesWorkdir, capsys):
    module = loadScript(hermesScript, "addHermesBatchUnderTest")
    module.patch_gaia()

    skills = json.loads((hermesWorkdir / "registry" / "gaia.json").read_text(encoding="utf-8"))["skills"]
    ids = [s["id"] for s in skills]
    assert ids == sorted(ids), "patch_gaia must leave skills sorted by id"
    assert len(ids) == len(set(ids)), "no duplicate ids"
    assert {"zzz-existing", "aaa-existing", "generative-media", "ml-artifact-management"} <= set(ids)

    added = [s for s in skills if s["id"] not in {"zzz-existing", "aaa-existing"}]
    assert len(added) >= 5
    for skill in added:
        assert skill["status"] == "provisional"
        assert skill["type"] in {"basic", "extra"}
        assert len(skill["description"]) >= 10
        assert skill["evidence"] and skill["evidence"][0]["source"].startswith("https://")
        assert skill["prerequisites"], f"{skill['id']} should declare a prerequisite"
    assert f"Added {len(added)} new skills" in capsys.readouterr().out


def test_add_hermes_batch_patch_named_skills_creates_bucket(hermesWorkdir, capsys):
    module = loadScript(hermesScript, "addHermesBatchUnderTest")
    module.patch_named_skills()

    data = json.loads((hermesWorkdir / "registry" / "named-skills.json").read_text(encoding="utf-8"))
    assert data["buckets"]["other-bucket"] == [], "unrelated buckets stay untouched"
    entries = data["buckets"]["prompt-optimization"]
    assert [e["id"] for e in entries] == ["stanfordnlp/dspy"]
    assert entries[0]["links"]["github"].startswith("https://github.com/stanfordnlp/dspy")
    assert "stanfordnlp/dspy" in capsys.readouterr().out


def test_add_hermes_batch_main_path_runs_both_patches(hermesWorkdir):
    # runpy with run_name="__main__" exercises the guarded entrypoint end to end,
    # confined to the tmp_path fixture registry via chdir.
    runpy.run_path(str(hermesScript), run_name="__main__")
    gaia = json.loads((hermesWorkdir / "registry" / "gaia.json").read_text(encoding="utf-8"))
    named = json.loads((hermesWorkdir / "registry" / "named-skills.json").read_text(encoding="utf-8"))
    assert any(s["id"] == "generative-media" for s in gaia["skills"])
    assert "prompt-optimization" in named["buckets"]


# ---------------------------------------------------------------------------
# scripts/archive/fetch_ruflo_skills.py
# ---------------------------------------------------------------------------


@pytest.fixture
def ruflo():
    # Top level calls Path(__file__).resolve() only; that is pure, so exec_module is safe.
    return loadScript(rufloScript, "fetchRufloSkillsUnderTest")


def test_fetch_ruflo_skills_top_level_paths_resolve(ruflo):
    assert ruflo.ROOT.is_dir()
    assert ruflo.ROOT.is_absolute()
    assert ruflo.OUT_DEFAULT == ruflo.ROOT / "generated-output" / "ruflo-skills-raw.json"
    assert ruflo.BASE_RAW.startswith("https://raw.githubusercontent.com/ruvnet/ruflo/")


def test_fetch_ruflo_skills_tables_are_consistent(ruflo):
    assert len(ruflo.SKILL_DIRS) == len(set(ruflo.SKILL_DIRS)), "no duplicate skill dirs"
    assert "dual-mode" in ruflo.SKILL_DIRS
    assert ruflo.DUAL_MODE_FILES and all(f.endswith(".md") for f in ruflo.DUAL_MODE_FILES)
    flat = [member for members in ruflo.SUITES.values() for member in members]
    assert set(flat) <= set(ruflo.SKILL_DIRS), "every suite member is a known skill dir"


def test_fetch_ruflo_skills_suite_of(ruflo):
    assert ruflo._suite_of("agentdb-learning") == "agentdb"
    assert ruflo._suite_of("flow-nexus-swarm") == "flow-nexus"
    assert ruflo._suite_of("definitely-not-a-ruflo-skill") == "standalone"


class FakeResponse:
    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body.encode("utf-8")


def test_fetch_ruflo_skills_fetch_url_success_404_and_retry(ruflo, monkeypatch):
    sleeps = []
    monkeypatch.setattr(ruflo.time, "sleep", sleeps.append)

    # success
    monkeypatch.setattr(ruflo.urllib.request, "urlopen", lambda url, timeout=0: FakeResponse("# hello"))
    assert ruflo._fetch_url("https://example.invalid/SKILL.md") == "# hello"

    # 404 returns None immediately, no retries
    def raise404(url, timeout=0):
        raise ruflo.urllib.error.HTTPError(url, 404, "nf", {}, None)

    monkeypatch.setattr(ruflo.urllib.request, "urlopen", raise404)
    assert ruflo._fetch_url("https://example.invalid/x") is None
    assert sleeps == []

    # transient failure retries with exponential backoff, then gives up with None
    calls = []

    def flaky(url, timeout=0):
        calls.append(url)
        raise OSError("boom")

    monkeypatch.setattr(ruflo.urllib.request, "urlopen", flaky)
    assert ruflo._fetch_url("https://example.invalid/y", retries=3, delay=1.0) is None
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]


def test_fetch_ruflo_skills_fetch_skill_regular_and_dual_mode(ruflo, monkeypatch):
    requested = []

    def fakeFetch(url, retries=3, delay=1.0):
        requested.append(url)
        if url.endswith("missing/SKILL.md"):
            return None
        return f"content of {url.rsplit('/', 1)[-1]}"

    monkeypatch.setattr(ruflo, "_fetch_url", fakeFetch)

    ok = ruflo.fetch_skill("agentdb-learning")
    assert ok["fetch_status"] == "ok"
    assert ok["suite"] == "agentdb"
    assert ok["content"] == "content of SKILL.md"
    assert requested[-1] == f"{ruflo.BASE_RAW}/agentdb-learning/SKILL.md"

    gone = ruflo.fetch_skill("missing")
    assert gone["fetch_status"] == "not_found" and gone["content"] is None

    dual = ruflo.fetch_skill("dual-mode")
    assert dual["fetch_status"] == "ok"
    assert dual["sub_skills"] == ruflo.DUAL_MODE_FILES
    for fname in ruflo.DUAL_MODE_FILES:
        assert f"## {fname}" in dual["content"]


@pytest.mark.filterwarnings("ignore:datetime.datetime.utcnow:DeprecationWarning")  # raised inside the unmodified subject
def test_fetch_ruflo_skills_build_and_main_write_only_to_tmp(ruflo, monkeypatch, tmp_path, capsys):
    def fakeFetchSkill(name, verbose=False):
        status = "not_found" if name == "browser" else "ok"
        return {"id": name, "fetch_status": status, "content": None if status != "ok" else "x"}

    monkeypatch.setattr(ruflo, "fetch_skill", fakeFetchSkill)

    out = tmp_path / "nested" / "ruflo.json"
    code = ruflo.main(["--out", str(out)])
    assert code == 1, "a missing skill makes the run exit nonzero"
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["total"] == len(ruflo.SKILL_DIRS)
    assert result["fetched_ok"] == len(ruflo.SKILL_DIRS) - 1
    assert result["missing"] == ["browser"]
    assert result["source"] == "https://github.com/ruvnet/ruflo"
    assert len(result["skills"]) == len(ruflo.SKILL_DIRS)
    assert "WARNING" in capsys.readouterr().out

    # all present: exit 0
    monkeypatch.setattr(ruflo, "fetch_skill", lambda name, verbose=False: {"id": name, "fetch_status": "ok", "content": "x"})
    assert ruflo.build(tmp_path / "all.json", verbose=False) == 0


def test_fetch_ruflo_skills_help_exits_zero_without_network():
    proc = subprocess.run(
        [sys.executable, str(rufloScript), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=repoRoot,
    )
    assert proc.returncode == 0
    assert "--out" in proc.stdout and "--verbose" in proc.stdout


# ---------------------------------------------------------------------------
# scripts/check_rank_vocabulary.py
# ---------------------------------------------------------------------------
# Its top level conditionally calls sys.stdout/sys.stderr.reconfigure(...) when the
# stream encoding is not utf-8. To load it safely we hand it private in-memory
# streams, which also lets us assert both sides of that conditional.


def loadRankVocabulary(encoding: str, monkeypatch):
    fakeOut = io.TextIOWrapper(io.BytesIO(), encoding=encoding)
    fakeErr = io.TextIOWrapper(io.BytesIO(), encoding=encoding)
    with monkeypatch.context() as scoped:
        scoped.setattr(sys, "stdout", fakeOut)
        scoped.setattr(sys, "stderr", fakeErr)
        module = loadScript(rankScript, "checkRankVocabularyUnderTest")
    return module, fakeOut, fakeErr


def test_check_rank_vocabulary_reconfigures_non_utf8_streams(monkeypatch):
    module, fakeOut, fakeErr = loadRankVocabulary("latin-1", monkeypatch)
    for stream in (fakeOut, fakeErr):
        assert stream.encoding == "utf-8"
        assert stream.errors == "replace"
    assert module.BANNED_PATTERNS


def test_check_rank_vocabulary_leaves_utf8_streams_alone(monkeypatch):
    module, fakeOut, fakeErr = loadRankVocabulary("utf-8", monkeypatch)
    for stream in (fakeOut, fakeErr):
        assert stream.encoding == "utf-8"
        assert stream.errors == "strict", "utf-8 streams must not be reconfigured"
    assert module.DOCS_ONLY_BANNED_PATTERNS


@pytest.fixture
def rank(monkeypatch):
    return loadRankVocabulary("utf-8", monkeypatch)[0]


def matchedLabels(rank, line: str, docsOnly: bool = False) -> set[str]:
    patterns = rank.DOCS_ONLY_BANNED_PATTERNS if docsOnly else rank.BANNED_PATTERNS
    return {label for pattern, label, _why in patterns if pattern.search(line)}


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("The old Transcendent rank", "Transcendent"),
        ("a Hardened skill", "Hardened"),
        ("a Fusion Skill here", "Fusion Skill"),
        ("a Basic   Skill here", "Basic Skill"),
        ("this Extra skill is taxonomy", "Extra skill"),
        ("an Ultimate skill is taxonomy", "Ultimate skill"),
        ("type: extra", "type=extra"),
        ("type = ultimate", "type=ultimate"),
        ("the Apex Tier", "apex tier"),
        ("Fusion Magnitude of the suite", "fusion magnitude"),
        ("the Composition Score", "composition score"),
        ("a Structure Score input", "structure score"),
    ],
)
def test_check_rank_vocabulary_banned_patterns_fire(rank, line, label):
    assert label in matchedLabels(rank, line)


@pytest.mark.parametrize(
    "line",
    [
        "Unlocks the Extra Skill rank at 4 stars",
        "Reaches Ultimate Skill status",
        "type: basic",
        "type: fusion",
        "The Fusion Score is the structural scalar",
        "Awakened, Named, Evolved",
    ],
)
def test_check_rank_vocabulary_valid_vocabulary_passes(rank, line):
    assert matchedLabels(rank, line) == set()


def test_check_rank_vocabulary_docs_only_patterns(rank):
    assert matchedLabels(rank, "ships with G7 trust", docsOnly=True) == {"G7"}
    assert matchedLabels(rank, "the G8 plan", docsOnly=True) == {"G8"}
    assert matchedLabels(rank, "G70 is not a codename", docsOnly=True) == set()


def test_check_rank_vocabulary_path_classifiers(rank):
    assert rank.is_hard_excluded("scripts/anything.md")
    assert rank.is_hard_excluded("docs/badges/x.md")
    assert rank.is_hard_excluded("docs/page.html")
    assert not rank.is_hard_excluded("docs/guide.md")

    assert rank.is_allowlisted("CONTEXT.md")
    assert rank.is_allowlisted("docs/archive/anything/new.md"), "subtree allowlist"
    assert not rank.is_allowlisted("docs/guide.md")

    assert rank.is_docs_scope("README.md")
    assert rank.is_docs_scope("docs/guide.md")
    assert not rank.is_docs_scope("registry/x.md")
    assert not rank.is_docs_scope("founder/handovers/x.md")

    assert rank.is_docs_only_allowlisted("CHANGELOG.md")
    assert rank.is_docs_only_allowlisted("CONTEXT.md")
    assert not rank.is_docs_only_allowlisted("docs/guide.md")


def buildSyntheticRepo(root: Path, violating: bool) -> None:
    (root / "registry").mkdir()
    (root / "docs" / "badges").mkdir(parents=True)
    (root / "founder" / "handovers").mkdir(parents=True)
    (root / "registry" / "clean.json").write_text('{"type": "fusion", "rank": "Extra Skill"}\n', encoding="utf-8")
    (root / "docs" / "guide.md").write_text("Reach the Extra Skill rank.\n", encoding="utf-8")
    # allowlisted pre-existing violation must warn, never fail
    (root / "CONTEXT.md").write_text("Banned: Transcendent\n", encoding="utf-8")
    # hard-excluded path is never scanned
    (root / "docs" / "badges" / "note.md").write_text("Hardened\n", encoding="utf-8")
    if violating:
        (root / "registry" / "bad.json").write_text('{"note": "Transcendent"}\n', encoding="utf-8")
        (root / "docs" / "public.md").write_text("line one\nThe G7 codename leaks\n", encoding="utf-8")
        (root / "founder" / "handovers" / "memo.md").write_text("G7 is fine here\nBut a Basic Skill is not\n", encoding="utf-8")


def test_check_rank_vocabulary_scan_clean_synthetic_repo(rank, tmp_path):
    buildSyntheticRepo(tmp_path, violating=False)
    hard, soft = rank.scan(tmp_path)
    assert hard == []
    assert {entry[0] for entry in soft} == {"CONTEXT.md"}


def test_check_rank_vocabulary_scan_flags_violations_with_locations(rank, tmp_path):
    buildSyntheticRepo(tmp_path, violating=True)
    hard, soft = rank.scan(tmp_path)

    found = {(path, lineno, label) for path, lineno, _snippet, label, _why in hard}
    assert ("registry/bad.json", 1, "Transcendent") in found
    assert ("docs/public.md", 2, "G7") in found
    assert ("founder/handovers/memo.md", 2, "Basic Skill") in found
    # G7 is docs-only: the same codename in founder/handovers must not be flagged
    assert ("founder/handovers/memo.md", 1, "G7") not in found
    assert {entry[0] for entry in soft} == {"CONTEXT.md"}
    # hard-excluded and clean files never appear
    assert all(not path.startswith("docs/badges/") and path != "registry/clean.json" for path, *_ in hard + soft)


def test_check_rank_vocabulary_main_exit_codes(rank, monkeypatch, capsys):
    entry = ("docs/x.md", 3, "a Hardened thing", "Hardened", "old 4 star rank name")

    monkeypatch.setattr(rank, "scan", lambda root: ([], []))
    assert rank.main() == 0
    assert "RESULT: PASS" in capsys.readouterr().out

    monkeypatch.setattr(rank, "scan", lambda root: ([], [("CONTEXT.md", 1, "Hardened", "Hardened", "why")]))
    assert rank.main() == 0
    out = capsys.readouterr().out
    assert "PRE-EXISTING VIOLATIONS" in out and "RESULT: PASS" in out

    monkeypatch.setattr(rank, "scan", lambda root: ([entry], []))
    assert rank.main() == 1
    out = capsys.readouterr().out
    assert "[FAIL] docs/x.md:3" in out and "RESULT: FAIL" in out


# ---------------------------------------------------------------------------
# scripts/crawlers/huggingface/crawler.py
# ---------------------------------------------------------------------------
# The module inserts scripts/crawlers into sys.path and imports `common.*` plus
# `requests` at top level. The fixture keeps that from leaking into other tests.


@pytest.fixture
def hf(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    module = loadScript(hfScript, "huggingfaceCrawlerUnderTest")
    yield module
    for name in set(sys.modules) - before:
        if name == "common" or name.startswith("common."):
            del sys.modules[name]


def fakeRequests(payload=None, status=200, boom=None, seen=None):
    def get(url, params=None, timeout=None):
        if seen is not None:
            seen.append((url, params, timeout))
        if boom is not None:
            raise boom
        return SimpleNamespace(status_code=status, json=lambda: payload)

    return SimpleNamespace(get=get)


def test_huggingface_crawler_loads_with_expected_tables(hf):
    assert hf.HF_API == "https://huggingface.co/api"
    assert set(hf.TASKS_TO_CRAWL) == set(hf.TASK_TO_SKILL)
    assert hf.TASK_TO_SKILL["summarization"] == "summarize"
    assert crawlersDir.as_posix() in {Path(p).resolve().as_posix() for p in sys.path}


def test_huggingface_crawler_crawl_models_transforms_payload(hf, monkeypatch):
    seen = []
    payload = [
        {"id": "acme/Great Model v2", "downloads": 500000, "likes": 300, "lastModified": "2020-01-01T00:00:00Z", "description": "x" * 400},
        {"modelId": "other/legacy-key", "downloads": 20000, "likes": 5},
        {"id": "acme/tiny", "downloads": 999, "likes": 1000},  # under the download floor
    ]
    monkeypatch.setattr(hf, "requests", fakeRequests(payload=payload, seen=seen))

    result = hf.crawl_models("summarization", limit=7)

    url, params, timeout = seen[0]
    assert url == "https://huggingface.co/api/models"
    assert params == {"pipeline_tag": "summarization", "sort": "downloads", "limit": 7}
    assert timeout == 30

    assert len(result) == 2, "the sub-1000-download model is filtered out"
    first, second = result
    assert first["id"] == "summarize-hf-great-model-v2"
    assert first["name"] == "Great Model v2 (summarization)"
    assert len(first["description"]) == 200, "description is truncated to 200 chars"
    assert first["status"] == "provisional"
    assert first["evidence"][0]["source"] == "https://huggingface.co/acme/Great Model v2"
    assert first["evidence"][0]["source_type"] == "huggingface"
    assert second["id"] == "summarize-hf-legacy-key"
    assert second["description"] == "HuggingFace model for summarization"


def test_huggingface_crawler_crawl_models_handles_failures(hf, monkeypatch, capsys):
    monkeypatch.setattr(hf, "requests", fakeRequests(status=503))
    assert hf.crawl_models("summarization") == []
    assert "503" in capsys.readouterr().out

    monkeypatch.setattr(hf, "requests", fakeRequests(boom=TimeoutError("slow")))
    assert hf.crawl_models("summarization") == []
    assert "Error crawling HuggingFace models" in capsys.readouterr().out

    # a task with no skill mapping yields nothing even when the API returns models
    monkeypatch.setattr(hf, "requests", fakeRequests(payload=[{"id": "a/b", "downloads": 10**6, "likes": 1}]))
    assert hf.crawl_models("not-a-mapped-task") == []


def test_huggingface_crawler_main_dedups_and_proposes(hf, monkeypatch, capsys):
    def fakeCrawl(task, limit=20):
        # every task returns the same id twice plus one id unique to the task
        return [{"id": "dup"}, {"id": "dup"}, {"id": f"only-{task}"}]

    captured = {}

    def fakeDedup(candidates):
        captured["deduped"] = list(candidates)
        return [c for c in candidates if c["id"] != "only-summarization"]

    def fakePropose(candidates, source_name):
        captured["proposed"] = (list(candidates), source_name)

    monkeypatch.setattr(hf, "crawl_models", fakeCrawl)
    monkeypatch.setattr(hf, "deduplicate", fakeDedup)
    monkeypatch.setattr(hf, "write_proposals", fakePropose)

    hf.main()

    ids = [c["id"] for c in captured["deduped"]]
    assert ids.count("dup") == 1, "duplicates across tasks collapse before dedup"
    assert len(ids) == 1 + len(hf.TASKS_TO_CRAWL)
    proposed, source = captured["proposed"]
    assert source == "huggingface"
    assert "only-summarization" not in {c["id"] for c in proposed}
    assert f"Found {len(ids)} raw candidates" in capsys.readouterr().out


def test_huggingface_crawler_main_skips_proposals_when_nothing_new(hf, monkeypatch):
    monkeypatch.setattr(hf, "crawl_models", lambda task, limit=20: [{"id": "x"}])
    monkeypatch.setattr(hf, "deduplicate", lambda candidates: [])

    def mustNotWrite(*args, **kwargs):
        raise AssertionError("write_proposals must not run with zero candidates")

    monkeypatch.setattr(hf, "write_proposals", mustNotWrite)
    hf.main()
