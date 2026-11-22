"""
Score symptom extraction and condition prediction against evals/cases/triage.jsonl.

    cd backend && python -m evals.run_triage

Runs fully offline: regex extraction plus the local XGBoost model. No API calls, no
database, same result every run, so it can gate every PR later (S20).

Mirrors production: chat joins every user message into one text before extraction.
"""

import json
import sys
from datetime import datetime, timezone
from statistics import mean

import pandas as pd

from evals.metrics import precision_recall_f1
from evals.schema import APP_DIR, EVALS_DIR, known_symptoms, load_cases

sys.path.insert(0, str(APP_DIR))
from model import load_model, process_text_to_feature  # noqa: E402

RESULTS_PATH = EVALS_DIR / "results" / "triage-latest.json"


def main():
    model, label_encoder, feature_columns = load_model()
    if model is None or label_encoder is None:
        raise SystemExit("app/model.joblib could not be loaded; train it first: cd backend/app && python model.py")
    symptoms = known_symptoms()

    rows = []
    totals = {"tp": 0, "fp": 0, "fn": 0}
    for case in load_cases("triage"):
        text = " ".join(case.turns)
        features = process_text_to_feature(text, feature_columns)
        extracted = {name for name in symptoms if features.get(name) == 1}
        expected = set(case.expected_symptoms)

        tp, fp, fn = len(extracted & expected), len(extracted - expected), len(expected - extracted)
        totals["tp"] += tp
        totals["fp"] += fp
        totals["fn"] += fn

        probabilities = model.predict_proba(pd.DataFrame([features], columns=pd.Index(feature_columns)))[0]
        ranked = [label_encoder.classes_[i] for i in probabilities.argsort()[::-1]]

        rows.append(
            {
                "id": case.id,
                "expected": case.expected_condition,
                "predicted": ranked[0],
                "confidence": round(float(probabilities.max()), 3),
                "correct@1": ranked[0] == case.expected_condition,
                "correct@2": case.expected_condition in ranked[:2],
                "missed": sorted(expected - extracted),
                "extra": sorted(extracted - expected),
                "negation_errors": sorted(extracted & set(case.absent_symptoms)),
            }
        )

    precision, recall, f1 = precision_recall_f1(**totals)
    summary = {
        "extraction_precision": precision,
        "extraction_recall": recall,
        "extraction_f1": f1,
        "negation_errors": sum(len(r["negation_errors"]) for r in rows),
        "accuracy@1": mean(r["correct@1"] for r in rows),
        "accuracy@2": mean(r["correct@2"] for r in rows),
    }

    print(f"{'case':<8} {'expected':<10} {'predicted':<10} {'conf':>5}  missed / extra")
    for r in rows:
        mark = "" if r["correct@1"] else "  <-- wrong"
        gaps = ", ".join([f"-{m}" for m in r["missed"]] + [f"+{e}" for e in r["extra"]])
        print(f"{r['id']:<8} {r['expected']:<10} {r['predicted']:<10} {r['confidence']:>5}  {gaps}{mark}")
    print(f"\n{len(rows)} cases")
    for name, value in summary.items():
        print(f"  {name:<21} {value:.3f}" if isinstance(value, float) else f"  {name:<21} {value}")

    result = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "summary": summary, "cases": rows}
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    main()
