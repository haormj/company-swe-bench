import json
from pathlib import Path

from packaging import grader

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="tests.test_app" tests="3">
    <testcase classname="tests.test_app" name="test_ok" time="0.1"/>
    <testcase classname="tests.test_app" name="test_bad" time="0.2">
      <failure message="boom">traceback</failure>
    </testcase>
    <testcase classname="tests.test_app" name="test_skip" time="0.0">
      <skipped message="not now"/>
    </testcase>
  </testsuite>
</testsuites>
"""


def _write(path, content):
    Path(path).write_text(content)
    return str(path)


def test_parse_junit_derives_classname_name(tmp_path):
    report = grader.parse_junit_file(_write(tmp_path / "r.xml", JUNIT))
    assert report == {
        "tests.test_app.test_ok": "passed",
        "tests.test_app.test_bad": "failed",
        "tests.test_app.test_skip": "skipped",
    }


def test_parse_junit_missing_file_is_empty():
    assert grader.parse_junit_file("/nonexistent/report.xml") == {}


def test_grade_all_pass():
    out = grader.grade(["a.ok"], ["b.ok"], {"a.ok": "passed", "b.ok": "passed"})
    assert out["reward"] == 1
    assert out["f2p_passed"] == 1 and out["p2p_passed"] == 1
    assert out["f2p"] == 1.0 and out["p2p"] == 1.0 and out["partial"] == 1.0


def test_grade_f2p_failure_blocks_reward():
    out = grader.grade(["a.ok", "a.bad"], ["b.ok"], {"a.ok": "passed", "b.ok": "passed"})
    assert out["reward"] == 0
    assert out["f2p_passed"] == 1 and out["f2p"] == 0.5


def test_grade_p2p_failure_blocks_reward():
    out = grader.grade(["a.ok"], ["b.ok", "b.bad"], {"a.ok": "passed", "b.ok": "passed"})
    assert out["reward"] == 0
    assert out["p2p_passed"] == 1


def test_grade_absent_and_skipped_count_as_failed():
    out = grader.grade(["a.absent"], ["a.skipped"], {"a.skipped": "skipped"})
    assert out["reward"] == 0
    assert out["f2p_passed"] == 0 and out["p2p_passed"] == 0


def test_grade_empty_f2p_is_zero():
    assert grader.grade([], ["b.ok"], {"b.ok": "passed"})["reward"] == 0


def test_grade_apply_failed_forces_zero():
    out = grader.grade(["a.ok"], ["b.ok"], {}, apply_failed=True)
    assert out["reward"] == 0 and out["apply_failed"] == 1


def test_run_grade_reads_config_and_reports(tmp_path):
    report = _write(tmp_path / "new.xml", JUNIT)
    config = {
        "base_commit": "abc",
        "f2p_node_ids": ["tests.test_app.test_ok"],
        "p2p_node_ids": ["tests.test_app.test_skip"],
        "grade": {"format": "junit", "reports": [report]},
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    out = grader.run_grade(tmp_path)
    # test_ok passes; test_skip is skipped (counts as failed) => reward 0.
    assert out["reward"] == 0
    assert out["f2p_passed"] == 1 and out["p2p_passed"] == 0


def test_generated_test_sh_invokes_grader(tmp_path):
    from config import load_settings
    from filter.pipeline import build_candidates
    from packaging.task_builder import build_task
    from support import make_mr

    cand = build_candidates([make_mr(iid=1)], load_settings())[0]
    task_dir = build_task(cand, "gold", "test", str(tmp_path))
    assert "grader.py grade" in (task_dir / "tests" / "test.sh").read_text()
