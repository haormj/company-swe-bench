from packaging.patch_split import split_diff_by_file, split_patch

KEYWORDS = ["test", "tests", "e2e", "testing"]

DIFF = (
    "diff --git a/src/app.py b/src/app.py\n"
    "index 111..222 100644\n"
    "--- a/src/app.py\n"
    "+++ b/src/app.py\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
    "diff --git a/tests/test_app.py b/tests/test_app.py\n"
    "index 333..444 100644\n"
    "--- a/tests/test_app.py\n"
    "+++ b/tests/test_app.py\n"
    "@@ -1 +1 @@\n"
    "+assert True\n"
)

NEW_TEST_DIFF = (
    "diff --git a/tests/test_new.py b/tests/test_new.py\n"
    "new file mode 100644\n"
    "index 000..555\n"
    "--- /dev/null\n"
    "+++ b/tests/test_new.py\n"
    "@@ -0,0 +1 @@\n"
    "+def test_new():\n"
    "+    assert True\n"
)


def test_split_diff_by_file():
    chunks = split_diff_by_file(DIFF)
    assert [path for path, _ in chunks] == ["src/app.py", "tests/test_app.py"]


def test_split_patch_separates_source_and_tests():
    gold, test = split_patch(DIFF, KEYWORDS)
    assert "src/app.py" in gold
    assert "tests/test_app.py" not in gold
    assert "tests/test_app.py" in test
    assert "src/app.py" not in test


def test_split_patch_handles_new_test_file():
    gold, test = split_patch(NEW_TEST_DIFF, KEYWORDS)
    assert gold == ""
    assert "tests/test_new.py" in test
    assert "test_new" in test


def test_split_patch_empty():
    assert split_patch("", KEYWORDS) == ("", "")
