"""Freeze a reproducible environment image for a task.

The image is built once (checkout at the base commit, future history pruned,
dependencies installed) and then referenced from ``task.toml`` so runs never
depend on live package sources.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Optional, Sequence

DEFAULT_BASE_IMAGE = "python:3.9-slim"
APT_GIT_SETUP = (
    "apt-get update && apt-get install -y --no-install-recommends "
    "git ca-certificates && rm -rf /var/lib/apt/lists/*"
)

_TIME_TRAVEL = (
    "RUN {clone} \\\n"
    " && DEFAULT=\"$(git remote show origin 2>/dev/null "
    "| sed -n 's/.*HEAD branch: //p')\" \\\n"
    " && git checkout -B \"${{DEFAULT:-main}}\" {base_commit} \\\n"
    " && git remote remove origin 2>/dev/null || true \\\n"
    " && for b in $(git for-each-ref --format='%(refname:short)' refs/heads); "
    "do [ \"$b\" = \"${{DEFAULT:-main}}\" ] || git branch -D \"$b\" || true; done \\\n"
    " && for t in $(git tag); do "
    "git merge-base --is-ancestor \"$t\" HEAD 2>/dev/null || "
    "git tag -d \"$t\" || true; done \\\n"
    " && git reflog expire --expire=now --all \\\n"
    " && git gc --prune=now"
)


def render_frozen_dockerfile(
    repo_url: str,
    base_commit: str,
    base_image: str = DEFAULT_BASE_IMAGE,
    install_commands: Optional[Sequence[str]] = None,
    workdir: str = "/app",
    repo_context: Optional[str] = None,
    setup_command: str = APT_GIT_SETUP,
) -> str:
    """Render a Dockerfile that fixes the environment at ``base_commit``.

    ``repo_context`` copies a local checkout into the build context and clones
    from it (useful for offline/internal sources); otherwise ``repo_url`` is
    cloned directly.
    """
    install_commands = list(install_commands or [])
    lines: List[str] = [f"FROM {base_image}", ""]
    if setup_command:
        lines.append(f"RUN {setup_command}")
        lines.append("")
    if repo_context:
        lines.append(f"COPY {repo_context} /tmp/source-repo")
        clone = "git clone /tmp/source-repo ."
    else:
        clone = f"git clone {repo_url} ."
    lines.append(f"WORKDIR {workdir}")
    lines.append(_TIME_TRAVEL.format(clone=clone, base_commit=base_commit))
    for command in install_commands:
        lines.append(f"RUN {command}")
    lines.append('CMD ["bash"]')
    lines.append("")
    return "\n".join(lines)


def build_image(
    context_dir: str,
    image_tag: str,
    dockerfile_text: str,
    run: Callable[..., "subprocess.CompletedProcess"] = subprocess.run,
) -> "subprocess.CompletedProcess":
    context = Path(context_dir)
    context.mkdir(parents=True, exist_ok=True)
    (context / "Dockerfile").write_text(dockerfile_text, encoding="utf-8")
    return run(["docker", "build", "-t", image_tag, str(context)], check=True)


def push_image(
    image_tag: str,
    run: Callable[..., "subprocess.CompletedProcess"] = subprocess.run,
) -> "subprocess.CompletedProcess":
    return run(["docker", "push", image_tag], check=True)


def freeze_environment(
    repo_url: str,
    base_commit: str,
    instance_id: str,
    context_dir: str,
    base_image: str = DEFAULT_BASE_IMAGE,
    install_commands: Optional[Sequence[str]] = None,
    repo_context: Optional[str] = None,
    registry: Optional[str] = None,
    push: bool = False,
    setup_command: str = APT_GIT_SETUP,
    run: Callable[..., "subprocess.CompletedProcess"] = subprocess.run,
) -> str:
    """Build (and optionally push) the frozen image; return its tag."""
    tag = f"{registry}/{instance_id}:latest" if registry else f"{instance_id}:latest"
    context = Path(context_dir)
    context.mkdir(parents=True, exist_ok=True)

    context_repo_rel = None
    if repo_context:
        src = Path(repo_context)
        context_repo_rel = src.name
        dest = context / context_repo_rel
        if dest.resolve() != src.resolve():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)

    dockerfile_text = render_frozen_dockerfile(
        repo_url=repo_url,
        base_commit=base_commit,
        base_image=base_image,
        install_commands=install_commands,
        repo_context=context_repo_rel,
        setup_command=setup_command,
    )
    build_image(context_dir, tag, dockerfile_text, run=run)
    if push:
        push_image(tag, run=run)
    return tag
