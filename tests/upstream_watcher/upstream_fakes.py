"""In-memory GitHub fake for the upstream batch planner (#2131)."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import urllib.parse
from pathlib import Path

from scripts.upstream_watcher import prechecks as pc
from scripts.upstream_watcher.live import GhError, GhNotFound


class FakeGh:
    """Implements the LiveGh surface over a dict of REST-shaped issues."""

    def __init__(self, issues: list[dict] | None = None):
        self.issues: dict[int, dict] = {}
        self.clock = 1000
        self.writes: list[tuple] = []
        self.list_calls: list[tuple] = []
        self.fail_list = False
        self.fail_get = False
        # Issues GitHub still serves by number but the LIST snapshot omits (for example a
        # child closed longer ago than the recently-closed window).
        self.hidden_from_list: set[int] = set()
        # Numbers GitHub answers with HTTP 301: the issue was transferred, so the old number
        # no longer names a live issue (absent to the planner, never listed).
        self.moved: set[int] = set()
        self.stale_on_get: dict[int, dict] = {}
        self.next_number = 5000
        # Issue comments by issue number (M5 record comments). Each comment is {id, body, user}.
        self.comments: dict[int, list[dict]] = {}
        self.next_comment_id = 9000
        for issue in issues or []:
            self.add(issue)

    # -- seeding -----------------------------------------------------------
    def add(self, issue: dict) -> dict:
        row = copy.deepcopy(issue)
        row.setdefault("state", "open")
        row.setdefault("updated_at", self.stamp())
        row.setdefault("body", "")
        row["labels"] = [{"name": label} if isinstance(label, str) else label for label in row.get("labels", [])]
        self.issues[row["number"]] = row
        self.next_number = max(self.next_number, row["number"] + 1)
        return row

    def stamp(self) -> str:
        self.clock += 1
        return f"2026-10-21T19:{self.clock % 60:02d}:{self.clock // 60 % 60:02d}Z"

    # -- LiveGh surface ----------------------------------------------------
    def list_issues(self, state: str, since: str | None = None, labels: str | None = None) -> list[dict]:
        self.list_calls.append((state, since))
        if self.fail_list:
            raise GhError("list failed (fake)")
        wanted = set(filter(None, (labels or "").split(",")))
        rows = [
            copy.deepcopy(row)
            for row in self.issues.values()
            if (state == "all" or row["state"] == state)
            and row["number"] not in self.hidden_from_list
            and row["number"] not in self.moved
            and (not since or row["updated_at"] >= since)
            and wanted <= {label["name"] for label in row["labels"]}
        ]
        return sorted(rows, key=lambda row: row["number"])

    def issue_state(self, number: int) -> str:
        """Mirror LiveGh.issue_state: absent for a number GitHub does not hold, GhError on a fake failure."""
        if self.fail_get:
            raise GhError("get failed (fake)")
        row = self.issues.get(number)
        if row is None or number in self.moved:
            return "absent"
        return "closed" if row["state"] == "closed" else "open"

    def child_state(self, number: int) -> str:
        """Mirror LiveGh.child_state: open, closed-rejected, closed, or absent."""
        if self.fail_get:
            raise GhError("get failed (fake)")
        row = self.issues.get(number)
        if row is None or number in self.moved:
            return "absent"
        if row["state"] != "closed":
            return "open"
        labels = {label["name"] for label in row["labels"]}
        return "closed-rejected" if "upstream:rejected" in labels else "closed"

    def get_issue(self, number: int) -> dict:
        if self.fail_get:
            raise GhError("get failed (fake)")
        if number in self.moved:
            raise GhNotFound(f"gh issue #{number} exited 1: HTTP 301 (fake moved)", "301")
        if number in self.stale_on_get:
            # Simulates a racing writer: the live issue changed after our list snapshot.
            self.issues[number].update(self.stale_on_get.pop(number))
        if number not in self.issues:
            raise GhError(f"issue #{number} missing (fake)")
        return copy.deepcopy(self.issues[number])

    def create_issue(self, title: str, labels: list[str], body: str) -> int:
        number = self.next_number
        self.next_number += 1
        self.issues[number] = {
            "number": number, "title": title, "state": "open", "body": body,
            "labels": [{"name": label} for label in labels], "updated_at": self.stamp(),
        }
        self.writes.append(("create", number, title))
        return number

    def edit_issue(self, number: int, title: str, body: str) -> None:
        self.issues[number].update({"title": title, "body": body, "updated_at": self.stamp()})
        self.writes.append(("edit", number))

    def edit_labels(self, number, add=(), remove=()) -> None:
        names = [label["name"] for label in self.issues[number]["labels"]]
        names = [name for name in names if name not in remove] + [name for name in add if name not in names]
        self.issues[number]["labels"] = [{"name": name} for name in names]
        self.writes.append(("labels", number, tuple(add), tuple(remove)))

    def comment(self, number: int, body: str) -> None:
        self.next_comment_id += 1
        self.comments.setdefault(number, []).append(
            {"id": self.next_comment_id, "body": body, "user": {"login": "github-actions[bot]", "type": "Bot"}}
        )
        self.writes.append(("comment", number, body))

    def list_comments(self, number: int) -> list[dict]:
        return [dict(row) for row in self.comments.get(number, [])]

    def edit_comment(self, comment_id: int, body: str) -> None:
        for rows in self.comments.values():
            for row in rows:
                if row["id"] == comment_id:
                    row["body"] = body
                    self.writes.append(("edit_comment", comment_id))
                    return
        raise GhError(f"comment {comment_id} missing (fake)")

    def delete_comment(self, comment_id: int) -> None:
        for rows in self.comments.values():
            for row in rows:
                if row["id"] == comment_id:
                    rows.remove(row)
                    self.writes.append(("delete_comment", comment_id))
                    return
        raise GhError(f"comment {comment_id} missing (fake)")

    # -- helpers -----------------------------------------------------------
    def write_count(self) -> int:
        return len(self.writes)

    def by_title(self, prefix: str) -> list[dict]:
        return [row for row in self.issues.values() if row["title"].startswith(prefix)]


def index_from_entries(entries: list[dict]) -> dict:
    """Build a registry index from ``{"id", "github"}`` records, as load_registry_index does."""
    by_id, by_slug = {}, {}
    for entry in entries:
        by_id[entry["id"]] = {"links": pc.normalize_blob(entry.get("github", ""), ignore_ref=True), "status": "named"}
        by_slug.setdefault(pc.slug_key(entry["id"].split("/")[-1]), []).append(entry["id"])
    return {"byId": by_id, "bySlug": by_slug}


class FakeRunner:
    """Stands in for subprocess.run for LiveGh pagination tests."""

    def __init__(self, pages_by_state: dict[str, list[list[dict]]]):
        self.pages = pages_by_state
        self.calls: list[list[str]] = []

    def __call__(self, args, capture_output=True, text=True, timeout=None):
        self.calls.append(list(args))
        state = next(a.split("=", 1)[1] for a in args if a.startswith("state="))
        page = int(next(a.split("=", 1)[1] for a in args if a.startswith("page=")))
        pages = self.pages.get(state, [])
        body = pages[page - 1] if page - 1 < len(pages) else []
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(body), stderr="")


def fixture_issue_rows(families: dict) -> list[dict]:
    rows = []
    for umbrella in families["umbrellas"]:
        rows.append({k: umbrella[k] for k in ("number", "title", "state", "labels", "body", "updated_at")})
    for child in families["children"]:
        rows.append({k: child[k] for k in ("number", "title", "state", "labels", "body", "updated_at")})
    return rows


def fixture_registry_entries(families: dict) -> list[dict]:
    return [{"id": entry["id"], "github": entry["github"]} for entry in families["registry"]]


SUGGESTED_RE = re.compile(r"Suggested ID:\*\*\s*`([^`]+)`")


REPO_ID = 1221716703


class RestGhRunner:
    """A ``subprocess.run`` stand-in for LiveGh that serves REST LIST pages as GitHub does.

    LIST calls are answered page by page from ``issues`` (state, label, ``since`` and
    ``per_page`` honoured), so the real pagination loop in LiveGh is what gets tested.
    ``fail_pages`` holds ``(state, labels, page)`` triples that answer with a gh failure.
    Writes (``issue create/edit/comment``) are recorded in ``writes`` with their body text.
    """

    repo = "gaia-research/gaia-skill-tree"

    def __init__(self, issues: list[dict], fail_pages=(), empty_pages=(), empty_once=(), no_link_pages=(),
                 short_pages=(), count_fails=False, open_count=None):
        self.issues = [copy.deepcopy(row) for row in issues]
        self.fail_pages = set(fail_pages)
        # (state, labels, page) triples that answer 200 with an empty array, as a short or dropped page does.
        self.empty_pages = set(empty_pages)
        # Like empty_pages, but only for the first request; a retry then gets the real page.
        self.empty_once = set(empty_once)
        # Pages served without a Link header, as a proxy that drops it does.
        self.no_link_pages = set(no_link_pages)
        # Pages served with only their first half, as a proxy that truncates does.
        self.short_pages = set(short_pages)
        self.count_fails = count_fails
        self.open_count = open_count
        self.calls: list[list[str]] = []
        self.writes: list[tuple] = []
        self.next_number = 5000
        # Comments by issue number, as the REST comments list serves them (each {id, body, user}).
        self.comments: dict[int, list[dict]] = {}
        # The text of every `gh issue comment`, whether it came by --body or --body-file.
        self.comment_texts: list[str] = []

    def __call__(self, args, capture_output=True, text=True, timeout=None):
        self.calls.append(list(args))
        if args[1] == "api" and "--include" in args:
            return self._include(args)
        if args[1] == "api" and args[-1] == f"repos/{self.repo}":
            return self._repository(args)
        if args[1] == "api" and "-f" not in args and re.search(r"/issues/\d+$", args[-1]):
            return self._single(args)
        comments_path = next((a for a in args if re.search(r"/issues/\d+/comments$", a)), None)
        if args[1] == "api" and comments_path:
            number = int(re.search(r"/issues/(\d+)/comments$", comments_path).group(1))
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(self.comments.get(number, [])), stderr="")
        if args[1] == "api":
            return self._list(args)
        if args[1:3] == ["issue", "create"]:
            body = Path(args[args.index("--body-file") + 1]).read_text(encoding="utf-8")
            self.next_number += 1
            self.writes.append(("create", args[args.index("--title") + 1], body))
            url = f"https://github.com/gaia-research/gaia-skill-tree/issues/{self.next_number}\n"
            return subprocess.CompletedProcess(args, 0, stdout=url, stderr="")
        if args[1:3] in (["issue", "edit"], ["issue", "comment"]):
            self.writes.append((args[2], int(args[3])))
            if args[1:3] == ["issue", "comment"]:
                if "--body-file" in args:
                    self.comment_texts.append(Path(args[args.index("--body-file") + 1]).read_text(encoding="utf-8"))
                elif "--body" in args:
                    self.comment_texts.append(args[args.index("--body") + 1])
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="unsupported (fake)")

    def _single(self, args) -> subprocess.CompletedProcess:
        """GET repos/{repo}/issues/{n}: the live issue as REST serves it (labels, body, state)."""
        number = int(re.search(r"/issues/(\d+)$", args[-1]).group(1))
        for row in self.issues:
            if row["number"] == number:
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(row), stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 404 (fake)")

    def _include(self, args) -> subprocess.CompletedProcess:
        """GET of a listing with its headers (``gh api --include``), served the way GitHub serves it.

        Every full page carries a ``next`` link, even when the page after it is empty, and the link names the
        repository by numeric id. A page is served short only when a test asks for it.
        """
        path, _, query = args[-1].partition("?")
        fields = {key: values[0] for key, values in urllib.parse.parse_qs(query).items()}
        state = fields["state"]
        labels = fields.get("labels", "")
        page, per_page = int(fields.get("page", 1)), int(fields.get("per_page", 100))
        key = (state, labels, page)
        if key in self.fail_pages:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="gh: Bad Gateway (HTTP 502)")
        wanted = set(filter(None, labels.split(",")))
        since = fields.get("since")
        rows = sorted(
            (
                row for row in self.issues
                if (state == "all" or row["state"] == state)
                and wanted <= {label["name"] for label in row["labels"]}
                and (not since or row["updated_at"] >= since)
            ),
            key=lambda row: row["number"],
        )
        chunk = rows[(page - 1) * per_page: page * per_page]
        if key in self.empty_pages or key in self.empty_once:
            self.empty_once.discard(key)
            chunk = []
        if key in self.short_pages:
            chunk = chunk[: len(chunk) // 2]
        headers = ["HTTP/2.0 200 OK", "Content-Type: application/json"]
        if len(chunk) == per_page and key not in self.no_link_pages:
            next_query = {"state": state, "per_page": per_page, "page": page + 1}
            if labels:
                next_query["labels"] = labels
            if since:
                next_query["since"] = since
            link = f"https://api.github.com/repositories/{REPO_ID}/issues?{urllib.parse.urlencode(next_query)}"
            headers.append(f'Link: <{link}>; rel="next"')
        stdout = "\n".join(headers) + "\n\n" + json.dumps(chunk)
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    def _repository(self, args) -> subprocess.CompletedProcess:
        """GET repos/{repo}: the repository's own metadata. open_issues_count counts issues and pull requests."""
        if self.count_fails:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 503 (fake)")
        count = self.open_count if self.open_count is not None else sum(
            1 for row in self.issues if row["state"] == "open")
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps({"open_issues_count": count}), stderr="")
