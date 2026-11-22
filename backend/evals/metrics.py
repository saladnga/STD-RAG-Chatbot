"""
Retrieval metrics. Pure functions with no network calls, unit-tested in tests/test_eval_metrics.py so the scoring itself can be trusted.

`retrieved` is the ranked list of source files returned by search (best first);
`relevant` is the set of files that contain the answer.
"""


def first_relevant_rank(retrieved: list[str], relevant: set[str]) -> int | None:
    """1-based position of the first relevant result, or None if none was retrieved."""
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return rank
    return None


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> bool:
    """Did at least one relevant source appear in the top k?"""
    rank = first_relevant_rank(retrieved, relevant)
    return rank is not None and rank <= k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Share of the relevant sources that appear in the top k (0.0 to 1.0)."""
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """1 / rank of the first relevant result: 1.0 if first, 0.5 if second, 0.0 if missing."""
    rank = first_relevant_rank(retrieved, relevant)
    return 1.0 / rank if rank else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """
    From counts of true positives, false positives and false negatives.
    Precision: of what was extracted, how much was right. Recall: of what should
    have been extracted, how much was found. F1 balances the two.
    """
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def percentile(values: list[float], p: int) -> float:
    """The p-th percentile (e.g. 50 = median, 95 = the slow tail), interpolated between points."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
