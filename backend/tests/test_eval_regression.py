"""
The eval regression gate, run on every PR by CI.

Only the triage suite runs here: it is offline and deterministic (regex extraction plus
the local model), so the same code always gives the same score. Retrieval needs the live
database and the LLM suites cost money and vary between runs; those run on demand in
.github/workflows/evals.yml.
"""

from evals import run_triage
from evals.gate import check


def test_triage_scores_have_not_regressed():
    summary = run_triage.main()["summary"]
    assert check("triage", summary) == []
