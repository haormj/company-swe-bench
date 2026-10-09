"""Mining phase: pull merged MRs and turn them into MRRecords."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from config import RepoConfig, Settings
from io_utils import append_jsonl
from mining.base_commit import compute_base_commit
from mining.checkpoint import Checkpoint
from mining.client import GitLabClient, GitLabError
from mining.models import MRRecord
from paths import classify_changed_files

T = TypeVar("T")


class Miner:
    """Fetches merged MRs for configured repositories.

    Pagination, resume and retry build on :meth:`fetch_page` (see
    :meth:`run`). The class is constructed with an injected client so it can
    be exercised without network access.
    """

    def __init__(
        self,
        client: GitLabClient,
        settings: Settings,
        per_page: int = 100,
    ) -> None:
        self.client = client
        self.settings = settings
        self.per_page = per_page

    def time_window(
        self, now: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """Return ``(since_iso, until_iso)`` for the configured window."""
        now = now or datetime.now(timezone.utc)
        since = now - timedelta(days=30 * self.settings.time_window_months)
        return since.isoformat(), now.isoformat()

    def build_record(
        self, repo: RepoConfig, project_id: int, raw: Dict[str, Any]
    ) -> MRRecord:
        iid = int(raw["iid"])
        changed = list(self.client.get_mr_changed_files(project_id, iid))
        test_files, _ = classify_changed_files(
            changed, self.settings.test_path_keywords
        )
        target_branch = raw.get("target_branch", "") or repo.default_branch
        base_commit = compute_base_commit(
            self.client, project_id, raw.get("sha", "") or "", target_branch
        )
        return MRRecord(
            project_id=project_id,
            mr_iid=iid,
            title=raw.get("title", "") or "",
            description=raw.get("description", "") or "",
            author=(raw.get("author") or {}).get("username", ""),
            merged_at=raw.get("merged_at", "") or "",
            labels=list(raw.get("labels", []) or []),
            changed_files=changed,
            diff=self.client.get_mr_diff(project_id, iid),
            commits=list(self.client.get_mr_commits(project_id, iid)),
            related_issues=list(self.client.get_related_issue_iids(project_id, iid)),
            base_commit=base_commit,
            test_files_changed=test_files,
            source_branch=raw.get("source_branch", "") or "",
            target_branch=target_branch,
            web_url=raw.get("web_url", "") or "",
        )

    def fetch_page(
        self,
        repo: RepoConfig,
        page: int,
        now: Optional[datetime] = None,
    ) -> List[MRRecord]:
        project_id = self.client.get_project_id(repo.group, repo.repo)
        since_iso, until_iso = self.time_window(now)
        raw_mrs = self.client.fetch_merged_mr_page(
            project_id, since_iso, until_iso, page, self.per_page
        )
        return [self.build_record(repo, project_id, raw) for raw in raw_mrs]

    def _with_retry(
        self,
        fn: Callable[[], T],
        sleep: Callable[[float], None],
        max_retries: int,
        base_delay: float,
    ) -> T:
        attempt = 0
        while True:
            try:
                return fn()
            except GitLabError:
                if attempt >= max_retries:
                    raise
                sleep(base_delay * (2 ** attempt))
                attempt += 1

    def run(
        self,
        repos: List[RepoConfig],
        output_path: str,
        checkpoint_path: Optional[str] = None,
        now: Optional[datetime] = None,
        sleep: Optional[Callable[[float], None]] = None,
        max_retries: int = 5,
        base_delay: float = 0.5,
    ) -> List[MRRecord]:
        """Mine all repos into ``output_path``, resuming from a checkpoint.

        Paginates each repo until an empty page, skips MRs already recorded in
        ``checkpoint_path``, and retries transient ``GitLabError`` with
        exponential backoff.
        """
        sleep = sleep or time.sleep
        checkpoint = Checkpoint(checkpoint_path)
        since_iso, until_iso = self.time_window(now)
        written: List[MRRecord] = []

        for repo in repos:
            project_id = self.client.get_project_id(repo.group, repo.repo)
            page = 1
            while True:
                raw_mrs = self._with_retry(
                    lambda pid=project_id, pg=page: self.client.fetch_merged_mr_page(
                        pid, since_iso, until_iso, pg, self.per_page
                    ),
                    sleep,
                    max_retries,
                    base_delay,
                )
                if not raw_mrs:
                    break
                for raw in raw_mrs:
                    key = f"{project_id}!{int(raw['iid'])}"
                    if key in checkpoint:
                        continue
                    record = self.build_record(repo, project_id, raw)
                    append_jsonl(output_path, [record.to_dict()])
                    checkpoint.add(record.key)
                    written.append(record)
                page += 1

        return written
