"""CLI regressions for the counted HTML-sink debt ratchet."""

import importlib.util
import json
import runpy
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
SINK = "el.innerHTML = `<b>${name}</b>`;"


@pytest.fixture
def scanner(tmp_path, monkeypatch):
    """Copy the real CLI so its script-relative root scans only fixture docs."""
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "check_html_sinks.py"
    shutil.copyfile(ROOT / "scripts/check_html_sinks.py", script)
    (tmp_path / "docs").mkdir()
    return script


def run_scan(scanner, source, findings=None, *args):
    (scanner.parents[1] / "docs/example.js").write_text(source, encoding="utf-8")
    if findings is not None:
        scanner.with_name("html_sinks_baseline.json").write_text(
            json.dumps({"findings": findings}), encoding="utf-8"
        )
    return subprocess.run(
        [sys.executable, str(scanner), *args], capture_output=True, text=True, timeout=15
    )


def test_new_sink_fails(scanner):
    (scanner.parents[1] / "docs/other.js").write_text("", encoding="utf-8")
    result = run_scan(scanner, SINK, {"docs/other.js": {"innerhtml-template": 1}})
    assert result.returncode == 1
    assert "[FAIL] docs/example.js" in result.stdout
    assert "1 un-baselined unsafe sink(s) found" in result.stdout


def test_baselined_sink_passes(scanner):
    result = run_scan(scanner, SINK, {"docs/example.js": {"innerhtml-template": 1}})
    assert result.returncode == 0
    assert "[DEBT] docs/example.js" in result.stdout
    assert "PASS (carried baseline debt: 1 sink(s)); new sinks are blocked" in result.stdout


def test_exceeding_baseline_fails(scanner):
    result = run_scan(scanner, SINK + "\n" + SINK,
                      {"docs/example.js": {"innerhtml-template": 1}})
    assert result.returncode == 1
    assert result.stdout.count("[DEBT] docs/example.js") == 1
    assert result.stdout.count("[FAIL] docs/example.js") == 1


@pytest.mark.parametrize("second, label", [
    (SINK, "innerhtml-template"),
    ("el.outerHTML = `<i>${name}</i>`;", "innerhtml-template"),
    ("document.write(`<i>${name}</i>`);", "document-write-dynamic"),
])
def test_multiple_sinks_on_one_line_count(scanner, second, label):
    result = run_scan(scanner, SINK + " " + second,
                      {"docs/example.js": {"innerhtml-template": 1}})
    assert result.returncode == 1
    assert result.stdout.count("[DEBT] docs/example.js") == 1
    assert result.stdout.count("[FAIL] docs/example.js") == 1
    assert f"[{label}]" in result.stdout


def test_baseline_does_not_cover_different_label(scanner):
    result = run_scan(scanner, SINK, {"docs/example.js": {"innerhtml-concat": 1}})
    assert result.returncode == 1


@pytest.mark.parametrize("comment", [
    "// gaia-html-sink-ok: build-time constant",
    "/* gaia-html-sink-ok: fixed enum */",
])
def test_valid_suppression_passes(scanner, comment):
    result = run_scan(scanner, SINK + " " + comment, {})
    assert result.returncode == 0
    assert "RESULT: PASS — 0 unsafe HTML sinks." in result.stdout


@pytest.mark.parametrize("reason", ["", " ", "\t   "])
def test_suppression_requires_reason(scanner, reason):
    result = run_scan(scanner, SINK + " // gaia-html-sink-ok:" + reason, {})
    assert result.returncode == 1


@pytest.mark.parametrize("comment", [
    "/* gaia-html-sink-ok: */",
    "/* gaia-html-sink-ok: \t */",
    "/* gaia-html-sink-ok: fixed enum */ moreCode();",
])
def test_invalid_block_suppression_fails(scanner, comment):
    result = run_scan(scanner, SINK + " " + comment, {})
    assert result.returncode == 1


def test_marker_inside_string_does_not_suppress(scanner):
    result = run_scan(scanner, 'const x = "gaia-html-sink-ok: foo"; ' + SINK, {})
    assert result.returncode == 1


@pytest.mark.parametrize("quote", ["'", '"', "`"])
@pytest.mark.parametrize("marker", [
    "// gaia-html-sink-ok: reason",
    "/* gaia-html-sink-ok: reason */",
])
@pytest.mark.parametrize("escaped", [False, True], ids=["plain", "escaped-quote"])
def test_quoted_comment_does_not_suppress(scanner, quote, marker, escaped):
    prefix = "\\" + quote if escaped else ""
    source = SINK + f" const s = {quote}{prefix}{marker}{quote};"
    result = run_scan(scanner, source, {})
    assert result.returncode == 1
    assert "[FAIL] docs/example.js" in result.stdout


