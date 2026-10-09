"""Persistent checkpoint of already-processed MRs for resumable mining."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Set


class Checkpoint:
    """A set of processed MR keys, persisted to JSON when a path is given."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path
        self.keys: Set[str] = set()
        if path and Path(path).exists():
            self.keys = set(json.loads(Path(path).read_text(encoding="utf-8")))

    def __contains__(self, key: str) -> bool:
        return key in self.keys

    def add(self, key: str) -> None:
        self.keys.add(key)
        self.save()

    def save(self) -> None:
        if not self.path:
            return
        p = Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(sorted(self.keys)), encoding="utf-8")
