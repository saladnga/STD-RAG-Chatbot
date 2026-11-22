import pytest

from evals.metrics import first_relevant_rank, hit_at_k, precision_recall_f1, recall_at_k, reciprocal_rank

RETRIEVED = ["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf", "f.pdf"]


def test_first_relevant_rank():
    assert first_relevant_rank(RETRIEVED, {"c.pdf"}) == 3
    assert first_relevant_rank(RETRIEVED, {"z.pdf"}) is None


def test_hit_at_k_respects_the_cutoff():
    assert hit_at_k(RETRIEVED, {"e.pdf"}, k=5)
    assert not hit_at_k(RETRIEVED, {"f.pdf"}, k=5)  # rank 6 is outside the top 5


def test_recall_counts_each_relevant_source_once():
    assert recall_at_k(RETRIEVED, {"a.pdf", "z.pdf"}, k=5) == 0.5
    assert recall_at_k(["a.pdf", "a.pdf"], {"a.pdf"}, k=5) == 1.0  # duplicate chunks of one file


@pytest.mark.parametrize("relevant, expected", [({"a.pdf"}, 1.0), ({"b.pdf"}, 0.5), ({"z.pdf"}, 0.0)])
def test_reciprocal_rank(relevant, expected):
    assert reciprocal_rank(RETRIEVED, relevant) == expected


def test_precision_recall_f1():
    assert precision_recall_f1(tp=8, fp=2, fn=2) == pytest.approx((0.8, 0.8, 0.8))
    assert precision_recall_f1(tp=0, fp=0, fn=3) == (1.0, 0.0, 0.0)  # found nothing it should have
    assert precision_recall_f1(tp=0, fp=0, fn=0) == (1.0, 1.0, 1.0)  # nothing to find, nothing found


def test_judge_quotes_are_checked_against_the_real_text():
    from evals.judge import quote_found

    context = "Chlamydia is treated with azithromycin or doxycycline."
    assert quote_found("treated with  Azithromycin", context)  # spacing and case ignored
    assert not quote_found("treated with penicillin", context)  # a made-up quote fails
    assert not quote_found("", context)  # no evidence is not evidence


def test_percentile():
    from evals.metrics import percentile

    latencies = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(latencies, 50) == 3.0
    assert percentile(latencies, 100) == 5.0
    assert percentile(latencies, 95) == pytest.approx(4.8)
    assert percentile([2.5], 95) == 2.5


def test_baseline_always_passes_its_own_thresholds():
    import json

    from evals.gate import initial_thresholds
    from evals.schema import EVALS_DIR

    suites = json.loads((EVALS_DIR / "baseline.json").read_text())["suites"]
    for suite, limits in initial_thresholds(suites).items():
        for metric, limit in limits.items():
            value = suites[suite][metric]
            worst = (value["max"] if "max" in limit else value["min"]) if isinstance(value, dict) else value
            assert worst >= limit.get("min", float("-inf")), f"{suite}.{metric}"
            assert worst <= limit.get("max", float("inf")), f"{suite}.{metric}"
