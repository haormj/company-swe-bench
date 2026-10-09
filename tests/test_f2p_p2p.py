from packaging.f2p_p2p import compute_differential, compute_f2p_p2p


class FakeRunner:
    """Returns fixture results keyed by the number/order of patches."""

    def __init__(self, before, after):
        self.before = before
        self.after = after
        self.calls = []

    def run(self, patches):
        self.calls.append(list(patches))
        return self.before if len(patches) == 1 else self.after


def test_compute_differential_basic():
    before = {"t.old": "passed", "t.new": "failed", "t.regress": "passed"}
    after = {"t.old": "passed", "t.new": "passed", "t.regress": "failed"}
    result = compute_differential(before, after)
    assert result.f2p == ["t.new"]
    assert result.p2p == ["t.old"]
    assert result.usable


def test_f2p_and_p2p_disjoint():
    before = {"a": "failed", "b": "passed"}
    after = {"a": "passed", "b": "passed"}
    result = compute_differential(before, after)
    assert set(result.f2p) & set(result.p2p) == set()


def test_absent_before_counts_as_failing():
    # A brand-new test that only exists after is F2P, not P2P.
    result = compute_differential({}, {"t.new": "passed"})
    assert result.f2p == ["t.new"]
    assert result.p2p == []


def test_empty_f2p_not_usable():
    result = compute_differential({"a": "passed"}, {"a": "passed"})
    assert result.f2p == []
    assert not result.usable


def test_compute_f2p_p2p_runs_before_then_after():
    runner = FakeRunner(
        before={"t.x": "failed", "t.y": "passed"},
        after={"t.x": "passed", "t.y": "passed"},
    )
    result = compute_f2p_p2p(runner, test_patch="TEST", gold_patch="GOLD")
    assert runner.calls == [["TEST"], ["TEST", "GOLD"]]
    assert result.f2p == ["t.x"]
    assert result.p2p == ["t.y"]
    assert result.usable
