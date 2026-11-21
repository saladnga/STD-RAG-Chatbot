from services.chat_analysis import build_system_prompt


def test_prompt_without_profile_does_not_crash():
    # Before the fix, this raised UnboundLocalError.
    prompt = build_system_prompt(None)
    assert "ANALYZE:" in prompt


def test_prompt_with_profile_includes_name_and_rules():
    prompt = build_system_prompt({"first_name": "Sam"})
    assert "Sam" in prompt
    assert "ANALYZE:" in prompt
