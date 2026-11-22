"""
What each chatbot message costs and how long it takes, measured from real API responses.

Prices are USD per 1 million tokens, copied from https://openai.com/api/pricing. They are not fetched automatically: when OpenAI changes them, update this table and the date.
"""

import time

PRICES_CHECKED = "2026-11-22"
PRICES_PER_1M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
}


def call_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES_PER_1M[model]
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


class Meter:
    """
    Records every OpenAI call made while answering one message: model, tokens, seconds.
    Wraps a client method in place, so the app code being measured is not changed.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def wrap(self, owner, method_name: str):
        original = getattr(owner, method_name)

        def measured(*args, **kwargs):
            started = time.perf_counter()
            response = original(*args, **kwargs)
            usage = response.usage
            self.record(
                kwargs["model"],
                usage.prompt_tokens,
                getattr(usage, "completion_tokens", 0) or 0,
                time.perf_counter() - started,
            )
            return response

        setattr(owner, method_name, measured)

    def record(self, model: str, input_tokens: int, output_tokens: int, seconds: float):
        self.calls.append(
            {"model": model, "input_tokens": input_tokens, "output_tokens": output_tokens, "seconds": round(seconds, 3)}
        )

    def cost(self) -> float:
        return sum(call_cost(c["model"], c["input_tokens"], c["output_tokens"]) for c in self.calls)
