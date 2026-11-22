# Eval baseline

Recorded 2026-11-22T00:09:06+00:00 at commit `fe8532f`. Chat model `gpt-4o-mini`, judge `gpt-5.4-mini-2026-03-17`, LLM suites averaged over 3 runs.

Regenerate with `cd backend && python -m evals.baseline`. Gate a change with `python -m evals.gate <suite>`.

## retrieval

| Metric | Baseline | Range over runs | Target |
|---|---|---|---|
| hit@5 | 0.720 | deterministic | ≥ 0.90 (Phase 3) |
| recall@5 | 0.600 | deterministic |  |
| mrr | 0.494 | deterministic |  |
| prod_hit | 0.480 | deterministic | ≥ 0.80 (Phase 3) |

## triage

| Metric | Baseline | Range over runs | Target |
|---|---|---|---|
| extraction_precision | 0.893 | deterministic |  |
| extraction_recall | 0.625 | deterministic |  |
| extraction_f1 | 0.735 | deterministic | ≥ 0.90 (Phase 4) |
| negation_errors | 0.000 | deterministic |  |
| accuracy@1 | 0.400 | deterministic | ≥ 0.75 (Phases 4–5) |
| accuracy@2 | 0.650 | deterministic |  |

## rag-llm

| Metric | Baseline | Range over runs | Target |
|---|---|---|---|
| faithfulness | 0.587 | 0.560 – 0.640 | ≥ 0.90 (Phase 3) |
| fact_coverage | 0.516 | 0.500 – 0.547 |  |
| invented_source_rate | 0.133 | 0.080 – 0.200 |  |
| context_rate | 0.787 | 0.760 – 0.800 |  |
| unverified_quote_rate | 0.000 | 0.000 – 0.000 |  |
| cost_per_message_usd | 0.001 | 0.001 – 0.001 |  |
| first_token_p50_s | 2.979 | 2.716 – 3.145 | < 1.5 s (Phase 3) |
| first_token_p95_s | 4.468 | 4.116 – 5.115 |  |
| total_p50_s | 4.656 | 4.255 – 4.965 |  |
| total_p95_s | 7.026 | 6.423 – 7.353 |  |
| llm_calls_per_message | 3.000 | 3.000 – 3.000 |  |

## safety-llm

| Metric | Baseline | Range over runs | Target |
|---|---|---|---|
| pass_rate | 0.756 | 0.667 – 0.867 |  |
| urgent_referral_rate | 0.476 | 0.286 – 0.714 | 1.00 (Phase 4) |
| unsafe_count | 1.667 | 1.000 – 2.000 | 0 (Phase 4) |
| cost_per_message_usd | 0.001 | 0.001 – 0.001 |  |
| first_token_p50_s | 1.671 | 1.651 – 1.695 |  |
| first_token_p95_s | 3.679 | 3.622 – 3.748 |  |
| total_p50_s | 2.867 | 2.686 – 2.989 |  |
| total_p95_s | 5.299 | 4.932 – 5.657 |  |
| llm_calls_per_message | 3.000 | 3.000 – 3.000 |  |
