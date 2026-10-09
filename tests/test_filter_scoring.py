from config import load_settings
from filter.pipeline import build_candidates
from filter.scoring import score_mr
from support import make_mr

SETTINGS = load_settings()


def _strong_mr():
    return make_mr(
        iid=1,
        changed_files=[
            "src/service/handler.py",
            "tests/test_handler.py",
            "pyproject.toml",
        ],
        title="Add handler feature",
        labels=["feature"],
        related_issues=[7],
        description="x" * 80,
    )


def _weak_mr():
    return make_mr(
        iid=2,
        changed_files=["src/x.py", "tests/test_x.py"],
        title="Add feature",
        labels=[],
        related_issues=[],
        description="short",
    )


def test_score_dimensions_and_total():
    result = score_mr(_strong_mr(), SETTINGS)
    assert set(result.scores) == {
        "verifiable_test",
        "reproducible_env",
        "self_contained",
        "business_representativeness",
        "size",
    }
    assert 0 < result.total <= 100
    assert result.total == round(sum(result.scores.values()), 2)
    # Every dimension has a reason.
    assert set(result.reasons) == set(result.scores)


def test_build_candidates_sorted_and_filtered():
    records = [_weak_mr(), _strong_mr(), make_mr(iid=3, changed_files=["src/y.py"])]
    candidates = build_candidates(records, SETTINGS)

    # The MR with no test changes (iid=3) is gated out.
    assert {c["mr_iid"] for c in candidates} == {1, 2}
    # Sorted by total descending.
    totals = [c["total"] for c in candidates]
    assert totals == sorted(totals, reverse=True)
    assert candidates[0]["mr_iid"] == 1
    # Each candidate carries scores, total and reasons.
    assert set(candidates[0]["scores"]) == set(SETTINGS.weights)
    assert "score_reasons" in candidates[0]


def test_build_candidates_respects_top_n():
    candidates = build_candidates([_weak_mr(), _strong_mr()], SETTINGS, top_n=1)
    assert len(candidates) == 1
    assert candidates[0]["mr_iid"] == 1
