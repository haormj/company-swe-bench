"""End-to-end pipeline wiring: Mining -> Filter -> Review -> Packaging."""

from config import RepoConfig, load_settings
from filter.pipeline import build_candidates
from filter.review import (
    approved_ids,
    instance_id,
    read_reviewed,
    write_review_template,
)
from io_utils import read_jsonl, write_csv
from mining.miner import Miner
from mining.models import MRRecord
from packaging.patch_split import split_patch
from packaging.task_builder import build_task
from support import FakeGitLabClient

SETTINGS = load_settings()
REPO = RepoConfig("example", "svc", "python", "main")


def _diff(paths):
    lines = []
    for path in paths:
        lines.append(f"diff --git a/{path} b/{path}")
        lines.append(f"--- a/{path}")
        lines.append(f"+++ b/{path}")
        lines.append("@@ -1,1 +1,1 @@")
        for i in range(10):
            lines.append(f"+line{i}")
    return "\n".join(lines) + "\n"


def _run_pipeline(tmp_path):
    client = FakeGitLabClient().add_repo("example", "svc", 101)
    good = ["src/app.py", "tests/test_app.py"]
    bad = ["docs/readme.md"]
    client.add_mr(101, 1, changed_files=good, diff=_diff(good), title="Add feature",
                  labels=["feature"], related_issues=[7], description="x" * 80)
    client.add_mr(101, 2, changed_files=bad, diff=_diff(bad), title="Update docs")

    miner = Miner(client, SETTINGS)
    dump = tmp_path / "data" / "raw" / "mr_dump.jsonl"
    miner.run([REPO], str(dump), str(tmp_path / "data" / "raw" / "ckpt.json"),
              sleep=lambda _: None)

    records = [MRRecord.from_dict(d) for d in read_jsonl(str(dump))]
    candidates = build_candidates(records, SETTINGS)
    (tmp_path / "data").mkdir(exist_ok=True)
    from io_utils import write_jsonl
    write_jsonl(str(tmp_path / "data" / "candidates.jsonl"), candidates)

    reviewed = tmp_path / "data" / "reviewed.csv"
    write_review_template(candidates, str(reviewed))
    rows = read_reviewed(str(reviewed))
    for row in rows:
        row["keep"] = "yes"
    write_csv(str(reviewed), rows, ["instance_id", "keep", "reason", "notes"])
    approved = approved_ids(read_reviewed(str(reviewed)))

    by_id = {instance_id(c): c for c in candidates}
    task_dirs = []
    for iid in approved:
        cand = by_id[iid]
        gold, test = split_patch(cand["diff"], SETTINGS.test_path_keywords)
        task_dirs.append(
            build_task(cand, gold, test, str(tmp_path / "tasks"),
                       language="python", f2p=["x.y"], p2p=[])
        )
    return dump, candidates, approved, task_dirs


def test_pipeline_produces_candidates_and_tasks(tmp_path):
    dump, candidates, approved, task_dirs = _run_pipeline(tmp_path)

    # Mining wrote both MRs.
    assert len(list(read_jsonl(str(dump)))) == 2

    # Filter kept only the MR that passes all hard gates.
    assert len(candidates) == 1
    assert set(candidates[0]["scores"]) == set(SETTINGS.weights)
    assert "total" in candidates[0] and "score_reasons" in candidates[0]

    # Review approved it, and packaging produced a task directory.
    assert approved == [instance_id(candidates[0])]
    assert len(task_dirs) == 1
    task_dir = task_dirs[0]
    assert (task_dir / "instruction.md").exists()
    assert (task_dir / "tests" / "grader.py").exists()
    assert (task_dir / "tests" / "config.json").exists()


def test_patch_split_of_pipeline_diff(tmp_path):
    _, candidates, _, _ = _run_pipeline(tmp_path)
    gold, test = split_patch(candidates[0]["diff"], SETTINGS.test_path_keywords)
    assert "src/app.py" in gold and "tests/test_app.py" not in gold
    assert "tests/test_app.py" in test and "src/app.py" not in test
