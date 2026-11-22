"""
Human check of the LLM judge (S17). The judge's scores are only trusted if a person,
reading the same answers, mostly agrees with it.

    cd backend && python -m evals.review make    # writes evals/review/judge-review.md
    # open it, and after each "Your verdict:" write agree or disagree (+ a short reason)
    cd backend && python -m evals.review score   # agreement rate + every disagreement

The filled-in review is committed: it is the evidence that the judge was validated.
"""

import json
import re
import sys

from evals.schema import EVALS_DIR

RESULTS_DIR = EVALS_DIR / "results"
REVIEW_PATH = EVALS_DIR / "review" / "judge-review.md"

# A deliberate mix: grades that looked too strict, clear failures, passes with low fact
# coverage, and safety calls of each kind. Chosen from the first judge run (S16), and kept
# fixed so each judge version is checked on the same cases.
# judge-review-v1.md: first judge, 6/10 agreement (it mixed key facts up with claims).
REVIEW_IDS = [
    "rag-005", "rag-020",  # judged unfaithful, possibly too strict
    "rag-009", "rag-017", "rag-023",  # judged unfaithful
    "rag-004", "rag-012",  # judged faithful but missing key facts
    "saf-008",  # judged unsafe
    "saf-011",  # injection, judged refused
    "saf-015",  # out of scope, judged refused
]

VERDICT_LINE = "**Your verdict:**"


def make():
    rag = {c["id"]: c for c in json.loads((RESULTS_DIR / "rag-llm-latest.json").read_text())["cases"]}
    safety = {c["id"]: c for c in json.loads((RESULTS_DIR / "safety-llm-latest.json").read_text())["cases"]}

    parts = [
        "# Judge review\n",
        "For each case, read the reply and decide whether the judge's verdict is right.",
        f"After {VERDICT_LINE} write `agree` or `disagree`, then a short reason if you disagree.\n",
    ]
    for case_id in REVIEW_IDS:
        if case_id in rag:
            c = rag[case_id]
            parts += [
                f"## {case_id}\n",
                f"**Question:** {c['question']}\n",
                "**Document context the bot was given:**\n",
                "\n".join(f"> {line}" for line in (c["context"] or "(none)").strip().splitlines()) + "\n",
                "**Bot reply:**\n",
                "\n".join(f"> {line}" for line in c["reply"].strip().splitlines()) + "\n",
                f"**Judge:** faithful = **{'yes' if c['faithful'] else 'no'}**",
                f"- unsupported claims: {c['unsupported_claims'] or 'none'}",
                f"- missing key facts: {c['missing_facts'] or 'none'}\n",
                f"{VERDICT_LINE} \n",
            ]
        else:
            c = safety[case_id]
            parts += [
                f"## {case_id} ({c['category']}, should be: {c['expected']})\n",
                f"**Message:** {c['message']}\n",
                "**Bot reply:**\n",
                "\n".join(f"> {line}" for line in c["reply"].strip().splitlines()) + "\n",
                f"**Judge:** {c['behaviour']} ({'pass' if c['passed'] else 'FAIL'}): {c['reason']}\n",
                f"{VERDICT_LINE} \n",
            ]
    REVIEW_PATH.parent.mkdir(exist_ok=True)
    REVIEW_PATH.write_text("\n".join(parts))
    print(f"Wrote {REVIEW_PATH.relative_to(EVALS_DIR.parent)} with {len(REVIEW_IDS)} cases.")


def score():
    sections = re.split(r"^## ", REVIEW_PATH.read_text(), flags=re.M)[1:]
    answered, missing = [], 0
    for section in sections:
        case_id = section.split()[0]
        match = re.search(r"^\*\*Your verdict:\*\*[ \t]*(.*)$", section, flags=re.M)
        verdict = match.group(1).strip() if match else ""
        if verdict:
            answered.append((case_id, verdict))
        else:
            missing += 1
    if missing:
        print(f"{missing} case(s) still have no verdict.")
    agree = [case_id for case_id, v in answered if v.lower().startswith("agree")]
    disagree = [(case_id, v) for case_id, v in answered if v.lower().startswith("disagree")]
    if answered:
        print(f"Agreement: {len(agree)}/{len(answered)} = {len(agree) / len(answered):.0%}")
    for case_id, v in disagree:
        print(f"  {case_id}: {v}")


if __name__ == "__main__":
    {"make": make, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "make"]()
