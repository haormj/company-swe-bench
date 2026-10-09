"""Compute FAIL_TO_PASS / PASS_TO_PASS from a before/after test differential.

The before run applies the test patch (not the gold patch); the after run
applies both. Tests that flip failed -> passed are F2P; tests passing in both
are P2P.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Protocol, Sequence


@dataclass
class DifferentialResult:
    f2p: List[str]
    p2p: List[str]

    @property
    def usable(self) -> bool:
        """A task is objectively judgeable only with non-empty F2P."""
        return len(self.f2p) > 0


class TestRunner(Protocol):
    def run(self, patches: Sequence[str]) -> Mapping[str, str]:
        """Apply *patches* in the task environment, run tests, return
        ``{node_id: status}``."""
        ...


def compute_differential(
    before: Mapping[str, str], after: Mapping[str, str]
) -> DifferentialResult:
    f2p = sorted(
        node for node, status in after.items()
        if status == "passed" and before.get(node) != "passed"
    )
    p2p = sorted(
        node for node, status in after.items()
        if status == "passed" and before.get(node) == "passed"
    )
    return DifferentialResult(f2p=f2p, p2p=p2p)


def compute_f2p_p2p(
    runner: TestRunner, test_patch: str, gold_patch: str
) -> DifferentialResult:
    before = runner.run([test_patch])
    after = runner.run([test_patch, gold_patch])
    return compute_differential(before, after)
