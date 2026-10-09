from config import RepoConfig, load_settings
from io_utils import read_jsonl
from mining.miner import Miner
from support import FakeGitLabClient

REPO = RepoConfig("example", "svc", "python", "main")
SETTINGS = load_settings()


def test_run_paginates_until_empty(tmp_path):
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    client.add_mr(101, 1, changed_files=["src/a.py"], page=1)
    client.add_mr(101, 2, changed_files=["src/b.py"], page=1)
    client.add_mr(101, 3, changed_files=["src/c.py"], page=2)

    out = tmp_path / "mr_dump.jsonl"
    records = Miner(client, SETTINGS).run([REPO], str(out), sleep=lambda _: None)

    assert {r.mr_iid for r in records} == {1, 2, 3}
    assert len(list(read_jsonl(str(out)))) == 3


def test_run_resumes_without_duplicates(tmp_path):
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    client.add_mr(101, 1, changed_files=["src/a.py"])
    client.add_mr(101, 2, changed_files=["src/b.py"])

    out = tmp_path / "mr_dump.jsonl"
    ckpt = tmp_path / "checkpoint.json"
    miner = Miner(client, SETTINGS)

    first = miner.run([REPO], str(out), str(ckpt), sleep=lambda _: None)
    second = miner.run([REPO], str(out), str(ckpt), sleep=lambda _: None)

    assert len(first) == 2
    assert second == []
    assert len(list(read_jsonl(str(out)))) == 2


def test_run_backs_off_on_transient_failure(tmp_path):
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    client.add_mr(101, 1, changed_files=["src/a.py"])
    client.fail_counts[("fetch_page", (101, 1))] = 2  # two transient failures

    delays = []
    out = tmp_path / "mr_dump.jsonl"
    records = Miner(client, SETTINGS).run(
        [REPO],
        str(out),
        sleep=delays.append,
        base_delay=1.0,
        max_retries=5,
    )

    assert [r.mr_iid for r in records] == [1]
    assert delays == [1.0, 2.0]  # exponential backoff
