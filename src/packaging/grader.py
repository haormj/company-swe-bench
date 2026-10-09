#!/usr/bin/env python3
"""Harbor task verifier for company-swe-bench.

Reads per-task data from ``config.json`` next to this file and turns JUnit XML
reports into a reward. Intended to be copied verbatim into ``tests/grader.py``
inside each task directory and invoked by ``tests/test.sh``.

Config keys:
  base_commit    str
  f2p_node_ids   [str]  fail-to-pass whitelist (absence counts as failure)
  p2p_node_ids   [str]  pass-to-pass whitelist
  grade          {format: "junit", reports: [path, ...], tool_label: str}

Reward: 1 iff |f2p| > 0, every f2p passes and no p2p fails.
"""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def _default_tests_dir() -> Path:
    return Path(os.environ.get("TESTS_DIR", "/tests"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("VERIFIER_DIR", "/logs/verifier"))


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_junit_file(path: str) -> Dict[str, str]:
    """Return ``{node_id: status}`` for one JUnit XML report."""
    results: Dict[str, str] = {}
    try:
        root = ET.parse(path).getroot()
    except Exception:  # noqa: BLE001 - missing/unreadable report => no results
        return results
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        status = "passed"
        for child in testcase:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ("failure", "error"):
                status = "failed"
                break
            if tag == "skipped":
                status = "skipped"
        previous = results.get(node_id)
        if previous is None or _RANK[status] > _RANK[previous]:
            results[node_id] = status
    return results


def merge_reports(results: Dict[str, str], report: Mapping[str, str]) -> None:
    """Merge *report* into *results* worst-status-wins."""
    for node_id, status in report.items():
        previous = results.get(node_id)
        if previous is None or _RANK[status] > _RANK[previous]:
            results[node_id] = status


def grade(
    f2p_ids: Sequence[str],
    p2p_ids: Sequence[str],
    results: Mapping[str, str],
    apply_failed: bool = False,
) -> Dict[str, float]:
    f2p_total = len(f2p_ids)
    p2p_total = len(p2p_ids)
    f2p_passed = sum(1 for i in f2p_ids if results.get(i) == "passed")
    p2p_passed = sum(1 for i in p2p_ids if results.get(i) == "passed")
    f2p_failed = f2p_total - f2p_passed
    p2p_failed = p2p_total - p2p_passed
    reward = 1 if (f2p_total > 0 and f2p_failed == 0 and p2p_failed == 0) else 0
    total = f2p_total + p2p_total
    out: Dict[str, float] = {
        "reward": reward,
        "f2p_total": f2p_total,
        "f2p_passed": f2p_passed,
        "p2p_total": p2p_total,
        "p2p_passed": p2p_passed,
        "f2p": (f2p_passed / f2p_total) if f2p_total else 0.0,
        "p2p": (p2p_passed / p2p_total) if p2p_total else 1.0,
        "partial": ((f2p_passed + p2p_passed) / total) if total else 0.0,
    }
    if apply_failed:
        out["reward"] = 0
        out["apply_failed"] = 1
    return out


def run_grade(tests_dir: Path) -> Dict[str, float]:
    config = load_config(str(tests_dir / "config.json"))
    f2p = list(config.get("f2p_node_ids", []))
    p2p = list(config.get("p2p_node_ids", []))
    grade_cfg = config.get("grade", {}) or {}
    reports: Sequence[str] = grade_cfg.get("reports", []) or []
    results: Dict[str, str] = {}
    for report in reports:
        merge_reports(results, parse_junit_file(report))
    return grade(f2p, p2p, results)


def main(argv: List[str]) -> int:
    tests_dir = _default_tests_dir()
    command = argv[1] if len(argv) > 1 else "grade"
    if command != "grade":
        print(f"unknown command: {command}", file=sys.stderr)
        return 2
    out = run_grade(tests_dir)
    verifier_dir = _verifier_dir()
    verifier_dir.mkdir(parents=True, exist_ok=True)
    (verifier_dir / "reward.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(f"reward.json={json.dumps(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
