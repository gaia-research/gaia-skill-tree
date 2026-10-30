"""Browser-rendered frontend sensor: what a real browser saw, not what the HTML says.

``FrontendContractSensor`` reads page source, so it cannot see a stylesheet
``url()`` that 404s, an icon sprite requested from the wrong directory, an
uncaught script error, or a page that overflows a phone viewport. Only a browser
can. This sensor never launches one and never touches the network: a driver
(``scripts/steward_collect_browser_render.js``) renders the tracked pages in
headless Chromium and hands the observations over as
``.gaia/steward/inputs/browser-render.json`` (``steward-browser-render-v1``).

Like the other driver-input sensors, an absent, stale or foreign input raises
``SensorNotEvaluated``: a browser that was not run is unknown, never healthy. A
page the browser could not render, or that the driver never reached, is a skipped
subject (partial coverage), not a clean one.

Only same-origin requests are findings. A request to another host failing in the
collector's sandbox says nothing about the site, so the driver records only that
external requests were not judged.

Findings carry structure (rule, same-origin path, status, viewport, widths) and
never an arbitrary string from the page: paths are validated against a strict
shape, and page error text is reduced to a count.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from gaia_cli.steward.models import Observation, SensorScan, Subject
from gaia_cli.steward.primitives import (
    SensorNotEvaluated,
    SensorUnavailable,
    SkipLog,
    finding_payload,
    git_root,
    read_text_bounded,
    tracked_files,
)
from gaia_cli.steward.primitives.inputs import origin_repository, require_fresh
from gaia_cli.steward.primitives.redact import describe_value
from gaia_cli.steward.sensors_ci import _load_optional_json, _require_str
from gaia_cli.steward.sensors_contracts import _FRONTEND_EXCLUDES

_RENDER_INPUT = Path(".gaia/steward/inputs/browser-render.json")
_RENDER_SCHEMA = "steward-browser-render-v1"
_MAX_RENDERS = 4000
_MAX_FAILURES_PER_RENDER = 50
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_PAGE = re.compile(r"docs/[A-Za-z0-9._/-]{1,200}\.html")
_ORIGIN_PATH = re.compile(r"/[A-Za-z0-9._~%/+=@:,()'!$*;-]{0,300}")
_BROWSER_TEXT = re.compile(r"[A-Za-z0-9 ._-]{1,40}")
# What the collector reports for a request path the sensor could not safely carry.
_UNREPRESENTABLE = "/unrepresentable-path"
_HTML_ELEMENT = re.compile(r"<html[\s>]", re.IGNORECASE)
_NAVIGATION = frozenset({"ok", "timeout", "error"})
_UNRENDERED_REASONS = frozenset({"not requested", "unsupported file name"})
# One pixel of slack: fractional layout widths round differently across engines.
_OVERFLOW_TOLERANCE = 1


def _integer(value: Any, where: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SensorUnavailable(f"{where} requires an integer of at least {minimum}")
    return value


class BrowserRenderSensor:
    """Same-origin load failures, uncaught page errors and viewport overflow from a real browser.

    Exhaustive whenever the input is present, valid, fresh and about this
    checkout's repository: a healthy re-collection resolves what an earlier one
    found. Its debt is keyed ``rendered:<page>`` so it never collides with the
    static ``frontend-contract`` debt for the same file.
    """

    id = "browser-render"
    debt_kinds = ("frontend_contract_drift",)
    routine_ids = (15,)
    resolution_scope = "exhaustive"
    driver_inputs = (_RENDER_INPUT.as_posix(),)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        root = git_root(repo_root)
        document = _load_optional_json(root, _RENDER_INPUT)
        if not isinstance(document, dict) or document.get("schemaVersion") != _RENDER_SCHEMA:
            raise SensorUnavailable(f"browser-render does not declare schema {_RENDER_SCHEMA}")
        repository = _require_str(document, "repository", "browser-render")
        if not _REPOSITORY.fullmatch(repository):
            raise SensorUnavailable(
                f"browser-render repository is not owner/name {describe_value(repository)}"
            )
        browser = document.get("browser")
        if not isinstance(browser, dict):
            raise SensorUnavailable("browser-render requires a browser object (name, version)")
        browser_name = _require_str(browser, "name", "browser-render browser")
        browser_version = _require_str(browser, "version", "browser-render browser")
        if not _BROWSER_TEXT.fullmatch(browser_name) or not _BROWSER_TEXT.fullmatch(browser_version):
            raise SensorUnavailable("browser-render browser name or version is not plain bounded text")
        viewports = self._viewports(document.get("viewports"))
        renders = self._renders(document.get("renders"), viewports)
        freshness = require_fresh(document, root / _RENDER_INPUT, observed_at, label="browser-render")

        origin = origin_repository(root)
        if origin is not None and origin.casefold() != repository.casefold():
            raise SensorNotEvaluated("browser-render is about another repository than this checkout's origin")

        skips = SkipLog()
        for entry in self._unrendered(document.get("unrendered")):
            skips.add("html-page", entry["path"], f"page was not rendered by the driver: {entry['reason']}")

        # Exhaustive means the browser saw every page the checkout tracks. A page
        # that is tracked and rendered by neither the renders nor the unrendered
        # list is unknown, so it is skipped rather than silently treated as clean
        # (otherwise a driver bug or a hand-built input could clear real debt).
        accounted = {render["path"] for render in renders} | {entry["path"] for entry in self._unrendered(document.get("unrendered"))}
        for page in self._inventory(root):
            if page not in accounted:
                skips.add("html-page", page, "tracked page absent from the browser-render input")

        by_page: dict[str, list[dict[str, Any]]] = {}
        for render in renders:
            if render["navigation"] != "ok":
                skips.add(
                    "html-page",
                    render["path"],
                    f"browser navigation ended {render['navigation']} at {render['viewport']}",
                )
                continue
            by_page.setdefault(render["path"], []).append(render)
        # A page needs both viewports judged to be called clean or drifting; a
        # page rendered at only some of them is incomplete, so it is skipped
        # rather than reported on half the evidence.
        wanted = {name for name in viewports}
        observations: list[Observation] = []
        for page in sorted(by_page):
            seen = {render["viewport"] for render in by_page[page]}
            if seen != wanted:
                skips.add("html-page", page, "not rendered successfully at every viewport")
                continue
            findings = self._findings(by_page[page])
            if not findings:
                continue
            observed_state = finding_payload(findings)
            observed_state["viewports"] = sorted(wanted)
            observations.append(
                Observation(
                    kind="frontend_contract_drift",
                    subject=Subject(type="html-page", id=f"rendered:{page}"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"findingCount": 0},
                    observed_state=observed_state,
                    confidence=1.0,
                    provenance={
                        "input": _RENDER_INPUT.as_posix(),
                        "schemaVersion": _RENDER_SCHEMA,
                        "repository": repository,
                        "browser": f"{browser_name} {browser_version}",
                        "externalRequests": "not judged",
                        "renderedAgainst": "local static server of tracked docs/, not the deployed site",
                        **freshness,
                    },
                )
            )
        return SensorScan(tuple(observations), skips.entries())

    @staticmethod
    def _inventory(root: Path) -> list[str]:
        """Tracked hand-authored document pages, as the collector discovers them."""

        pages: list[str] = []
        for relative in tracked_files(root, ["docs/"], suffixes=(".html",), exclude=_FRONTEND_EXCLUDES):
            if not _PAGE.fullmatch(relative) or ".." in relative:
                continue
            try:
                text = read_text_bounded(root / relative)
            except (OSError, ValueError, SensorUnavailable):
                pages.append(relative)  # unreadable: surface it as unaccounted, not as absent
                continue
            if _HTML_ELEMENT.search(text):
                pages.append(relative)
        return pages

    @staticmethod
    def _viewports(raw: Any) -> dict[str, int]:
        if not isinstance(raw, list) or not raw:
            raise SensorUnavailable("browser-render requires a non-empty viewports list")
        viewports: dict[str, int] = {}
        for index, item in enumerate(raw):
            where = f"browser-render viewport {index}"
            if not isinstance(item, dict):
                raise SensorUnavailable(f"{where} is not an object")
            name = _require_str(item, "name", where)
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", name) or name in viewports:
                raise SensorUnavailable(f"{where} has an invalid or duplicate name {describe_value(name)}")
            viewports[name] = _integer(item.get("width"), f"{where} width", minimum=1)
        return viewports

    @staticmethod
    def _unrendered(raw: Any) -> list[dict[str, str]]:
        if raw is None:
            return []
        if not isinstance(raw, list) or len(raw) > _MAX_RENDERS:
            raise SensorUnavailable("browser-render unrendered must be a bounded list")
        entries: list[dict[str, str]] = []
        for index, item in enumerate(raw):
            where = f"browser-render unrendered {index}"
            if not isinstance(item, dict):
                raise SensorUnavailable(f"{where} is not an object")
            path = _require_str(item, "path", where)
            reason = _require_str(item, "reason", where)
            if not _PAGE.fullmatch(path) or ".." in path:
                raise SensorUnavailable(f"{where} path is not a docs html page {describe_value(path)}")
            # The driver's wording is never echoed: only a known reason survives.
            entries.append({"path": path, "reason": reason if reason in _UNRENDERED_REASONS else "unspecified"})
        return entries

    @staticmethod
    def _renders(raw: Any, viewports: dict[str, int]) -> list[dict[str, Any]]:
        if not isinstance(raw, list) or not raw:
            raise SensorUnavailable("browser-render requires a non-empty renders list")
        if len(raw) > _MAX_RENDERS:
            raise SensorUnavailable(f"browser-render exceeds the bounded limit of {_MAX_RENDERS} renders")
        renders: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for index, item in enumerate(raw):
            where = f"browser-render render {index}"
            if not isinstance(item, dict):
                raise SensorUnavailable(f"{where} is not an object")
            path = _require_str(item, "path", where)
            viewport = _require_str(item, "viewport", where)
            navigation = _require_str(item, "navigation", where)
            if not _PAGE.fullmatch(path) or ".." in path:
                raise SensorUnavailable(f"{where} path is not a docs html page {describe_value(path)}")
            if viewport not in viewports:
                raise SensorUnavailable(f"{where} names an undeclared viewport {describe_value(viewport)}")
            if navigation not in _NAVIGATION:
                raise SensorUnavailable(f"{where} navigation is not one of {sorted(_NAVIGATION)}")
            if (path, viewport) in seen:
                raise SensorUnavailable(f"{where} repeats a page and viewport")
            seen.add((path, viewport))
            failures = item.get("sameOriginFailures", [])
            if not isinstance(failures, list) or len(failures) > _MAX_FAILURES_PER_RENDER:
                raise SensorUnavailable(f"{where} sameOriginFailures must be a bounded list")
            checked: list[dict[str, Any]] = []
            for number, failure in enumerate(failures):
                label = f"{where} failure {number}"
                if not isinstance(failure, dict):
                    raise SensorUnavailable(f"{label} is not an object")
                resource = _require_str(failure, "path", label)
                if resource != _UNREPRESENTABLE and not _ORIGIN_PATH.fullmatch(resource):
                    raise SensorUnavailable(f"{label} path is not a same-origin path {describe_value(resource)}")
                status = failure.get("status")
                if status is None:
                    outcome: Any = "network-error"
                else:
                    outcome = _integer(status, f"{label} status", minimum=100)
                checked.append({"path": resource, "outcome": outcome})
            overflow = item.get("horizontalOverflow")
            if overflow is not None:
                if not isinstance(overflow, dict):
                    raise SensorUnavailable(f"{where} horizontalOverflow must be an object")
                overflow = {
                    "scrollWidth": _integer(overflow.get("scrollWidth"), f"{where} scrollWidth"),
                    "clientWidth": _integer(overflow.get("clientWidth"), f"{where} clientWidth"),
                }
            renders.append({
                "path": path,
                "viewport": viewport,
                "navigation": navigation,
                "failures": checked,
                "pageErrors": _integer(item.get("pageErrors", 0), f"{where} pageErrors"),
                "overflow": overflow,
            })
        return renders

    @staticmethod
    def _findings(renders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        failed: dict[tuple[str, Any], set[str]] = {}
        for render in renders:
            for failure in render["failures"]:
                failed.setdefault((failure["path"], failure["outcome"]), set()).add(render["viewport"])
            if render["pageErrors"]:
                findings.append({
                    "rule": "rendered-page-error",
                    "viewport": render["viewport"],
                    "count": render["pageErrors"],
                })
            overflow = render["overflow"]
            if overflow and overflow["scrollWidth"] > overflow["clientWidth"] + _OVERFLOW_TOLERANCE:
                findings.append({
                    "rule": "rendered-horizontal-overflow",
                    "viewport": render["viewport"],
                    "scrollWidth": overflow["scrollWidth"],
                    "clientWidth": overflow["clientWidth"],
                })
        for (resource, outcome), names in failed.items():
            findings.append({
                "rule": "rendered-same-origin-failure",
                "resource": resource,
                "outcome": outcome,
                "viewports": sorted(names),
            })
        findings.sort(key=lambda item: (item["rule"], str(item.get("resource", "")), str(item.get("viewport", ""))))
        return findings
