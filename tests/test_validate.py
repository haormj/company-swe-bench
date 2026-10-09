from io_utils import read_jsonl
from packaging.validate import (
    check_gold_patch,
    evaluate_solvability,
    record_reject,
    validate_task,
)


class FakeProc:
    def __init__(self, returncode):
        self.returncode = returncode


def test_evaluate_solvability_ok():
    result = evaluate_solvability(gold_applies=True, f2p=["t.x"])
    assert result.ok and result.reasons == []


def test_evaluate_solvability_gold_not_applied():
    result = evaluate_solvability(gold_applies=False, f2p=["t.x"])
    assert not result.ok
    assert result.reasons == ["gold_patch_not_applied"]


def test_evaluate_solvability_empty_f2p():
    result = evaluate_solvability(gold_applies=True, f2p=[])
    assert not result.ok
    assert result.reasons == ["empty_fail_to_pass"]


def test_check_gold_patch_success_and_failure():
    ok = check_gold_patch("/repo", "patch", run=lambda cmd, capture_output: FakeProc(0))
    bad = check_gold_patch("/repo", "patch", run=lambda cmd, capture_output: FakeProc(1))
    assert ok is True
    assert bad is False


def test_check_gold_patch_empty_patch_is_false():
    assert check_gold_patch("/repo", "  \n") is False


def test_record_and_validate_writes_rejects(tmp_path):
    rejects = tmp_path / "rejects.log"
    record_reject(str(rejects), "101__1", ["empty_fail_to_pass"])

    result = validate_task("101__2", gold_applies=False, f2p=[], rejects_path=str(rejects))
    assert not result.ok

    rows = list(read_jsonl(str(rejects)))
    assert rows == [
        {"instance_id": "101__1", "reasons": ["empty_fail_to_pass"]},
        {
            "instance_id": "101__2",
            "reasons": ["gold_patch_not_applied", "empty_fail_to_pass"],
        },
    ]


def test_validate_task_keeps_valid(tmp_path):
    rejects = tmp_path / "rejects.log"
    result = validate_task("101__3", True, ["t.x"], str(rejects))
    assert result.ok
    assert not rejects.exists()
