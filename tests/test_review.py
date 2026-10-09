from filter.review import (
    REVIEW_FIELDS,
    approved_ids,
    instance_id,
    read_reviewed,
    seed_review_rows,
    write_review_template,
)
from support import make_mr


def test_instance_id_and_seed_rows():
    mr = make_mr(iid=12, project_id=101)
    assert instance_id(mr.to_dict()) == "101__12"
    rows = seed_review_rows([mr.to_dict()])
    assert rows == [{"instance_id": "101__12", "keep": "", "reason": "", "notes": ""}]
    assert list(rows[0]) == REVIEW_FIELDS


def test_write_and_read_reviewed_roundtrip(tmp_path):
    mr = make_mr(iid=12)
    path = tmp_path / "reviewed.csv"
    write_review_template([mr.to_dict()], str(path))
    rows = read_reviewed(str(path))
    assert len(rows) == 1
    assert rows[0]["instance_id"] == "101__12"


def test_approved_ids_filters_keep(tmp_path):
    rows = [
        {"instance_id": "101__1", "keep": "yes", "reason": "", "notes": ""},
        {"instance_id": "101__2", "keep": "no", "reason": "", "notes": ""},
        {"instance_id": "101__3", "keep": "TRUE", "reason": "", "notes": ""},
    ]
    assert approved_ids(rows) == ["101__1", "101__3"]
