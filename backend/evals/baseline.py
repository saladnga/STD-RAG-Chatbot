"""
Record the baseline: the scores every later change is compared against.

    cd backend && python -m evals.baseline      # about 10 minutes, a few cents

Retrieval and triage are deterministic, so they run once. The LLM-judged suites give a
different score each run (answers use temperature 0.7, and the judge varies a little),
so they run RUNS times and the baseline keeps the mean and the range.

Writes evals/baseline.json and evals/BASELINE.md. Creates evals/thresholds.json the first
time only; after that, thresholds are changed by hand.

Threshold rule: a metric fails if it is worse than the worst run seen in the baseline.
That keeps run-to-run noise from failing a check while a real drop still does. Latency and
cost also depend on network and OpenAI load, so they get 20% headroom on top.
"""

import json
import subprocess
from datetime import datetime, timezone
from statistics import mean

from evals import run_llm, run_retrieval, run_triage
from evals.gate import THRESHOLDS_PATH, initial_thresholds
from evals.schema import EVALS_DIR

RUNS = 3
BASELINE_PATH = EVALS_DIR / "baseline.json"
REPORT_PATH = EVALS_DIR / "BASELINE.md"

# Where the roadmap says each key metric should end up (shown in the report only).
TARGETS = {
    "retrieval": {"hit@5": "≥ 0.90 (Phase 3)", "prod_hit": "≥ 0.80 (Phase 3)"},
    "triage": {"extraction_f1": "≥ 0.90 (Phase 4)", "accuracy@1": "≥ 0.75 (Phases 4–5)"},
    "rag-llm": {"faithfulness": "≥ 0.90 (Phase 3)", "first_token_p50_s": "< 1.5 s (Phase 3)"},
    "safety-llm": {"urgent_referral_rate": "1.00 (Phase 4)", "unsafe_count": "0 (Phase 4)"},
}


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def spread(summaries: list[dict]) -> dict:
    return {
        metric: {
            "mean": mean(s[metric] for s in summaries),
            "min": min(s[metric] for s in summaries),
            "max": max(s[metric] for s in summaries),
        }
        for metric in summaries[0]
    }


def report(baseline: dict) -> str:
    lines = [
        "# Eval baseline",
        "",
        f"Recorded {baseline['recorded_at']} at commit `{baseline['git_commit']}`. "
        f"Chat model `{baseline['chat_model']}`, judge `{baseline['judge_model']}`, "
        f"LLM suites averaged over {baseline['runs']} runs.",
        "",
        "Regenerate with `cd backend && python -m evals.baseline`. Gate a change with `python -m evals.gate <suite>`.",
    ]
    for suite, metrics in baseline["suites"].items():
        lines += ["", f"## {suite}", "", "| Metric | Baseline | Range over runs | Target |", "|---|---|---|---|"]
        for metric, value in metrics.items():
            target = TARGETS.get(suite, {}).get(metric, "")
            if isinstance(value, dict):
                lines.append(f"| {metric} | {value['mean']:.3f} | {value['min']:.3f} – {value['max']:.3f} | {target} |")
            else:
                lines.append(f"| {metric} | {value:.3f} | deterministic | {target} |")
    return "\n".join(lines) + "\n"


def main():
    suites = {
        "retrieval": run_retrieval.main()["summary"],
        "triage": run_triage.main()["summary"],
    }
    client = run_llm.sync_client(run_llm.settings.openai_api_key)
    for suite in ["rag", "safety"]:
        runs = [run_llm.run_suite(client, suite)["summary"] for _ in range(RUNS)]
        suites[f"{suite}-llm"] = spread(runs)

    baseline = {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "chat_model": run_llm.DEFAULT_CHAT_MODEL,
        "judge_model": run_llm.JUDGE_MODEL,
        "runs": RUNS,
        "suites": suites,
    }
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n")
    REPORT_PATH.write_text(report(baseline))
    if not THRESHOLDS_PATH.exists():
        THRESHOLDS_PATH.write_text(json.dumps(initial_thresholds(suites), indent=2) + "\n")
        print(f"Created {THRESHOLDS_PATH.name} from the baseline's worst runs.")
    print(f"Wrote {BASELINE_PATH.name} and {REPORT_PATH.name}.")


if __name__ == "__main__":
    main()
