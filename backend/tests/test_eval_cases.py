import pytest

from evals.schema import SUITES, known_conditions, known_symptoms, load_cases


@pytest.mark.parametrize("suite", SUITES)
def test_cases_are_valid_and_ids_unique(suite):
    cases = load_cases(suite)  # raises with the file and line number on a bad case
    assert cases, f"{suite}.jsonl has no cases"
    ids = [case.id for case in cases]
    assert len(ids) == len(set(ids)), f"duplicate ids in {suite}.jsonl"


def test_triage_cases_use_labels_the_model_knows():
    conditions, symptoms = known_conditions(), known_symptoms()
    for case in load_cases("triage"):
        assert case.expected_condition in conditions, f"{case.id}: unknown condition"
        unknown = set(case.expected_symptoms + case.absent_symptoms) - symptoms
        assert not unknown, f"{case.id}: unknown symptoms {unknown}"
