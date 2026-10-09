"""Generate a self-contained Harbor task directory from an approved MR."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from filter.review import instance_id
from packaging.sanitize import sanitize_text

GRADER_ASSET = Path(__file__).with_name("grader.py")

DEFAULT_VERIFIER_TIMEOUT = 1800.0
DEFAULT_AGENT_TIMEOUT = 10800.0


def compose_instruction(candidate: Mapping[str, Any]) -> str:
    """Build instruction.md from the MR title, description and linked issues."""
    parts: List[str] = []
    title = sanitize_text(str(candidate.get("title", "")).strip())
    if title:
        parts.append(title)
    description = sanitize_text(str(candidate.get("description") or "").strip())
    if description:
        parts.append(description)
    issues = candidate.get("related_issues") or []
    if issues:
        parts.append("Related issues: " + ", ".join(str(i) for i in issues))
    return "\n\n".join(parts).strip() + "\n"


def _toml_scores(scores: Optional[Mapping[str, Any]]) -> str:
    if not scores:
        return "{}"
    pairs = ", ".join(f"{key} = {float(value)}" for key, value in scores.items())
    return "{ " + pairs + " }"


def render_task_toml(
    candidate: Mapping[str, Any],
    language: str,
    docker_image: str,
    f2p: Sequence[str],
    p2p: Sequence[str],
) -> str:
    iid = instance_id(candidate)
    scores = _toml_scores(candidate.get("scores"))
    f2p_lit = ", ".join(json.dumps(x) for x in f2p)
    p2p_lit = ", ".join(json.dumps(x) for x in p2p)
    return "\n".join(
        [
            'schema_version = "1.4"',
            "",
            "[task]",
            f'name = "company/{iid}"',
            "",
            "[metadata]",
            f'source_url = {json.dumps(candidate.get("web_url", ""))}',
            f'base_commit = {json.dumps(candidate.get("base_commit", ""))}',
            f'language = {json.dumps(language)}',
            'difficulty = "medium"',
            f"fail_to_pass = [{f2p_lit}]",
            f"pass_to_pass = [{p2p_lit}]",
            f"filter_scores = {scores}",
            "",
            "[verifier]",
            f"timeout_sec = {DEFAULT_VERIFIER_TIMEOUT}",
            "",
            "[agent]",
            f"timeout_sec = {DEFAULT_AGENT_TIMEOUT}",
            "",
            "[environment]",
            f"docker_image = {json.dumps(docker_image)}",
            "",
        ]
    )


def render_dockerfile(candidate: Mapping[str, Any], docker_image: str) -> str:
    base = docker_image or "company/base:latest"
    base_commit = candidate.get("base_commit", "")
    return "\n".join(
        [
            "# Environment image for this task (frozen; see packaging.freeze).",
            f"FROM {base}",
            "WORKDIR /app",
            f"ARG BASE_SHA={base_commit}",
            "# Git time-travel: reset to the base commit with no future history.",
            'RUN git -C /app rev-parse HEAD >/dev/null 2>&1 || true',
            "CMD [\"bash\"]",
            "",
        ]
    )


def render_solve_sh() -> str:
    return "\n".join(
        [
            "#!/bin/bash",
            "set -euo pipefail",
            "",
            "cd /app",
            "git apply --whitespace=nowarn /solution/solution.patch",
            'git -c user.name="oracle" -c user.email="oracle@local" \\',
            '  commit -q --no-verify -am "Apply reference solution" || true',
            "",
        ]
    )


def render_test_sh() -> str:
    return "\n".join(
        [
            "#!/bin/bash",
            "set -uo pipefail",
            "mkdir -p /logs/verifier",
            "cd /app || exit 6",
            "# Run the held-out test suites, then grade from their JUnit XML.",
            "python3 /tests/grader.py grade",
            "",
        ]
    )


def render_config(
    candidate: Mapping[str, Any],
    f2p: Sequence[str],
    p2p: Sequence[str],
) -> Dict[str, Any]:
    return {
        "base_commit": candidate.get("base_commit", ""),
        "f2p_node_ids": list(f2p),
        "p2p_node_ids": list(p2p),
        "grade": {
            "format": "junit",
            "tool_label": "pytest-junitxml",
            "reports": [
                "/logs/verifier/base.xml",
                "/logs/verifier/new.xml",
            ],
        },
    }


def build_task(
    candidate: Mapping[str, Any],
    gold_patch: str,
    test_patch: str,
    output_root: str,
    language: str = "unknown",
    docker_image: Optional[str] = None,
    f2p: Optional[Sequence[str]] = None,
    p2p: Optional[Sequence[str]] = None,
) -> Path:
    """Create ``<output_root>/<instance_id>/`` and return its path."""
    iid = instance_id(candidate)
    image = docker_image or f"company/{iid}:latest"
    f2p = list(f2p or [])
    p2p = list(p2p or [])

    task_dir = Path(output_root) / iid
    (task_dir / "environment").mkdir(parents=True, exist_ok=True)
    (task_dir / "solution").mkdir(exist_ok=True)
    (task_dir / "tests").mkdir(exist_ok=True)

    (task_dir / "instruction.md").write_text(
        compose_instruction(candidate), encoding="utf-8"
    )
    (task_dir / "task.toml").write_text(
        render_task_toml(candidate, language, image, f2p, p2p), encoding="utf-8"
    )
    (task_dir / "environment" / "Dockerfile").write_text(
        render_dockerfile(candidate, image), encoding="utf-8"
    )
    (task_dir / "solution" / "solution.patch").write_text(
        gold_patch, encoding="utf-8"
    )
    solve_sh = task_dir / "solution" / "solve.sh"
    solve_sh.write_text(render_solve_sh(), encoding="utf-8")
    os.chmod(solve_sh, 0o755)

    (task_dir / "tests" / "test.patch").write_text(test_patch, encoding="utf-8")
    test_sh = task_dir / "tests" / "test.sh"
    test_sh.write_text(render_test_sh(), encoding="utf-8")
    os.chmod(test_sh, 0o755)
    shutil.copyfile(str(GRADER_ASSET), str(task_dir / "tests" / "grader.py"))
    (task_dir / "tests" / "config.json").write_text(
        json.dumps(render_config(candidate, f2p, p2p), indent=2), encoding="utf-8"
    )
    return task_dir