@pytest.mark.parametrize("regex", [
    "/[// gaia-html-sink-ok: fake]/",
    r"/[\/ gaia-html-sink-ok: fake]/",
    "/[/* gaia-html-sink-ok: fake */]/",
    r"/\/\/ gaia-html-sink-ok: fake/",
])
@pytest.mark.parametrize("prefix", [
    "const r = ", "function f() { return ", "const f = () => ", "return ",
    "yield ", "typeof ", "delete ", "void ", "throw ", "instanceof ",
    "in ", "of ", "new ", "await ", "case ", "default ", "else ", "do ",
    "value < ", "value > ", "if (ok) ", "while (ok) ",
    "for (; ok;) ", "for (const x of xs) ", "if (check(ok)) ",
])
def test_regex_marker_cannot_suppress(scanner, regex, prefix):
    source = "el.innerHTML = '<b>' + user; " + prefix + regex + ".test(user);"
    result = run_scan(scanner, source, {})
    assert result.returncode == 1
    assert "[FAIL] docs/example.js" in result.stdout


@pytest.mark.parametrize("expression", [
    r"/[\/]/.test(user)",
    "/[//]/.test(user)",
    r"/escaped\//.test(user)",
    "total / count",
    "42 / count",
    "'42' / count",
    '"42" / count',
    "`42` / count",
    "getTotal() / count",
    "(total) / count",
    "totals[0] / count",
    "total / count / scale",
    "total++ / count",
])
def test_real_comment_after_regex_or_division_suppresses(scanner, expression):
    source = SINK + " const r = " + expression + "; // gaia-html-sink-ok: fixed enum"
    assert run_scan(scanner, source, {}).returncode == 0


@pytest.mark.parametrize("quote", ["'", '"', "`"])
def test_comment_after_escaped_backslash_suppresses(scanner, quote):
    source = SINK + f" const s = {quote}\\\\{quote}; // gaia-html-sink-ok: fixed enum"
    assert run_scan(scanner, source, {}).returncode == 0


@pytest.mark.parametrize("source", [
    'el.innerHTML = `${"`// gaia-html-sink-ok: fake"}`;',
    'el.innerHTML = `${`nested ${"`// gaia-html-sink-ok: fake"}`}`;',
    'el.innerHTML = `${{value: `nested ${"fake"}`}.value}`;',
    'el.innerHTML = `${value // gaia-html-sink-ok: fake',
    'el.innerHTML = `${value /* gaia-html-sink-ok: fake */',
    'el.innerHTML = `${value /* ` // fake */}`;',
])
def test_template_expression_cannot_suppress(scanner, source):
    result = run_scan(scanner, source, {})
    assert result.returncode == 1
    assert "[FAIL] docs/example.js" in result.stdout


@pytest.mark.parametrize("comment", [
    "// gaia-html-sink-ok: fixed enum",
    "/* gaia-html-sink-ok: fixed enum */",
])
def test_nested_template_with_real_trailing_comment(scanner, comment):
    source = 'el.innerHTML = `${{value: `nested ${"fake"}`}.value}`; '
    assert run_scan(scanner, source + comment, {}).returncode == 0


@pytest.mark.parametrize("isHtml", [False, True], ids=["javascript", "inline-script"])
@pytest.mark.parametrize("body", [
    "${el.innerHTML = '<b>' + user} // gaia-html-sink-ok: fake",
    "${el.innerHTML = '<b>' + user // gaia-html-sink-ok: fake\n}",
    "${el.innerHTML = '<b>' + user /* gaia-html-sink-ok: fake */}",
])
def test_multiline_template_marker_cannot_suppress(scanner, isHtml, body):
    source = "const t = `\n" + body + "\n`;"
    if isHtml:
        (scanner.parents[1] / "docs/example.html").write_text(
            "<script>\n" + source + "\n</script>", encoding="utf-8"
        )
        source = ""
    result = run_scan(scanner, source, {})
    assert result.returncode == 1
    assert "[innerhtml-concat]" in result.stdout


def test_multiline_template_restores_top_level_suppression(scanner):
    source = "const t = `\n${{value: `nested ${user}`}.value}\n`;\n"
    source += SINK + " // gaia-html-sink-ok: fixed enum"
    assert run_scan(scanner, source, {}).returncode == 0


