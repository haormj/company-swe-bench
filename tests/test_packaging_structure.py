import json
from pathlib import Path

from config import load_settings
from filter.pipeline import build_candidates
from packaging.task_builder import build_task
from support import make_mr

SETTINGS = load_settings()
GOLD = "diff --git a/src/app.py b/src/app.py\n+new\n"
TEST = "diff --git a/tests/test_app.py b/tests/test_app.py\n+assert True\n"


def _candidate():
    return build_candidates([make_mr(iid=12)], SETTINGS)[0]


def test_build_task_creates_full_structure(tmp_path):
    task_dir = build_task(_candidate(), GOLD, TEST, str(tmp_path))
    assert task_dir.name == "101__12"
    for rel in [
        "instruction.md",
        "task.toml",
        "environment/Dockerfile",
        "solution/solve.sh",
        "solution/solution.patch",
        "tests/test.sh",
        "tests/grader.py",
        "tests/config.json",
        "tests/test.patch",
    ]:
        assert (task_dir / rel).exists(), rel


def test_instruction_contains_title(tmp_path):
    task_dir = build_task(_candidate(), GOLD, TEST, str(tmp_path))
    text = (task_dir / "instruction.md").read_text()
    assert "Add feature" in text


def test_config_json_contract(tmp_path):
    candidate = _candidate()
    task_dir = build_task(candidate, GOLD, TEST, str(tmp_path), f2p=["a.b"], p2p=["c.d"])
    config = json.loads((task_dir / "tests" / "config.json").read_text())
    assert config["base_commit"] == candidate["base_commit"]
    assert config["f2p_node_ids"] == ["a.b"]
    assert config["p2p_node_ids"] == ["c.d"]
    assert config["grade"]["format"] == "junit"


def test_task_toml_has_harbor_fields(tmp_path):
    task_dir = build_task(_candidate(), GOLD, TEST, str(tmp_path))
    toml = (task_dir / "task.toml").read_text()
    assert 'schema_version = "1.4"' in toml
    assert "[verifier]" in toml and "[agent]" in toml and "[environment]" in toml
    assert "base_commit" in toml


def test_grader_copied_into_tests(tmp_path):
    task_dir = build_task(_candidate(), GOLD, TEST, str(tmp_path))
    grader = (task_dir / "tests" / "grader.py").read_text()
    assert "def grade(" in grader
    # Copied grader must be self-contained (stdlib only).
    assert "import rewardkit" not in grader
