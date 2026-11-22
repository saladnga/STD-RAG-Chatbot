"""
Every prompt the app sends to a model lives in this folder as a plain file, so prompt
changes show up as readable diffs in a PR and can be checked against the evals.

Placeholders use {name} and are filled with str.format. A literal brace would have to be
written as {{ or }}.
"""

from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@cache
def load(name: str) -> str:
    """The prompt text of prompts/<name>.md, minus the one newline every file ends with."""
    text = (PROMPTS_DIR / f"{name}.md").read_text()
    return text[:-1] if text.endswith("\n") else text