def test_script_blocks_have_independent_lexical_state(scanner):
    (scanner.parents[1] / "docs/example.html").write_text(
        "<script>const t = `unterminated</script>\n<script>" + SINK
        + " // gaia-html-sink-ok: fixed enum\n</script>", encoding="utf-8"
    )
    assert run_scan(scanner, "", {}).returncode == 0


def test_nontrailing_block_contents_cannot_suppress(scanner):
    source = SINK + " /* // gaia-html-sink-ok: not trailing */ moreCode();"
    assert run_scan(scanner, source, {}).returncode == 1


@pytest.mark.parametrize("findings", [None, {}], ids=["missing", "empty"])
def test_zero_baseline_hard_fails(scanner, findings):
    result = run_scan(scanner, SINK, findings)
    assert result.returncode == 1
    assert "HARD-FAIL" in result.stdout
    assert "empty — zero budget" in result.stdout


def test_clean_file_passes(scanner):
    result = run_scan(scanner, "el.textContent = name;", {})
    assert result.returncode == 0
    assert "RESULT: PASS — 0 unsafe HTML sinks." in result.stdout


def test_custom_baseline(scanner, tmp_path):
    baseline = tmp_path / "custom.json"
    baseline.write_text(json.dumps({"findings": {
        "docs/example.js": {"innerhtml-template": 1}
    }}), encoding="utf-8")
    result = run_scan(scanner, SINK, {}, "--baseline", str(baseline))
    assert result.returncode == 0
    assert "carried baseline debt: 1 sink(s)" in result.stdout


def test_dump_baseline(scanner):
    result = run_scan(scanner, SINK + "\n" + SINK, {}, "--dump-baseline")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["findings"] == {"docs/example.js": {"innerhtml-template": 2}}
    assert "never grow it" in payload["about"]
    assert payload["generated"]


def git(scanner, *args):
    return subprocess.run(
        ["git", *args], cwd=scanner.parents[1], check=True,
        capture_output=True, text=True, timeout=15,
    ).stdout.strip()


@pytest.fixture
def baseline_repo(scanner):
    git(scanner, "init", "-b", "fixture-base")
    git(scanner, "config", "user.email", "fixture@example.invalid")
    git(scanner, "config", "user.name", "Fixture")
    baseline = scanner.with_name("html_sinks_baseline.json")
    baseline.write_text(json.dumps({"findings": {
        "docs/example.js": {"innerhtml-template": 1}
    }}), encoding="utf-8")
    (scanner.parents[1] / "docs/example.js").write_text("", encoding="utf-8")
    git(scanner, "add", "scripts", "docs")
    git(scanner, "commit", "-m", "Initial baseline")
    git(scanner, "update-ref", "refs/remotes/origin/main", "HEAD")
    return scanner


@pytest.mark.parametrize("findings", [
    {"docs/example.js": {"innerhtml-template": 2}},
    {"docs/example.js": {"innerhtml-template": 1, "innerhtml-concat": 1}},
    {"docs/new.js": {"innerhtml-template": 1}},
])
def test_baseline_growth_rejected(baseline_repo, findings):
    (baseline_repo.parents[1] / "docs/new.js").write_text("", encoding="utf-8")
    result = run_scan(baseline_repo, "el.textContent = name;", findings,
                      "--check-baseline-growth")
    assert result.returncode == 1
    assert "[FAIL] Baseline grew for docs/" in result.stdout


@pytest.mark.parametrize("count", [0, 1])
def test_baseline_same_or_smaller_passes(baseline_repo, count):
    findings = {"docs/example.js": {"innerhtml-template": count}} if count else {}
    result = run_scan(baseline_repo, "el.textContent = name;", findings,
                      "--check-baseline-growth", "--base-ref", "HEAD")
    assert result.returncode == 0, result.stderr


def test_baseline_growth_explicit_previous_revision(baseline_repo):
    scanner = baseline_repo
    run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 2}})
    git(scanner, "add", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Grow baseline")
    result = run_scan(scanner, "", None,
                      "--check-baseline-growth", "--base-ref", "HEAD~1")
    assert result.returncode == 1
    assert "[FAIL] Baseline grew for docs/example.js" in result.stdout
    assert "1 -> 2" in result.stdout


def test_missing_base_baseline_without_sinks_is_zero_budget(baseline_repo):
    scanner = baseline_repo
    git(scanner, "rm", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Remove baseline")
    result = run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 1}},
                      "--check-baseline-growth", "--base-ref", "HEAD")
    assert result.returncode == 1
    assert "[FAIL] Baseline grew for docs/example.js" in result.stdout


