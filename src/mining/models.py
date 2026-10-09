"""Data model for a mined merge request."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass
class MRRecord:
    project_id: int
    mr_iid: int
    title: str
    description: str
    author: str
    merged_at: str
    labels: List[str]
    changed_files: List[str]
    diff: str
    commits: List[Dict[str, Any]]
    related_issues: List[int]
    base_commit: str
    test_files_changed: List[str]
    source_branch: str = ""
    target_branch: str = ""
    web_url: str = ""

    @property
    def key(self) -> str:
        """Stable identity used for resume/dedup."""
        return f"{self.project_id}!{self.mr_iid}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MRRecord":
        return cls(
            project_id=data["project_id"],
            mr_iid=data["mr_iid"],
            title=data.get("title", ""),
            description=data.get("description", "") or "",
            author=data.get("author", ""),
            merged_at=data.get("merged_at", "") or "",
            labels=list(data.get("labels", []) or []),
            changed_files=list(data.get("changed_files", []) or []),
            diff=data.get("diff", "") or "",
            commits=list(data.get("commits", []) or []),
            related_issues=list(data.get("related_issues", []) or []),
            base_commit=data.get("base_commit", "") or "",
            test_files_changed=list(data.get("test_files_changed", []) or []),
            source_branch=data.get("source_branch", "") or "",
            target_branch=data.get("target_branch", "") or "",
            web_url=data.get("web_url", "") or "",
        )
