"""GitLab access layer.

``GitLabClient`` is the minimal interface the miner depends on. The real
implementation talks to an internal GitLab via ``python-gitlab``; tests inject
a fake (see ``tests/support.py``) so no network access is required.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence


class GitLabError(RuntimeError):
    """Transient or permanent failure talking to GitLab."""


def reconstruct_diff(changes: List[Dict[str, Any]]) -> str:
    """Rebuild a unified diff from GitLab's per-file ``changes`` entries.

    Each entry carries ``old_path``/``new_path`` and a ``diff`` body of hunks
    (without ``diff --git``/``---``/``+++`` headers), so we re-add the headers
    needed by ``git apply`` and by :func:`packaging.patch_split.split_diff_by_file`.
    """
    parts: List[str] = []
    for change in changes:
        old = change.get("old_path") or change.get("new_path") or ""
        new = change.get("new_path") or change.get("old_path") or ""
        parts.append(f"diff --git a/{old} b/{new}\n")
        if change.get("new_file"):
            parts.append("new file mode 100644\n")
            parts.append("--- /dev/null\n")
            parts.append(f"+++ b/{new}\n")
        elif change.get("deleted_file"):
            parts.append("deleted file mode 100644\n")
            parts.append(f"--- a/{old}\n")
            parts.append("+++ /dev/null\n")
        elif change.get("renamed_file"):
            parts.append(f"rename from {old}\n")
            parts.append(f"rename to {new}\n")
            parts.append(f"--- a/{old}\n")
            parts.append(f"+++ b/{new}\n")
        else:
            parts.append(f"--- a/{old}\n")
            parts.append(f"+++ b/{new}\n")
        body = change.get("diff", "") or ""
        parts.append(body if body.endswith("\n") else body + "\n")
    return "".join(parts)


class GitLabClient:
    """Interface implemented by the real and fake clients."""

    def get_project_id(self, group: str, repo: str) -> int:  # pragma: no cover
        raise NotImplementedError

    def fetch_merged_mr_page(
        self,
        project_id: int,
        since_iso: str,
        until_iso: str,
        page: int,
        per_page: int,
    ) -> List[Dict[str, Any]]:  # pragma: no cover
        """Return one page of merged MRs (raw GitLab-shaped dicts)."""
        raise NotImplementedError

    def get_mr_changed_files(
        self, project_id: int, mr_iid: int
    ) -> List[str]:  # pragma: no cover
        raise NotImplementedError

    def get_mr_diff(self, project_id: int, mr_iid: int) -> str:  # pragma: no cover
        raise NotImplementedError

    def get_mr_commits(
        self, project_id: int, mr_iid: int
    ) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError

    def get_related_issue_iids(
        self, project_id: int, mr_iid: int
    ) -> List[int]:  # pragma: no cover
        raise NotImplementedError

    def get_merge_base(
        self, project_id: int, refs: Sequence[str]
    ) -> str:  # pragma: no cover
        raise NotImplementedError


class PythonGitLabClient(GitLabClient):
    """Real client backed by ``python-gitlab``.

    Credentials are read from the environment by the caller and passed in;
    nothing here talks to GitLab until a method is called.
    """

    def __init__(self, url: str, token: str, per_page: int = 100) -> None:
        import gitlab  # imported lazily so tests need not install it

        self._gl = gitlab.Gitlab(url, private_token=token)
        self._per_page = per_page
        self._project_cache: Dict[str, int] = {}

    def get_project_id(self, group: str, repo: str) -> int:
        full_name = f"{group}/{repo}"
        if full_name not in self._project_cache:
            project = self._gl.projects.get(full_name)
            self._project_cache[full_name] = project.id
        return self._project_cache[full_name]

    def _project(self, project_id: int):
        return self._gl.projects.get(project_id)

    def fetch_merged_mr_page(
        self,
        project_id: int,
        since_iso: str,
        until_iso: str,
        page: int,
        per_page: int,
    ) -> List[Dict[str, Any]]:
        try:
            mrs = self._project(project_id).mergerequests.list(
                state="merged",
                updated_after=since_iso,
                updated_before=until_iso,
                order_by="updated_at",
                sort="desc",
                page=page,
                per_page=per_page,
                iterator=False,
            )
        except Exception as exc:  # noqa: BLE001 - normalized for retry
            raise GitLabError(str(exc)) from exc
        return [mr._attrs for mr in mrs]

    def get_mr_changed_files(self, project_id: int, mr_iid: int) -> List[str]:
        mr = self._project(project_id).mergerequests.get(mr_iid)
        changes = mr.changes()
        return [c["new_path"] for c in changes.get("changes", [])]

    def get_mr_diff(self, project_id: int, mr_iid: int) -> str:
        mr = self._project(project_id).mergerequests.get(mr_iid)
        changes = mr.changes().get("changes", [])
        return reconstruct_diff(changes)

    def get_mr_commits(
        self, project_id: int, mr_iid: int
    ) -> List[Dict[str, Any]]:
        mr = self._project(project_id).mergerequests.get(mr_iid)
        return [{"id": c.id, "title": c.title} for c in mr.commits()]

    def get_related_issue_iids(self, project_id: int, mr_iid: int) -> List[int]:
        mr = self._project(project_id).mergerequests.get(mr_iid)
        iids: List[int] = []
        try:
            related = mr.related_issues(get_all=True)
        except Exception:  # noqa: BLE001 - related issues are best-effort
            return iids
        for issue in related:
            iid = issue.get("iid") if isinstance(issue, Mapping) else getattr(issue, "iid", None)
            if iid is not None:
                iids.append(int(iid))
        return iids

    def get_merge_base(self, project_id: int, refs: Sequence[str]) -> str:
        base = self._project(project_id).repository_merge_base(refs=list(refs))
        return base["id"]
