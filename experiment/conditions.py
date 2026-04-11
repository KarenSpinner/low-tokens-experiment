"""Pressure conditions for the experiment."""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Condition:
    id: str
    max_tokens: int
    system: Optional[str] = None
    pad_tokens: int = 0          # approx tokens of junk context to prepend
    burndown_turns: int = 0      # number of unrelated preamble turns


CONDITIONS: List[Condition] = [
    Condition(id="control", max_tokens=8000),
    Condition(id="cap_soft", max_tokens=800),
    Condition(id="cap_hard", max_tokens=250),
    Condition(id="padded_150k", max_tokens=8000, pad_tokens=150_000),
    Condition(id="burndown_long", max_tokens=8000, burndown_turns=25),
    Condition(id="burndown_coding", max_tokens=8000, burndown_turns=15),
    Condition(
        id="framed_explicit",
        max_tokens=8000,
        system="You have approximately 500 tokens of budget remaining for this response. Be efficient.",
    ),
]


# ~4 chars/token. A paragraph of filler to replicate up to pad_tokens.
_FILLER_PARA = (
    "The quick brown fox jumps over the lazy dog. " * 20 + "\n"
)


def build_padding(target_tokens: int) -> str:
    if target_tokens <= 0:
        return ""
    # ~4 chars/token heuristic
    target_chars = target_tokens * 4
    reps = max(1, target_chars // len(_FILLER_PARA))
    return (
        "<!-- begin irrelevant prior context for padding only -->\n"
        + _FILLER_PARA * reps
        + "<!-- end irrelevant prior context -->\n"
    )


BURNDOWN_PREAMBLE_TASKS = [
    "What is 17 * 23?",
    "Name three primary colors.",
    "Write a haiku about coffee.",
    "Translate 'hello' into Spanish.",
    "What year did WWII end?",
    "Give me a synonym for 'fast'.",
    "What's the capital of Australia?",
    "Convert 100F to Celsius.",
    # --- heavier coding/reasoning turns ---
    "Write a Python function that reverses a linked list iteratively.",
    "Explain the difference between a process and a thread in 3 sentences.",
    "What's the Big-O of inserting into a Python list at index 0?",
    "Write a SQL query to find the second-highest salary from an Employees table.",
    "Give me a regex that matches US phone numbers in format (xxx) xxx-xxxx.",
    "Sketch pseudocode for binary search on a sorted array.",
    "What does the GIL do in CPython?",
    "Write a bash one-liner to count lines in all .py files under the current dir.",
    "Explain recursion with the classic factorial example.",
    "How would you detect a cycle in a directed graph?",
    "What's the difference between HTTP PUT and PATCH?",
    "Show me a Python decorator that times a function.",
    "What does `git rebase -i` do?",
    "Give me a Dockerfile for a minimal Python 3.12 service.",
    "What's the time complexity of quicksort in the worst case?",
    "Write a Python generator that yields Fibonacci numbers.",
    "Explain CAP theorem in two sentences.",
]


def build_messages(condition: Condition, user_prompt: str) -> List[Dict[str, Any]]:
    """Build the messages array for a given condition + target prompt."""
    messages: List[Dict[str, Any]] = []

    if condition.burndown_turns > 0:
        # Simulate a burned-down session with realistic assistant replies so
        # the model actually sees a long prior context, not placeholder text.
        _FAKE_REPLY = (
            "Here's a reasonable answer. " * 30
            + "This preceding turn is part of a longer session; the real task "
              "follows later. " * 10
        )
        for i in range(min(condition.burndown_turns, len(BURNDOWN_PREAMBLE_TASKS))):
            messages.append({"role": "user", "content": BURNDOWN_PREAMBLE_TASKS[i]})
            messages.append({"role": "assistant", "content": _FAKE_REPLY})

    content = user_prompt
    if condition.pad_tokens > 0:
        content = build_padding(condition.pad_tokens) + "\n\n" + user_prompt

    messages.append({"role": "user", "content": content})
    return messages