def test_invalid_base_ref_warns_and_continues(baseline_repo):
    result = run_scan(baseline_repo, "", {}, "--check-baseline-growth",
                      "--base-ref", "refs/heads/nonexistent")
    assert result.returncode == 0
    assert "[WARN] Cannot check baseline growth" in result.stderr


@pytest.mark.parametrize("source, code", [("", 0), (SINK, 1)])
def test_outside_git_warns_and_still_checks_sinks(scanner, source, code):
    result = run_scan(scanner, source, {}, "--check-baseline-growth")
    assert result.returncode == code
    assert "[WARN] Cannot check baseline growth" in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_base_takes_precedence_over_main(baseline_repo, monkeypatch):
    scanner = baseline_repo
    branch = "dev/steward-campaign-2026-11-05"
    git(scanner, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
    run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 2}})
    git(scanner, "add", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Inflate budget")
    git(scanner, "update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.setenv("GITHUB_BASE_REF", branch)
    result = run_scan(scanner, SINK, None, "--check-baseline-growth")
    assert result.returncode == 1
    assert "1 -> 2" in result.stdout


def test_unresolvable_ci_pr_base_does_not_fall_back(baseline_repo, monkeypatch):
    scanner = baseline_repo
    git(scanner, "commit", "--allow-empty", "-m", "Feature tip")
    assert git(scanner, "rev-parse", "--verify", "HEAD~1^{commit}")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_BASE_REF", "missing-pr-base")
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    assert "CI PR event requires pull_request.base.sha in event payload" in result.stderr
    assert "continuing sink scan" not in result.stderr
    assert "Traceback" not in result.stderr


def test_external_baseline_growth_has_explicit_error(scanner, tmp_path):
    baseline = tmp_path.parent / (tmp_path.name + "-external.json")
    baseline.write_text(json.dumps({"findings": {}}), encoding="utf-8")
    try:
        result = run_scan(scanner, "", {}, "--check-baseline-growth",
                          "--baseline", str(baseline))
        assert result.returncode == 1
        assert f"baseline file '{baseline}' is outside repository root" in result.stderr
        assert "Traceback" not in result.stderr
    finally:
        baseline.unlink()


def test_default_falls_back_to_previous_revision(baseline_repo):
    scanner = baseline_repo
    git(scanner, "update-ref", "-d", "refs/remotes/origin/main")
    run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 2}})
    git(scanner, "add", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Inflate budget")
    result = run_scan(scanner, "", None, "--check-baseline-growth")
    assert result.returncode == 1
    assert "1 -> 2" in result.stdout


@pytest.mark.parametrize("base", [None, "refs/heads/nonexistent"])
def test_unresolvable_base_fails_in_ci(scanner, monkeypatch, base):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    args = ["--check-baseline-growth"]
    if base:
        args.extend(["--base-ref", base])
    result = run_scan(scanner, "", {}, *args)
    assert result.returncode == 1
    assert "[FAIL] Cannot check baseline growth: Git base unavailable" in result.stderr
    assert "continuing sink scan" not in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("event", ["push", "workflow_dispatch", None])
def test_unrelated_ci_merge_with_unresolvable_base_fails_closed(
        baseline_repo, monkeypatch, event):
    scanner = baseline_repo
    git(scanner, "checkout", "-b", "unrelated-feature")
    git(scanner, "commit", "--allow-empty", "-m", "Unrelated feature")
    git(scanner, "checkout", "fixture-base")
    git(scanner, "merge", "--no-ff", "unrelated-feature", "-m", "Unrelated merge")
    assert git(scanner, "rev-parse", "--verify", "HEAD^1^{commit}")
    assert git(scanner, "rev-parse", "--verify", "HEAD^2^{commit}")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_BASE_REF", "missing-pr-base")
    if event:
        monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    expected = {
        "push": "CI push event requires valid 'before' commit SHA in event payload",
        "workflow_dispatch": "Git base unavailable",
        None: "CI PR event requires pull_request.base.sha in event payload",
    }[event]
    assert expected in result.stderr
    assert "continuing sink scan" not in result.stderr
    assert "Traceback" not in result.stderr


def test_depth_two_merge_uses_first_parent(baseline_repo, tmp_path, monkeypatch):
    scanner = baseline_repo
    git(scanner, "checkout", "-b", "feature")
    run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 2}})
    git(scanner, "add", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Inflate feature budget")
    git(scanner, "checkout", "-b", "pr-merge", "HEAD~1")
    # A distinct base tip makes both parents shallow boundaries at depth two.
    (scanner.parents[1] / "base.txt").write_text("base change", encoding="utf-8")
    git(scanner, "add", "base.txt")
    git(scanner, "commit", "-m", "Advance base")
    git(scanner, "merge", "--no-ff", "feature", "-m", "Synthetic PR merge")
    checkout = tmp_path / "depth-two"
    git(scanner, "clone", "--depth=2", "--single-branch", "--branch", "pr-merge",
        scanner.parents[1].as_uri(), str(checkout))
    shallowScanner = checkout / "scripts/check_html_sinks.py"
    (checkout / "docs").mkdir(exist_ok=True)
    assert git(shallowScanner, "rev-parse", "--is-shallow-repository") == "true"
    assert git(shallowScanner, "rev-parse", "--verify", "HEAD^1^{commit}")
    assert git(shallowScanner, "rev-parse", "--verify", "HEAD^2^{commit}")
    assert git(shallowScanner, "rev-list", "--count", "HEAD") == "3"
    assert git(shallowScanner, "for-each-ref", "--format=%(refname)",
               "refs/remotes/origin/main") == ""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_BASE_REF", "unfetched-base")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps({"pull_request": {"base": {
        "sha": git(shallowScanner, "rev-parse", "HEAD^1")
    }}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(shallowScanner, "", None, "--check-baseline-growth")
    assert result.returncode == 1
    assert "[FAIL] Baseline grew for docs/example.js" in result.stdout
    assert "1 -> 2" in result.stdout
    assert "Cannot check baseline growth" not in result.stderr


