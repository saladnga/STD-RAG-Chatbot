"""
The regression gate: do the latest scores still meet evals/thresholds.json?

    cd backend && python -m evals.gate triage           # one suite
    cd backend && python -m evals.gate rag-llm safety-llm

Exits with code 1 if any metric is past its limit, so CI and scripts can stop on it.
Thresholds are edited by hand, on purpose: raising one is a decision, not a side effect.
"""

import json
import math
import sys

from evals.schema import EVALS_DIR

THRESHOLDS_PATH = EVALS_DIR / "thresholds.json"
RESULTS_DIR = EVALS_DIR / "results"

# Metrics where a lower number is better; everything else, higher is better.
LOWER_IS_BETTER = {
    "negation_errors", "invented_source_rate", "unverified_quote_rate", "unsafe_count",
    "cost_per_message_usd", "first_token_p50_s", "first_token_p95_s", "total_p50_s", "total_p95_s",
    "llm_calls_per_message",
}
# Recorded for context, not gated (they describe the setup, not quality).
NOT_GATED = {"context_rate", "unverified_quote_rate", "llm_calls_per_message"}


def initial_thresholds(suites: dict) -> dict:
    thresholds = {}
    for suite, metrics in suites.items():
        thresholds[suite] = {}
        for metric, value in metrics.items():
            if metric in NOT_GATED:
                continue
            worst = (value["max"] if metric in LOWER_IS_BETTER else value["min"]) if isinstance(value, dict) else value
            if metric.endswith("_s") or metric.endswith("_usd"):
                worst *= 1.2
            # Round outward (minimums down, maximums up) so the baseline always passes its own gate.
            if metric in LOWER_IS_BETTER:
                thresholds[suite][metric] = {"max": math.ceil(worst * 1e6) / 1e6}
            else:
                thresholds[suite][metric] = {"min": math.floor(worst * 1e3) / 1e3}
    return thresholds


def check(suite: str, summary: dict) -> list[str]:
    """Every threshold the summary breaks, as readable messages. Empty means it passes."""
    failures = []
    for metric, limit in json.loads(THRESHOLDS_PATH.read_text())[suite].items():
        value = summary[metric]
        if "min" in limit and value < limit["min"]:
            failures.append(f"{suite}.{metric} = {value:.3f}, below the minimum {limit['min']}")
        if "max" in limit and value > limit["max"]:
            failures.append(f"{suite}.{metric} = {value:.3f}, above the maximum {limit['max']}")
    return failures


def main():
    failures = []
    for suite in sys.argv[1:]:
        summary = json.loads((RESULTS_DIR / f"{suite}-latest.json").read_text())["summary"]
        suite_failures = check(suite, summary)
        print(f"{suite}: {'pass' if not suite_failures else 'FAIL'}")
        failures += suite_failures
    for failure in failures:
        print(f"  {failure}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
