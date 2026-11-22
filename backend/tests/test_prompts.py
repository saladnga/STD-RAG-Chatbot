from pathlib import Path

from prompts import PROMPTS_DIR, load

BACKEND = Path(__file__).parent.parent


def test_every_prompt_file_loads():
    names = [path.stem for path in PROMPTS_DIR.glob("*.md")]
    assert names, "no prompt files found"
    for name in names:
        assert load(name).strip(), f"prompts/{name}.md is empty"


def test_prompts_are_shipped_in_the_docker_image():
    # .dockerignore drops *.md; the prompts must be re-included or production can't start.
    assert "!app/prompts/*.md" in (BACKEND / ".dockerignore").read_text().splitlines()
