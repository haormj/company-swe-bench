"""Split an MR diff into a gold patch (source) and a test patch (tests).

Classification is by file path keywords, mirroring SWE-bench's
``extract_patches``: any file whose path looks like a test file goes to the
test patch, everything else to the gold patch.
"""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple

from paths import is_test_path

_GIT_HEADER_RE = re.compile(r'^diff --git "?a/(.+?)"? "?b/(.+?)"?\s*$')
_PLUS_RE = re.compile(r"^\+\+\+ b/(.+?)\s*$")


def _path_from_diff_header(line: str) -> str:
    match = _GIT_HEADER_RE.match(line.rstrip("\n"))
    if match:
        return match.group(2)
    return ""


def split_diff_by_file(diff: str) -> List[Tuple[str, str]]:
    """Return ``[(path, chunk), ...]`` split on ``diff --git`` boundaries."""
    chunks: List[Tuple[str, str]] = []
    current: List[str] = []
    current_path = ""
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current:
                chunks.append((current_path, "".join(current)))
            current = [line]
            current_path = _path_from_diff_header(line)
            continue
        if not current:
            # Preamble before the first file header; keep it with no path.
            continue
        current.append(line)
        if not current_path:
            plus = _PLUS_RE.match(line.rstrip("\n"))
            if plus:
                current_path = plus.group(1)
    if current:
        chunks.append((current_path, "".join(current)))
    return chunks


def split_patch(diff: str, keywords: Sequence[str]) -> Tuple[str, str]:
    """Return ``(gold_patch, test_patch)``."""
    gold_parts: List[str] = []
    test_parts: List[str] = []
    for path, chunk in split_diff_by_file(diff):
        if path and is_test_path(path, keywords):
            test_parts.append(chunk)
        else:
            gold_parts.append(chunk)
    return "".join(gold_parts), "".join(test_parts)
