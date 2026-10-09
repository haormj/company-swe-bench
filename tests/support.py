"""Test doubles shared across the test suite."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from mining.client import GitLabClient, GitLabError
from mining.models import MRRecord


class FakeGitLabClient(GitLabClient):
    """In-memory GitLab client for tests.

    Storage is keyed by project id. ``fail_counts`` injects transient
    failures: an entry ``(op, key) -> n`` makes the next *n* calls to that
    operation raise ``GitLabError`` before succeeding.
    """

    def __init__(self) -> None:
        self.projects: Dict[str, int] = {}
        self.pages: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self.changed_files: Dict[Tuple[int, int], List[str]] = {}
        self.diffs: Dict[Tuple[int, int], str] = {}
        self.commits: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self.related_issues: Dict[Tuple[int, int], List[int]] = {}
        self.merge_bases: Dict[Tuple[int, Tuple[str, ...]], str] = {}
        self.fail_counts: Dict[Tuple[str, Any], int] = {}
        self.calls: List[Tuple[str, Any]] = []

    def _record(self, op: str, key: Any) -> None:
        self.calls.append((op, key))
        remaining = self.fail_counts.get((op, key), 0)
        if remaining > 0:
            self.fail_counts[(op, key)] = remaining - 1
            raise GitLabError(f"injected transient failure: {op} {key}")

    def get_project_id(self, group: str, repo: str) -> int:
        full = f"{group}/{repo}"
        self._record("get_project_id", full)
        return self.projects[full]

    def fetch_merged_mr_page(
        self,
        project_id: int,
        since_iso: str,
        until_iso: str,
        page: int,
        per_page: int,
    ) -> List[Dict[str, Any]]:
        self._record("fetch_page", (project_id, page))
        return list(self.pages.get((project_id, page), []))

    def get_mr_changed_files(self, project_id: int, mr_iid: int) -> List[str]:
        self._record("changed_files", (project_id, mr_iid))
        return list(self.changed_files.get((project_id, mr_iid), []))

    def get_mr_diff(self, project_id: int, mr_iid: int) -> str:
        self._record("diff", (project_id, mr_iid))
        return self.diffs.get((project_id, mr_iid), "")

    def get_mr_commits(
        self, project_id: int, mr_iid: int
    ) -> List[Dict[str, Any]]:
        self._record("commits", (project_id, mr_iid))
        return list(self.commits.get((project_id, mr_iid), []))

    def get_related_issue_iids(self, project_id: int, mr_iid: int) -> List[int]:
        self._record("related_issues", (project_id, mr_iid))
        return list(self.related_issues.get((project_id, mr_iid), []))

    def get_merge_base(self, project_id: int, refs: Sequence[str]) -> str:
        self._record("merge_base", (project_id, tuple(refs)))
        return self.merge_bases.get((project_id, tuple(refs)), "base0")

    # -- convenience builders -------------------------------------------------

    def add_repo(
        self, group: str, repo: str, project_id: int
    ) -> "FakeGitLabClient":
        self.projects[f"{group}/{repo}"] = project_id
        return self

    def add_mr(
        self,
        project_id: int,
        iid: int,
        changed_files: Sequence[str],
        diff: str = "",
        page: int = 1,
        **raw: Any,
    ) -> "FakeGitLabClient":
        record = {
            "iid": iid,
            "title": raw.get("title", f"MR {iid}"),
            "description": raw.get("description", ""),
            "author": {"username": raw.get("author", "alice")},
            "merged_at": raw.get("merged_at", "2026-09-01T10:00:00.000Z"),
            "labels": raw.get("labels", []),
            "source_branch": raw.get("source_branch", f"feat/{iid}"),
            "target_branch": raw.get("target_branch", "main"),
            "web_url": raw.get("web_url", f"https://gitlab.internal/p/-/mr/{iid}"),
            "sha": raw.get("sha", f"sha{iid}"),
        }
        self.pages.setdefault((project_id, page), []).append(record)
        self.changed_files[(project_id, iid)] = list(changed_files)
        self.diffs[(project_id, iid)] = diff
        self.commits.setdefault((project_id, iid), []).append(
            {"id": record["sha"], "title": record["title"]}
        )
        self.related_issues[(project_id, iid)] = list(raw.get("related_issues", []))
        return self


def _default_diff(paths: Sequence[str], added: int = 10, removed: int = 0) -> str:
    lines: List[str] = []
    for path in paths:
        lines.append(f"diff --git a/{path} b/{path}")
        lines.append(f"--- a/{path}")
        lines.append(f"+++ b/{path}")
        lines.append("@@ -1,1 +1,1 @@")
        for i in range(removed):
            lines.append(f"-old{i}")
        for i in range(added):
            lines.append(f"+new{i}")
    return "\n".join(lines) + "\n"


def make_mr(
    iid: int = 1,
    project_id: int = 101,
    changed_files: Sequence[str] = ("src/app.py", "tests/test_app.py"),
    diff: Optional[str] = None,
    title: str = "Add feature",
    labels: Sequence[str] = (),
    related_issues: Sequence[int] = (),
    merged_at: str = "2026-09-01T10:00:00.000Z",
    base_commit: str = "base0",
    commits: Optional[List[Dict[str, Any]]] = None,
    test_files_changed: Optional[Sequence[str]] = None,
    description: str = "description",
) -> MRRecord:
    from paths import classify_changed_files

    paths = list(changed_files)
    if test_files_changed is None:
        test_files_changed, _ = classify_changed_files(
            paths, ["test", "tests", "e2e", "testing"]
        )
    if diff is None:
        diff = _default_diff(paths, added=10)
    if commits is None:
        commits = [{"id": "sha", "title": title}]
    return MRRecord(
        project_id=project_id,
        mr_iid=iid,
        title=title,
        description=description,
        author="alice",
        merged_at=merged_at,
        labels=list(labels),
        changed_files=paths,
        diff=diff,
        commits=commits,
        related_issues=list(related_issues),
        base_commit=base_commit,
        test_files_changed=list(test_files_changed),
    )
