"""Weighted scoring of MRs that passed the hard gates.

Each dimension contributes at most its configured weight. v1 uses heuristics
(no LLM). Every dimension records a short human-readable reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from config import Settings
from filter.hard_gates import count_changed_lines, source_files
from mining.models import MRRecord

_EXT_LANG = {
    ".py": "python",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
    ".c": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".ts": "ts",
    ".tsx": "ts",
    ".js": "js",
    ".jsx": "js",
}
_BUILD_HINTS = (
    "dockerfile",
    "cmakelists.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "go.mod",
    "cargo.toml",
    "package.json",
    "makefile",
    ".gitlab-ci.yml",
    "ci.yml",
    "tox.ini",
)
_ASSERTION_HINTS = (
    "assert",
    "expect",
    "should",
    "require(",
    "runtime_error",
    "catch_",
    "assert_eq",
)
_INTERNAL_LINK_RE = re.compile(
    r"https?://[^\s]*(internal|intranet|\.corp|wiki|gitlab\.internal)", re.IGNORECASE
)


@dataclass
class ScoreResult:
    scores: Dict[str, float]
    total: float
    reasons: Dict[str, str] = field(default_factory=dict)


def _dominant_language(paths: Sequence[str]) -> Optional[str]:
    counts: Dict[str, int] = {}
    for path in paths:
        lower = path.lower()
        for ext, lang in _EXT_LANG.items():
            if lower.endswith(ext):
                counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _has_build_config(paths: Sequence[str]) -> bool:
    return any(
        any(hint in path.lower() for hint in _BUILD_HINTS) for path in paths
    )


def _module_matches(source_paths: Sequence[str], test_paths: Sequence[str]) -> bool:
    stems = {Path(p).stem.lower() for p in source_paths if Path(p).stem}
    for test in test_paths:
        stem = Path(test).stem.lower().replace("test_", "").replace("_test", "")
        for src_stem in stems:
            if src_stem and (src_stem in stem or stem in src_stem):
                return True
    return False


def _score_verifiable(mr: MRRecord, settings: Settings) -> Tuple[float, str]:
    tests = mr.test_files_changed
    if not tests:
        return 0.0, "no test files"
    src = source_files(mr, settings)
    factor = 0.4
    notes = ["has tests"]
    if _module_matches(src, tests):
        factor += 0.3
        notes.append("test/source module match")
    has_assertion = any(h in mr.diff.lower() for h in _ASSERTION_HINTS)
    if has_assertion:
        factor += 0.3
        notes.append("assertions")
    snapshot_only = all("snapshot" in t.lower() for t in tests) and not has_assertion
    if snapshot_only:
        factor = min(factor, 0.2)
        notes.append("snapshot-only")
    return min(factor, 1.0), "; ".join(notes)


def _score_reproducible(mr: MRRecord, settings: Settings) -> Tuple[float, str]:
    src = source_files(mr, settings)
    lang = _dominant_language(src or mr.changed_files)
    factor = 0.0
    notes: List[str] = []
    if lang:
        factor += 0.6
        notes.append(f"language={lang}")
    if _has_build_config(mr.changed_files):
        factor += 0.4
        notes.append("build/CI config present")
    return min(factor, 1.0), "; ".join(notes) or "unrecognized"


def _score_self_contained(mr: MRRecord, settings: Settings) -> Tuple[float, str]:
    factor = 0.0
    notes: List[str] = []
    if len(mr.description) >= 50:
        factor += 0.4
        notes.append("description ok")
    if mr.related_issues:
        factor += 0.3
        notes.append("linked issue")
    if len(mr.title.strip()) >= 8:
        factor += 0.3
        notes.append("readable title")
    if _INTERNAL_LINK_RE.search(mr.title + " " + mr.description):
        factor -= 0.3
        notes.append("internal link penalty")
    return max(0.0, min(factor, 1.0)), "; ".join(notes) or "thin description"


def _score_business(mr: MRRecord, settings: Settings) -> Tuple[float, str]:
    src = source_files(mr, settings)
    factor = 0.0
    notes: List[str] = []
    if any(
        path.startswith(core) or f"/{core}" in path
        for path in src
        for core in settings.core_paths
    ):
        factor += 0.5
        notes.append("core path")
    if set(mr.labels) & set(settings.business_labels):
        factor += 0.5
        notes.append("business label")
    return min(factor, 1.0), "; ".join(notes) or "peripheral path"


def _score_size(mr: MRRecord, settings: Settings) -> Tuple[float, str]:
    files = len(mr.changed_files)
    lines = count_changed_lines(mr.diff)
    in_ideal = (
        settings.ideal_min_files <= files <= settings.ideal_max_files
        and settings.ideal_min_changed_lines
        <= lines
        <= settings.ideal_max_changed_lines
    )
    if in_ideal:
        return 1.0, f"ideal ({files} files, {lines} lines)"
    return 0.5, f"acceptable ({files} files, {lines} lines)"


def score_mr(mr: MRRecord, settings: Settings) -> ScoreResult:
    weight = settings.weights
    raw = {
        "verifiable_test": _score_verifiable(mr, settings),
        "reproducible_env": _score_reproducible(mr, settings),
        "self_contained": _score_self_contained(mr, settings),
        "business_representativeness": _score_business(mr, settings),
        "size": _score_size(mr, settings),
    }
    scores = {name: round(factor * weight[name], 2) for name, (factor, _) in raw.items()}
    reasons = {name: reason for name, (_, reason) in raw.items()}
    total = round(sum(scores.values()), 2)
    return ScoreResult(scores=scores, total=total, reasons=reasons)
