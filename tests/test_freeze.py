from packaging.freeze import (
    build_image,
    freeze_environment,
    push_image,
    render_frozen_dockerfile,
)


def test_render_contains_time_travel_and_install():
    text = render_frozen_dockerfile(
        repo_url="https://gitlab.internal/example/svc.git",
        base_commit="abc123",
        base_image="python:3.9-slim",
        install_commands=["pip install -e ."],
    )
    assert "FROM python:3.9-slim" in text
    assert "git clone https://gitlab.internal/example/svc.git ." in text
    assert "git checkout -B" in text
    assert "abc123" in text
    assert "git reflog expire --expire=now --all" in text
    assert "git gc --prune=now" in text
    assert "RUN pip install -e ." in text


def test_render_uses_local_context_when_given():
    text = render_frozen_dockerfile(
        repo_url="ignored",
        base_commit="sha",
        repo_context="repo",
    )
    assert "COPY repo /tmp/source-repo" in text
    assert "git clone /tmp/source-repo ." in text
    assert "git clone ignored" not in text


def test_build_image_invokes_docker(tmp_path):
    calls = []

    def fake_run(cmd, check):
        calls.append((cmd, check))
        return None

    build_image(str(tmp_path), "img:latest", "FROM scratch\n", run=fake_run)
    assert calls[0][0] == ["docker", "build", "-t", "img:latest", str(tmp_path)]
    assert calls[0][1] is True
    assert (tmp_path / "Dockerfile").read_text() == "FROM scratch\n"


def test_freeze_environment_builds_and_pushes():
    calls = []

    def fake_run(cmd, check):
        calls.append(cmd)
        return None

    tag = freeze_environment(
        repo_url="url",
        base_commit="sha",
        instance_id="101__12",
        context_dir="/tmp/csb-freeze",
        registry="registry.corp.local",
        push=True,
        run=fake_run,
    )
    assert tag == "registry.corp.local/101__12:latest"
    assert calls[0][:3] == ["docker", "build", "-t"]
    assert calls[1] == ["docker", "push", "registry.corp.local/101__12:latest"]


def test_push_image_invokes_docker():
    calls = []

    def fake_run(cmd, check):
        calls.append(cmd)
        return None

    push_image("img:latest", run=fake_run)
    assert calls == [["docker", "push", "img:latest"]]


def test_freeze_stages_repo_context(tmp_path):
    source = tmp_path / "repo"
    source.mkdir()
    (source / "app.txt").write_text("v1\n")
    context = tmp_path / "context"

    def fake_run(cmd, check):
        # The staged repo must exist in the build context.
        assert (context / "repo" / "app.txt").exists()
        return None

    freeze_environment(
        repo_url="ignored",
        base_commit="sha",
        instance_id="i",
        context_dir=str(context),
        repo_context=str(source),
        run=fake_run,
    )
    assert (context / "repo" / "app.txt").read_text() == "v1\n"
