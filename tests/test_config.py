import textwrap

import pytest

import config as config_mod
from config import ConfigError, RepoConfig, Settings, load_repos, load_settings

REPOS_YAML = textwrap.dedent(
    """
    repos:
      - group: acme
        repo: svc
        language: python
        default_branch: main
    """
)

SETTINGS_YAML = textwrap.dedent(
    """
    mining:
      time_window_months: 3
    filter:
      size:
        min_files: 2
        max_files: 10
        min_changed_lines: 4
        max_changed_lines: 300
      weights:
        verifiable_test: 40
        reproducible_env: 20
        self_contained: 20
        business_representativeness: 10
        size: 10
      top_n: 7
    """
)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def test_load_repos(tmp_path):
    repos = load_repos(_write(tmp_path, "repos.yaml", REPOS_YAML))
    assert repos == [RepoConfig("acme", "svc", "python", "main")]
    assert repos[0].full_name == "acme/svc"


def test_load_settings_overrides(tmp_path):
    settings = load_settings(_write(tmp_path, "settings.yaml", SETTINGS_YAML))
    assert settings.time_window_months == 3
    assert settings.size_max_changed_lines == 300
    assert settings.top_n == 7
    assert sum(settings.weights.values()) == 100
    # Unspecified keys fall back to defaults.
    assert settings.test_path_keywords == ["test", "tests", "e2e", "testing"]


def test_load_settings_defaults_from_repo_config():
    settings = load_settings(config_mod.DEFAULT_SETTINGS_PATH)
    assert isinstance(settings, Settings)
    assert settings.time_window_months == 6
    assert settings.top_n == 50
    assert sum(settings.weights.values()) == 100


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_repos(str(tmp_path / "nope.yaml"))


def test_malformed_repos_raises(tmp_path):
    bad = textwrap.dedent(
        """
        repos:
          - group: acme
            language: python
        """
    )
    with pytest.raises(ConfigError):
        load_repos(_write(tmp_path, "repos.yaml", bad))
