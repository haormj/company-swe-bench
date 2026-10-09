"""Path classification helpers shared by mining and packaging."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple


def is_test_path(path: str, keywords: Sequence[str]) -> bool:
    """Return True if *path* looks like a test file.

    A keyword matches only on a path boundary (start, ``/``, ``.``, ``_`` or
    ``-``), so ``fastest.py`` does not match ``test`` while ``tests/test_x.py``
    and ``src/x_test.py`` do.
    """
    name = path.lower().replace("\\", "/")
    for kw in keywords:
        kw = kw.lower()
        if re.search(r"(^|[/._-])" + re.escape(kw) + r"([/._-]|$)", name):
            return True
    return False


def classify_changed_files(
    paths: Iterable[str], keywords: Sequence[str]
) -> Tuple[List[str], List[str]]:
    """Split *paths* into ``(test_files, source_files)``."""
    test_files: List[str] = []
    source_files: List[str] = []
    for path in paths:
        if is_test_path(path, keywords):
            test_files.append(path)
        else:
            source_files.append(path)
    return test_files, source_files
