"""Filter pipeline: gate, score, rank and emit the candidate list."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import Settings
from filter.hard_gates import evaluate_gates
from filter.scoring import score_mr
from mining.models import MRRecord


def _dedup_key(candidate: Dict[str, Any]):
    issues = candidate.get("related_issues") or []
    if issues:
        return ("issue", issues[0])
    return ("mr", candidate["project_id"], candidate["mr_iid"])


def _preference(candidate: Dict[str, Any]):
    # Prefer merged, then higher score, then more recent.
    return (
        1 if candidate.get("merged_at") else 0,
        candidate.get("total", 0.0),
        candidate.get("merged_at", ""),
    )


def dedup_candidates(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Collapse candidates that share their primary issue, keeping the best.

    Candidates are all merged (mining only fetches merged MRs); among several
    merged MRs for the same issue the highest-scoring, most recent one wins.
    MRs without a linked issue are never merged together.
    """
    best: Dict[Any, Dict[str, Any]] = {}
    for candidate in candidates:
        key = _dedup_key(candidate)
        if key not in best or _preference(candidate) > _preference(best[key]):
            best[key] = candidate
    return list(best.values())


def build_candidates(
    records: List[MRRecord],
    settings: Settings,
    top_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Gate + score *records*, then dedup and return the top-N candidates."""
    limit = settings.top_n if top_n is None else top_n
    candidates: List[Dict[str, Any]] = []
    for mr in records:
        if not evaluate_gates(mr, settings).passed:
            continue
        score = score_mr(mr, settings)
        candidate = mr.to_dict()
        candidate["scores"] = score.scores
        candidate["total"] = score.total
        candidate["score_reasons"] = score.reasons
        candidates.append(candidate)
    candidates = dedup_candidates(candidates)
    candidates.sort(key=lambda c: c["total"], reverse=True)
    return candidates[:limit]
