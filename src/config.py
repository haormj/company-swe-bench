"""Shared configuration loading for the company-swe-bench pipeline.

Reads the YAML files under ``config/`` into typed objects consumed by the
mining, filter and packaging components. GitLab credentials are intentionally
NOT stored in these files; they are read from the environment at call time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

DEFAULT_REPOS_PATH = "config/repos.yaml"
DEFAULT_SETTINGS_PATH = "config/settings.yaml"

DEFAULT_WEIGHTS: Dict[str, int] = {
    "verifiable_test": 30,
    "reproducible_env": 25,
    "self_contained": 20,
    "business_representativeness": 15,
    "size": 10,
}


class ConfigError(ValueError):
    """Raised when a configuration file is malformed."""


@dataclass(frozen=True)
class RepoConfig:
    group: str
    repo: str
    language: str
    default_branch: str

    @property
    def full_name(self) -> str:
        return f"{self.group}/{self.repo}"


@dataclass(frozen=True)
class Settings:
    time_window_months: int = 6
    size_min_files: int = 1
    size_max_files: int = 20
    size_min_changed_lines: int = 5
    size_max_changed_lines: int = 500
    ideal_min_files: int = 2
    ideal_max_files: int = 8
    ideal_min_changed_lines: int = 20
    ideal_max_changed_lines: int = 200
    weights: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    top_n: int = 50
    sensitive_patterns: List[str] = field(
        default_factory=lambda: [
            "-----BEGIN",
            "PRIVATE KEY",
            "AKIA",
            "aws_secret_access_key",
        ]
    )
    business_labels: List[str] = field(
        default_factory=lambda: ["feature", "backend", "core", "service"]
    )
    core_paths: List[str] = field(default_factory=lambda: ["src/", "app/", "lib/"])
    test_path_keywords: List[str] = field(
        default_factory=lambda: ["test", "tests", "e2e", "testing"]
    )


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        try:
            return yaml.safe_load(fh)
        except yaml.YAMLError as exc:  # pragma: no cover - passthrough
            raise ConfigError(f"failed to parse {path}: {exc}") from exc


def load_repos(path: Optional[str] = None) -> List[RepoConfig]:
    """Load the list of target repositories from ``config/repos.yaml``."""
    raw = _read_yaml(Path(path or DEFAULT_REPOS_PATH)) or {}
    entries = raw.get("repos")
    if not isinstance(entries, list):
        raise ConfigError("repos.yaml must contain a top-level 'repos' list")
    repos: List[RepoConfig] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ConfigError("each repos entry must be a mapping")
        missing = {"group", "repo", "language", "default_branch"} - set(entry)
        if missing:
            raise ConfigError(f"repo entry missing keys: {sorted(missing)}")
        repos.append(
            RepoConfig(
                group=str(entry["group"]),
                repo=str(entry["repo"]),
                language=str(entry["language"]),
                default_branch=str(entry["default_branch"]),
            )
        )
    return repos


def load_settings(path: Optional[str] = None) -> Settings:
    """Load pipeline settings from ``config/settings.yaml`` with defaults."""
    raw = _read_yaml(Path(path or DEFAULT_SETTINGS_PATH)) or {}
    mining = raw.get("mining", {}) or {}
    filt = raw.get("filter", {}) or {}
    size = filt.get("size", {}) or {}
    ideal = filt.get("ideal_size", {}) or {}
    weights = filt.get("weights") or dict(DEFAULT_WEIGHTS)

    settings = Settings(
        time_window_months=int(mining.get("time_window_months", 6)),
        size_min_files=int(size.get("min_files", 1)),
        size_max_files=int(size.get("max_files", 20)),
        size_min_changed_lines=int(size.get("min_changed_lines", 5)),
        size_max_changed_lines=int(size.get("max_changed_lines", 500)),
        ideal_min_files=int(ideal.get("min_files", 2)),
        ideal_max_files=int(ideal.get("max_files", 8)),
        ideal_min_changed_lines=int(ideal.get("min_changed_lines", 20)),
        ideal_max_changed_lines=int(ideal.get("max_changed_lines", 200)),
        weights={str(k): int(v) for k, v in weights.items()},
        top_n=int(filt.get("top_n", 50)),
        sensitive_patterns=list(
            filt.get("sensitive_patterns", Settings().sensitive_patterns)
        ),
        business_labels=list(
            filt.get("business_labels", Settings().business_labels)
        ),
        core_paths=list(filt.get("core_paths", Settings().core_paths)),
        test_path_keywords=list(
            filt.get("test_path_keywords", Settings().test_path_keywords)
        ),
    )
    if not settings.weights:
        raise ConfigError("settings.weights must not be empty")
    return settings
