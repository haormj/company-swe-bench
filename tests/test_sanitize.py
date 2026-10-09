from packaging.sanitize import (
    find_internal_links,
    find_sensitive,
    is_clean,
    sanitize_text,
)


def test_sanitize_removes_internal_links_keeps_public():
    text = "see https://gitlab.internal/acme/svc and https://example.com/docs"
    cleaned = sanitize_text(text)
    assert "gitlab.internal" not in cleaned
    assert "https://example.com/docs" in cleaned


def test_sanitize_masks_secrets():
    cleaned = sanitize_text("token -----BEGIN PRIVATE KEY----- and AKIA123")
    assert "PRIVATE KEY" not in cleaned
    assert "AKIA123" not in cleaned
    assert "[redacted-secret]" in cleaned


def test_helpers():
    text = "go to https://wiki.corp/page and use AKIA123"
    assert find_internal_links(text) == ["https://wiki.corp/page"]
    assert "AKIA" in find_sensitive(text)
    assert not is_clean(text)
    assert is_clean("plain public text https://example.com")


def test_build_task_instruction_is_clean(tmp_path):
    from config import load_settings
    from filter.pipeline import build_candidates
    from packaging.task_builder import build_task
    from support import make_mr

    candidate = build_candidates([make_mr(iid=1)], load_settings())[0]
    candidate["description"] = "Internal ref https://gitlab.internal/x/y and AKIA123"
    task_dir = build_task(candidate, "gold", "test", str(tmp_path))
    instruction = (task_dir / "instruction.md").read_text()
    assert is_clean(instruction)
    assert "gitlab.internal" not in instruction
