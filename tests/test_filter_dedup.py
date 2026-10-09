from config import load_settings
from filter.pipeline import build_candidates, dedup_candidates
from support import make_mr

SETTINGS = load_settings()


def _strong(issue):
    return make_mr(
        iid=1,
        changed_files=[
            "src/service/handler.py",
            "tests/test_handler.py",
            "pyproject.toml",
        ],
        title="Add handler feature",
        labels=["feature"],
        related_issues=[issue],
        description="x" * 80,
    )


def _weak(issue):
    return make_mr(
        iid=2,
        changed_files=["src/x.py", "tests/test_x.py"],
        title="Add feature",
        labels=[],
        related_issues=[issue],
        description="short",
    )


def test_dedup_same_issue_keeps_best():
    candidates = build_candidates([_weak(7), _strong(7)], SETTINGS)
    assert len(candidates) == 1
    assert candidates[0]["mr_iid"] == 1


def test_dedup_keeps_distinct_issues():
    candidates = build_candidates([_strong(7), _weak(8)], SETTINGS)
    assert {c["mr_iid"] for c in candidates} == {1, 2}


def test_dedup_no_issue_not_merged():
    a = make_mr(iid=10, changed_files=["src/a.py", "tests/test_a.py"], related_issues=[])
    b = make_mr(iid=11, changed_files=["src/b.py", "tests/test_b.py"], related_issues=[])
    candidates = build_candidates([a, b], SETTINGS)
    assert {c["mr_iid"] for c in candidates} == {10, 11}


def test_dedup_candidates_prefers_higher_total():
    low = {"project_id": 1, "mr_iid": 1, "related_issues": [7], "total": 10.0,
           "merged_at": "2026-01-01"}
    high = {"project_id": 1, "mr_iid": 2, "related_issues": [7], "total": 50.0,
            "merged_at": "2026-01-02"}
    out = dedup_candidates([low, high])
    assert len(out) == 1
    assert out[0]["mr_iid"] == 2
