"""Solvability checks for packaged tasks.

A task is kept only if its gold patch applies cleanly to the base commit and
its FAIL_TO_PASS list is non-empty. Rejected tasks are appended to a
``rejects.log`` (JSONL) with reasons.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Sequence

from io_utils import append_jsonl


@dataclass
class SolvabilityResult:
    ok: bool
    reasons: List[str] = field(default_factory=list)


def evaluate_solvability(
    gold_applies: bool, f2p: Sequence[str]
) -> SolvabilityResult:
    reasons: List[str] = []
    if not gold_applies:
        reasons.append("gold_patch_not_applied")
    if not f2p:
        reasons.append("empty_fail_to_pass")
    return SolvabilityResult(ok=not reasons, reasons=reasons)


def check_gold_patch(
    repo_dir: str,
    patch_text: str,
    run: Callable[..., "subprocess.CompletedProcess"] = subprocess.run,
) -> bool:
    """Return True if *patch_text* applies cleanly to *repo_dir*."""
    if not patch_text.strip():
        return False
    fd, path = tempfile.mkstemp(suffix=".patch")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(patch_text)
        proc = run(
            ["git", "-C", repo_dir, "apply", "--check", path],
            capture_output=True,
        )
        return getattr(proc, "returncode", 1) == 0
    finally:
        os.unlink(path)


def record_reject(
    rejects_path: str, instance_id: str, reasons: Sequence[str]
) -> None:
    append_jsonl(rejects_path, [{"instance_id": instance_id, "reasons": list(reasons)}])


def validate_task(
    instance_id: str,
    gold_applies: bool,
    f2p: Sequence[str],
    rejects_path: str,
) -> SolvabilityResult:
    """Evaluate and, when rejected, record the task to *rejects_path*."""
    result = evaluate_solvability(gold_applies, f2p)
    if not result.ok:
        record_reject(rejects_path, instance_id, result.reasons)
    return result
