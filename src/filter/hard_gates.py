"""Hard gates: MRs that fail any gate are rejected before scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from config import Settings
from mining.models import MRRecord
from paths import is_test_path

_DOC_SUFFIXES = (".md", ".rst", ".adoc")
_CONFIG_SUFFIXES = (".cfg", ".ini", ".toml", ".yaml", ".yml", ".json")
_I18N_SUFFIXES = (".po", ".mo")
_GENERATED_SUFFIXES = (".min.js", ".pb.go", ".pb.cc", ".pb.h")
_DEP_FILENAMES = {
    "requirements.txt",
    "go.mod",
    "go.sum",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "cargo.lock",
    "cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
}
_IGNORED_DIRS = {
    "docs",
    "doc",
    ".github",
    ".gitlab",
    "ci",
    "i18n",
    "locale",
    "locales",
    "dist",
    "build",
    "vendor",
    "node_modules",
    "generated",
}


@dataclass
class GateResult:
    passed: bool
    reasons: List[str] = field(default_factory=list)


def count_changed_lines(diff: str) -> int:
    """Count added/removed content lines in a unified diff."""
    count = 0
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            count += 1
    return count


def find_sensitive(diff: str, patterns: Sequence[str]) -> List[str]:
    return [p for p in patterns if p in diff]


def is_ignored_source(path: str) -> bool:
    """True for docs/config/deps/i18n/generated files that are not 'real' code."""
    name = path.replace("\\", "/").lower()
    segments = name.split("/")
    filename = segments[-1]
    if any(seg in _IGNORED_DIRS for seg in segments[:-1]):
        return True
    if name.endswith(_DOC_SUFFIXES) or name.endswith(_CONFIG_SUFFIXES):
        return True
    if name.endswith(_I18N_SUFFIXES) or name.endswith(_GENERATED_SUFFIXES):
        return True
    if filename in _DEP_FILENAMES:
        return True
    if filename.startswith("requirements") and filename.endswith(".txt"):
        return True
    if filename.endswith("_pb2.py"):
        return True
    return False


def source_files(mr: MRRecord, settings: Settings) -> List[str]:
    """Changed files that are neither tests nor ignorable noise."""
    result = []
    for path in mr.changed_files:
        if is_test_path(path, settings.test_path_keywords):
            continue
        if is_ignored_source(path):
            continue
        result.append(path)
    return result


def _is_revert_or_merge(mr: MRRecord) -> bool:
    if mr.title.strip().lower().startswith("revert"):
        return True
    if mr.commits and all(
        str(c.get("title", "")).strip().lower().startswith("merge")
        for c in mr.commits
    ):
        return True
    return False


def evaluate_gates(mr: MRRecord, settings: Settings) -> GateResult:
    reasons: List[str] = []

    if not mr.merged_at:
        reasons.append("not_merged")
    if _is_revert_or_merge(mr):
        reasons.append("revert_or_merge")
    if not source_files(mr, settings):
        reasons.append("no_source_changes")

    file_count = len(mr.changed_files)
    changed_lines = count_changed_lines(mr.diff)
    if file_count < settings.size_min_files or file_count > settings.size_max_files:
        reasons.append("file_count_out_of_range")
    if (
        changed_lines < settings.size_min_changed_lines
        or changed_lines > settings.size_max_changed_lines
    ):
        reasons.append("changed_lines_out_of_range")

    if not mr.test_files_changed:
        reasons.append("no_test_changes")

    sensitive = find_sensitive(mr.diff, settings.sensitive_patterns)
    if sensitive:
        reasons.append("sensitive:" + ",".join(sensitive))

    return GateResult(passed=not reasons, reasons=reasons)
