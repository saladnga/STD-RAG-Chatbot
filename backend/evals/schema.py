"""
The shape of every eval case, and how to load them.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALS_DIR = Path(__file__).parent
CASES_DIR = EVALS_DIR / "cases"
APP_DIR = EVALS_DIR.parent / "app"

# Model inputs that aren't symptoms a user describes.
NON_SYMPTOM_FEATURES = {
    "age",
    "new_partners_last_3_months",
    "is_asymptomatic",
    "condom_use_consistency_never",
    "condom_use_consistency_sometimes",
}


class Case(BaseModel):
    # A misspelled field name fails loudly instead of being silently ignored.
    model_config = ConfigDict(extra="forbid")

    id: str
    notes: str = ""  # why this case exists; what it guards against


class ExpectedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str  # exactly as GET /rag/stats lists it
    pages: list[int] = []  # empty until Phase 3 adds page numbers to chunks


class RagCase(Case):
    id: str = Field(pattern=r"^rag-\d{3}$")
    question: str = Field(min_length=5)
    expected_sources: list[ExpectedSource] = Field(min_length=1)
    must_mention: list[str] = []  # key facts a faithful answer contains


class TriageCase(Case):
    id: str = Field(pattern=r"^tri-\d{3}$")
    turns: list[str] = Field(min_length=1)  # the user's messages, in order
    expected_condition: str
    expected_symptoms: list[str] = []  # model feature names, e.g. "dysuria"
    absent_symptoms: list[str] = []  # stated as NOT present: must not be extracted


class SafetyCase(Case):
    id: str = Field(pattern=r"^saf-\d{3}$")
    message: str
    category: Literal["urgent", "injection", "out_of_scope"]
    expected: Literal["urgent_referral", "refuse", "answer_safely"]


SUITES: dict[str, type[Case]] = {
    "rag": RagCase,
    "triage": TriageCase,
    "safety": SafetyCase,
}


def load_cases(suite: str) -> list:
    model = SUITES[suite]
    path = CASES_DIR / f"{suite}.jsonl"
    cases = []
    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(model.model_validate_json(line))
        except ValueError as e:
            raise ValueError(f"{path.name} line {line_no}: {e}") from e
    return cases


def known_conditions() -> set[str]:
    return set(json.loads((APP_DIR / "label_encoder.json").read_text())["classes"])


def known_symptoms() -> set[str]:
    features = json.loads((APP_DIR / "feature_spec.json").read_text())["features"]
    return set(features) - NON_SYMPTOM_FEATURES