@pytest.mark.parametrize("payload", [False, True], ids=["no-payload", "unavailable-sha"])
def test_ci_pr_unrelated_merge_fails_closed(baseline_repo, monkeypatch, tmp_path, payload):
    scanner = baseline_repo
    git(scanner, "checkout", "-b", "unrelated")
    git(scanner, "commit", "--allow-empty", "-m", "Unrelated change")
    git(scanner, "checkout", "fixture-base")
    git(scanner, "merge", "--no-ff", "unrelated", "-m", "Unrelated merge")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_BASE_REF", "missing-base")
    if payload:
        eventPath = tmp_path / "event.json"
        eventPath.write_text(json.dumps({"pull_request": {"base": {
            "sha": "a" * 40
        }}}), encoding="utf-8")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    expected = ("Cannot resolve CI PR base ref" if payload else
                "CI PR event requires pull_request.base.sha in event payload")
    assert expected in result.stderr


@pytest.mark.parametrize("payload", [
    None, "{invalid", "{}", '{"pull_request": {"base": {}}}',
    '{"pull_request": null}', "[]",
], ids=["missing-path", "invalid-json", "missing-pr", "missing-sha", "null-pr", "non-object"])
def test_ci_pr_missing_sha_rejects_existing_base_ref(baseline_repo, monkeypatch, tmp_path, payload):
    scanner = baseline_repo
    assert git(scanner, "rev-parse", "--verify", "origin/main^{commit}")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    if payload is not None:
        eventPath = tmp_path / "event.json"
        eventPath.write_text(payload, encoding="utf-8")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    assert "CI PR event requires pull_request.base.sha in event payload" in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_pr_unresolvable_sha_rejects_existing_base_ref(baseline_repo, monkeypatch, tmp_path):
    scanner = baseline_repo
    assert git(scanner, "rev-parse", "--verify", "origin/main^{commit}")
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps({"pull_request": {"base": {
        "sha": "a" * 40
    }}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    assert "Cannot resolve CI PR base ref" in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_pr_uses_event_base_sha(baseline_repo, monkeypatch, tmp_path):
    scanner = baseline_repo
    baseSha = git(scanner, "rev-parse", "HEAD")
    run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 2}})
    git(scanner, "add", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Inflate baseline")
    git(scanner, "update-ref", "refs/remotes/origin/main", "HEAD")
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps({"pull_request": {"base": {
        "sha": baseSha
    }}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(scanner, "", None, "--check-baseline-growth")
    assert result.returncode == 1
    assert "1 -> 2" in result.stdout
    assert "Cannot check baseline growth" not in result.stderr


@pytest.mark.parametrize("before", ["event-sha"])
def test_ci_push_base(baseline_repo, monkeypatch, tmp_path, before):
    scanner = baseline_repo
    baseSha = git(scanner, "rev-parse", "HEAD")
    run_scan(scanner, "", {"docs/example.js": {"innerhtml-template": 2}})
    git(scanner, "add", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Inflate baseline")
    if before == "event-sha":
        # Ensure HEAD~1 is not the event base; the payload must take precedence.
        git(scanner, "commit", "--allow-empty", "-m", "Another push commit")
        before = baseSha
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps({"before": before}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(scanner, "", None, "--check-baseline-growth")
    assert result.returncode == 1
    assert "1 -> 2" in result.stdout


@pytest.mark.parametrize("before", ["a" * 40, "invalid"])
def test_ci_push_unresolvable_before_does_not_fall_back(baseline_repo, monkeypatch, tmp_path, before):
    scanner = baseline_repo
    git(scanner, "commit", "--allow-empty", "-m", "Push tip")
    assert git(scanner, "rev-parse", "--verify", "HEAD~1^{commit}")
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps({"before": before}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    assert (f"CI push base commit {before} cannot be resolved in git" if len(before) == 40 else
            "CI push event requires valid 'before' commit SHA in event payload") in result.stderr
    assert "continuing sink scan" not in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_initial_push_without_parent_uses_zero_baseline(baseline_repo, monkeypatch, tmp_path):
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps({"before": "0" * 40}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    result = run_scan(baseline_repo, "", {"docs/example.js": {"innerhtml-template": 1}},
                      "--check-baseline-growth")
    assert result.returncode == 1
    assert "new baseline file entry" in result.stdout
    result = run_scan(baseline_repo, "", {}, "--check-baseline-growth")
    assert result.returncode == 0


@pytest.mark.parametrize("source", [
    "if (\n el.innerHTML = '<b>' + user\n) /[// gaia-html-sink-ok: fake]/.test(user);",
    "if (\n el.innerHTML = '<b>' + user) /[// gaia-html-sink-ok: fake]/.test(user);",
    "el.innerHTML = '<b>' + user; if (ok) {} /[// gaia-html-sink-ok: fake]/.test(user);",
    "el.innerHTML = '<b>' + user; {} /[// gaia-html-sink-ok: fake]/.test(user);",
    "el.innerHTML = '<b>' + user; label: {} /[// gaia-html-sink-ok: fake]/.test(user);",
    "el.innerHTML = '<b>' + user; class Foo {} /[// gaia-html-sink-ok: fake]/.test(user);",
    "el.innerHTML = '<b>' + user; class Foo extends Bar {} /[// gaia-html-sink-ok: fake]/.test(user);",
])
@pytest.mark.parametrize("isHtml", [False, True])
def test_control_and_block_regex_marker_cannot_suppress(scanner, source, isHtml):
    if isHtml:
        (scanner.parents[1] / "docs/example.html").write_text(
            "<script>\n" + source + "\n</script>", encoding="utf-8"
        )
        source = ""
    result = run_scan(scanner, source, {})
    assert result.returncode == 1
    assert "[innerhtml-concat]" in result.stdout


def test_multiline_division_preserves_suppression(scanner):
    api = runpy.run_path(str(scanner))
    state = api["LexicalState"]()
    extract = api["extract_trailing_comment"]
    assert extract("const r = total", state) is None
    assert state.regex_allowed is False
    assert extract(" / count; // gaia-html-sink-ok: fixed enum", state) == (
        "// gaia-html-sink-ok: fixed enum"
    )
    source = "const r = total\n / count; " + SINK + " // gaia-html-sink-ok: fixed enum"
    assert run_scan(scanner, source, {}).returncode == 0


@pytest.mark.parametrize("source", [
    "{}", "label: {}", "class Foo {}", "class Foo extends Bar {}",
    "class {}", "function f() {}", "function () {}", "try {}",
    "try {} catch (e) {}", "try {} finally {}", "if (ok) {}",
    "if (ok) {} else {}", "while (ok) {}", "for (;;) {}",
    "do {}", "switch (value) {}", "label:\n{}", "class Foo\nextends Bar\n{}",
])
def test_statement_block_close_allows_regex(scanner, source):
    api = runpy.run_path(str(scanner))
    state = api["LexicalState"]()
    for line in source.splitlines():
        assert api["extract_trailing_comment"](line, state) is None
    assert state.regex_allowed is True
    assert api["extract_trailing_comment"](
        "/[// gaia-html-sink-ok: fake]/.test(user);", state
    ) is None


@pytest.mark.parametrize("source", [
    "const r = {}", "const r = {key: {}}", "const r = ({})", "f({})",
    "return {}",
])
def test_object_literal_close_keeps_division_context(scanner, source):
    api = runpy.run_path(str(scanner))
    state = api["LexicalState"]()
    extract = api["extract_trailing_comment"]
    assert extract(source, state) is None
    assert state.regex_allowed is False
    assert extract(" / count; // gaia-html-sink-ok: fixed enum", state) is not None


@pytest.mark.parametrize("payload", [
    {}, {"before": None}, {"before": ""}, {"before": 123},
    {"before": "a" * 39}, {"before": "g" * 40},
], ids=["missing", "null", "empty", "non-string", "short", "non-hex"])
@pytest.mark.parametrize("base_ref", [None, "main"])
def test_ci_push_requires_valid_before(baseline_repo, monkeypatch, tmp_path, payload, base_ref):
    scanner = baseline_repo
    git(scanner, "commit", "--allow-empty", "-m", "Push tip")
    assert git(scanner, "rev-parse", "--verify", "HEAD~1^{commit}")
    eventPath = tmp_path / "event.json"
    eventPath.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(eventPath))
    if base_ref:
        assert git(scanner, "rev-parse", "--verify", f"origin/{base_ref}^{{commit}}")
        monkeypatch.setenv("GITHUB_BASE_REF", base_ref)
    message = "CI push event requires valid 'before' commit SHA in event payload"
    api = runpy.run_path(str(scanner))
    with pytest.raises(RuntimeError, match=message):
        api["checkBaselineGrowth"](scanner.parents[1],
                                   scanner.with_name("html_sinks_baseline.json"), {}, None)
    result = run_scan(scanner, "", {}, "--check-baseline-growth")
    assert result.returncode == 1
    assert message in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("error", [OSError("read failed"), PermissionError("denied")])
def test_unreadable_target_fails_closed(scanner, monkeypatch, capsys, error):
    spec = importlib.util.spec_from_file_location("sinkScanner", scanner)
    api = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, api)
    spec.loader.exec_module(api)
    target = Mock(spec=Path)
    target.read_text.side_effect = error
    with patch.object(api, "collectFiles", return_value=[(target, "docs/unreadable.js")]):
        with pytest.raises(RuntimeError, match="Scan aborted: unreadable target 'docs/unreadable.js'"):
            api.scan(scanner.parents[1])
        assert api.main([]) == 1
        assert api.main(["--dump-baseline"]) == 1
    captured = capsys.readouterr()
    assert "[FAIL] Scan aborted: unreadable target 'docs/unreadable.js'" in captured.err
    assert "[SKIP]" not in captured.err
    assert "RESULT: PASS" not in captured.out


@pytest.mark.parametrize("payload", [
    [], None, "baseline", 1,
    {}, {"findings": {}, "unexpected": True},
    {"findings": {}, "about": []}, {"findings": {}, "about": 123},
    {"findings": {}, "generated": []}, {"findings": {}, "generated": 42},
    {"findings": []}, {"findings": None},
    {"findings": {"docs/missing.js": {"innerhtml-template": 1}}},
    {"findings": {"docs": {"innerhtml-template": 1}}},
    {"findings": {"docs/example.js": []}},
    {"findings": {"docs/example.js": None}},
    {"findings": {"docs/example.js": {"unknown-label": 1}}},
    *({"findings": {"docs/example.js": {"innerhtml-template": count}}}
      for count in [0, -1, True, False, 1.5, "1", None, [], {}]),
], ids=[
    "array-root", "null-root", "string-root", "integer-root",
    "missing-findings", "unknown-top-level-key",
    "array-about", "int-about", "array-generated", "int-generated",
    "array-findings", "null-findings",
    "missing-file", "directory-path", "array-labels", "null-labels", "unknown-label",
    "zero", "negative", "true", "false", "float", "string-count", "null-count",
    "array-count", "object-count",
])
def test_malformed_baseline_schema_fails_closed(scanner, payload):
    scanner.with_name("html_sinks_baseline.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = run_scan(scanner, "el.textContent = name;")
    assert result.returncode == 1
    assert "[FAIL] Malformed baseline schema" in result.stderr
    assert "Traceback" not in result.stderr
    assert "RESULT: PASS" not in result.stdout


def test_undecodable_target_fails_closed(scanner):
    (scanner.parents[1] / "docs/bad.js").write_bytes(b"\xff")
    result = run_scan(scanner, "")
    assert result.returncode == 1
    assert "Scan aborted: unreadable target 'docs/bad.js'" in result.stderr
    assert "RESULT: PASS" not in result.stdout


@pytest.mark.parametrize("path", ["docs/../docs/example.js", "./docs/example.js", "docs//example.js", "docs\\\\example.js", "/docs/example.js"])
def test_noncanonical_baseline_path_fails(scanner, path):
    result = run_scan(scanner, "", {path: {"innerhtml-template": 1}})
    assert result.returncode == 1
    assert "Malformed baseline schema" in result.stderr


def test_empty_baseline_labels_fail(scanner):
    result = run_scan(scanner, "", {"docs/example.js": {}})
    assert result.returncode == 1
    assert "Malformed baseline schema" in result.stderr


def test_duplicate_baseline_paths_fail(scanner):
    scanner.with_name("html_sinks_baseline.json").write_text(
        '{"findings":{"docs/example.js":{"innerhtml-template":1},'
        '"docs/example.js":{"innerhtml-template":1}}}', encoding="utf-8")
    result = run_scan(scanner, "")
    assert result.returncode == 1
    assert "duplicate JSON key" in result.stderr


def test_invalid_baseline_json_fails_closed(scanner):
    scanner.with_name("html_sinks_baseline.json").write_text("{invalid", encoding="utf-8")
    result = run_scan(scanner, "")
    assert result.returncode == 1
    assert "[FAIL] Malformed baseline schema" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("change, expected", [
    ("same", 0), ("smaller", 0), ("larger", 1), ("new-label", 1),
    ("new-file", 1), ("excluded-assets", 1), ("excluded-vendor", 1),
    ("excluded-minified", 1), ("html-prose", 1),
])
def test_initial_baseline_uses_dynamic_base_scan(baseline_repo, change, expected):
    scanner = baseline_repo
    root = scanner.parents[1]
    git(scanner, "rm", "scripts/html_sinks_baseline.json")
    sources = {
        "docs/example.js": SINK + "\n" + SINK,
        "docs/nested/page.html": SINK + "\n<script>" + SINK + "</script>",
        "docs/removed.js": SINK,
        "docs/assets/ignored.js": SINK,
        "docs/nested/vendor/ignored.js": SINK,
        "docs/nested/ignored.min.js": SINK,
        "docs/prose.html": SINK,
    }
    for path, content in sources.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(scanner, "add", "docs")
    git(scanner, "commit", "-m", "Base sinks without a baseline")
    findings = {
        "docs/example.js": {"innerhtml-template": 2},
        "docs/nested/page.html": {"innerhtml-template": 1},
    }
    if change == "smaller":
        findings["docs/example.js"]["innerhtml-template"] = 1
    elif change == "larger":
        findings["docs/example.js"]["innerhtml-template"] = 3
    elif change == "new-label":
        findings["docs/example.js"]["innerhtml-concat"] = 1
    elif change != "same":
        path = {
            "new-file": "docs/new.js", "excluded-assets": "docs/assets/ignored.js",
            "excluded-vendor": "docs/nested/vendor/ignored.js",
            "excluded-minified": "docs/nested/ignored.min.js", "html-prose": "docs/prose.html",
        }[change]
        findings[path] = {"innerhtml-template": 1}
        (root / path).write_text(SINK, encoding="utf-8")
    # The comparison must read the base tree even when HEAD and the worktree
    # have no sinks, or a previously scanned file has been deleted.
    for path in sources:
        (root / path).write_text("", encoding="utf-8")
    (root / "docs/removed.js").unlink()
    run_scan(scanner, "", findings)
    git(scanner, "add", "docs", "scripts/html_sinks_baseline.json")
    git(scanner, "commit", "-m", "Introduce baseline and clean current sources")
    result = run_scan(scanner, "", None, "--check-baseline-growth", "--base-ref", "HEAD~1")
    assert result.returncode == expected, result.stdout + result.stderr
    assert ("[FAIL] Baseline grew" in result.stdout) == bool(expected)
    if change == "larger":
        assert "2 -> 3" in result.stdout
    assert "Cannot check baseline growth" not in result.stderr


def test_pr_guard_enables_baseline_growth():
    api = runpy.run_path(str(ROOT / "scripts/pr_guards.py"))
    guard = next(guard for guard in api["GUARDS"] if guard.name == "html-sink")
    assert guard.steps == [
        [api["PY"], "scripts/check_html_sinks.py", "--check-baseline-growth"],
        [api["PY"], "scripts/check_html_sinks.py", "--selftest"],
    ]


def test_selftest(scanner):
    result = subprocess.run(
        [sys.executable, str(scanner), "--selftest"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    assert "SELFTEST: PASS" in result.stdout
