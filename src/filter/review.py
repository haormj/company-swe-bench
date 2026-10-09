"""Human review contract: candidate list in, ``reviewed.csv`` out.

The reviewer fills the ``keep`` column for each candidate. Only rows with a
truthy ``keep`` value proceed to packaging.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from io_utils import read_csv, write_csv

REVIEW_FIELDS = ["instance_id", "keep", "reason", "notes"]

_TRUTHY = {"yes", "y", "true", "1", "keep", "pass"}


def instance_id(candidate: Mapping[str, Any]) -> str:
    return f"{candidate['project_id']}__{candidate['mr_iid']}"


def seed_review_rows(
    candidates: Sequence[Mapping[str, Any]]
) -> List[Dict[str, str]]:
    """Build an empty review sheet (all decisions blank)."""
    return [
        {"instance_id": instance_id(c), "keep": "", "reason": "", "notes": ""}
        for c in candidates
    ]


def write_review_template(
    candidates: Sequence[Mapping[str, Any]], path: str
) -> None:
    write_csv(path, seed_review_rows(candidates), REVIEW_FIELDS)


def read_reviewed(path: str) -> List[Dict[str, str]]:
    return read_csv(path)


def approved_ids(rows: Sequence[Mapping[str, str]]) -> List[str]:
    """Return instance ids the reviewer marked keep=yes (supported spellings)."""
    approved: List[str] = []
    for row in rows:
        value = str(row.get("keep", "")).strip().lower()
        if value in _TRUTHY:
            approved.append(str(row["instance_id"]))
    return approved
