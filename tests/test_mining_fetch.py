from config import RepoConfig, load_settings
from io_utils import read_jsonl, write_jsonl
from mining.miner import Miner
from support import FakeGitLabClient

REPO = RepoConfig("example", "svc", "python", "main")
SETTINGS = load_settings()


def _miner():
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    return client, Miner(client, SETTINGS)


def test_fetch_page_parses_fields(tmp_path):
    client, miner = _miner()
    client.add_mr(
        101,
        12,
        changed_files=["src/app.py", "tests/test_app.py"],
        diff="diff --git a/src/app.py b/src/app.py\n",
        labels=["feature"],
        related_issues=[7],
    )

    records = miner.fetch_page(REPO, page=1)

    assert len(records) == 1
    rec = records[0]
    assert rec.key == "101!12"
    assert rec.title == "MR 12"
    assert rec.author == "alice"
    assert rec.labels == ["feature"]
    assert rec.changed_files == ["src/app.py", "tests/test_app.py"]
    assert rec.test_files_changed == ["tests/test_app.py"]
    assert rec.related_issues == [7]
    assert rec.target_branch == "main"
    assert rec.diff.startswith("diff --git")


def test_dump_schema_roundtrip(tmp_path):
    client, miner = _miner()
    client.add_mr(101, 12, changed_files=["src/app.py", "tests/test_app.py"])
    records = miner.fetch_page(REPO, page=1)

    path = tmp_path / "mr_dump.jsonl"
    write_jsonl(str(path), [r.to_dict() for r in records])
    loaded = list(read_jsonl(str(path)))

    assert len(loaded) == 1
    expected_keys = {
        "project_id",
        "mr_iid",
        "title",
        "description",
        "author",
        "merged_at",
        "labels",
        "changed_files",
        "diff",
        "commits",
        "related_issues",
        "base_commit",
        "test_files_changed",
        "source_branch",
        "target_branch",
        "web_url",
    }
    assert set(loaded[0]) == expected_keys


def test_reconstruct_diff_headers():
    from mining.client import reconstruct_diff
    from packaging.patch_split import split_diff_by_file

    changes = [
        {"old_path": "src/a.py", "new_path": "src/a.py",
         "diff": "@@ -1 +1 @@\n-old\n+new\n"},
        {"old_path": "tests/t.py", "new_path": "tests/t.py", "new_file": True,
         "diff": "@@ -0,0 +1 @@\n+assert 1\n"},
    ]
    text = reconstruct_diff(changes)
    paths = [p for p, _ in split_diff_by_file(text)]
    assert paths == ["src/a.py", "tests/t.py"]
    assert "--- /dev/null" in text  # new-file marker preserved
