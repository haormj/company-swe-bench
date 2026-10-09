from config import load_settings
from filter.hard_gates import (
    count_changed_lines,
    evaluate_gates,
    is_ignored_source,
    source_files,
)
from support import make_mr

SETTINGS = load_settings()


def test_passing_mr_has_no_reasons():
    result = evaluate_gates(make_mr(), SETTINGS)
    assert result.passed
    assert result.reasons == []


def test_reject_not_merged():
    result = evaluate_gates(make_mr(merged_at=""), SETTINGS)
    assert not result.passed
    assert "not_merged" in result.reasons


def test_reject_revert():
    result = evaluate_gates(make_mr(title="Revert 'Add feature'"), SETTINGS)
    assert "revert_or_merge" in result.reasons


def test_reject_no_source_changes():
    mr = make_mr(changed_files=["tests/test_only.py"])
    result = evaluate_gates(mr, SETTINGS)
    assert "no_source_changes" in result.reasons


def test_reject_docs_only():
    mr = make_mr(changed_files=["docs/readme.md", "docs/guide.md"])
    result = evaluate_gates(mr, SETTINGS)
    assert "no_source_changes" in result.reasons


def test_reject_no_test_changes():
    mr = make_mr(changed_files=["src/app.py"])
    result = evaluate_gates(mr, SETTINGS)
    assert "no_test_changes" in result.reasons


def test_reject_size_out_of_range():
    many = [f"src/mod{i}.py" for i in range(25)] + ["tests/test_app.py"]
    result = evaluate_gates(make_mr(changed_files=many), SETTINGS)
    assert "file_count_out_of_range" in result.reasons


def test_reject_tiny_change():
    mr = make_mr(
        changed_files=["src/app.py", "tests/test_app.py"],
        diff="+a\n+b\n",
    )
    result = evaluate_gates(mr, SETTINGS)
    assert "changed_lines_out_of_range" in result.reasons


def test_reject_sensitive_content():
    mr = make_mr(diff="+-----BEGIN PRIVATE KEY-----\n+secret\n")
    result = evaluate_gates(mr, SETTINGS)
    assert any(r.startswith("sensitive:") for r in result.reasons)


def test_count_changed_lines_ignores_headers():
    diff = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n+add\n-rem\n"
    assert count_changed_lines(diff) == 2


def test_is_ignored_source_classification():
    assert is_ignored_source("docs/readme.md")
    assert is_ignored_source("go.mod")
    assert is_ignored_source("locale/messages.po")
    assert is_ignored_source("dist/bundle.js")
    assert not is_ignored_source("src/service/handler.py")
    assert not is_ignored_source("src/fastest.py")


def test_source_files_excludes_tests_and_noise():
    mr = make_mr(changed_files=["src/app.py", "docs/x.md", "tests/test_app.py"])
    assert source_files(mr, SETTINGS) == ["src/app.py"]
