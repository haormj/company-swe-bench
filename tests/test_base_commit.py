from config import RepoConfig, load_settings
from mining.base_commit import compute_base_commit
from mining.miner import Miner
from support import FakeGitLabClient

REPO = RepoConfig("example", "svc", "python", "main")
SETTINGS = load_settings()


def test_compute_base_commit_queries_merge_base():
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    client.merge_bases[(101, ("sha12", "main"))] = "deadbeef"

    assert compute_base_commit(client, 101, "sha12", "main") == "deadbeef"


def test_compute_base_commit_missing_inputs():
    client = FakeGitLabClient()
    assert compute_base_commit(client, 101, "", "main") == ""
    assert compute_base_commit(client, 101, "sha12", "") == ""


def test_miner_sets_base_commit_from_merge_base():
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    client.merge_bases[(101, ("sha12", "main"))] = "basecafe"
    client.add_mr(101, 12, changed_files=["src/app.py", "tests/test_app.py"], sha="sha12")

    records = Miner(client, SETTINGS).fetch_page(REPO, page=1)

    assert records[0].base_commit == "basecafe"
