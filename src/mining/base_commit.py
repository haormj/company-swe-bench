"""Base commit resolution for a mined MR.

The base commit is the merge base of the MR head and its target branch: the
commit the evaluation environment is checked out at, and the preimage the
gold patch must apply to cleanly.
"""

from __future__ import annotations

from typing import Optional

from mining.client import GitLabClient


def compute_base_commit(
    client: GitLabClient,
    project_id: int,
    source_sha: str,
    target_branch: str,
) -> str:
    """Return the merge base of ``source_sha`` and ``target_branch``.

    Returns an empty string when either input is missing, so callers can skip
    MRs that lack enough information rather than erroring out.
    """
    if not source_sha or not target_branch:
        return ""
    return client.get_merge_base(project_id, [source_sha, target_branch])
