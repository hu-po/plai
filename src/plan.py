import logging
from typing import Callable, Dict, List, Union

from .gpt import gpt_text, set_openai_key

log = logging.getLogger(__name__)

PLAN_DELIMITER: str = ";"
log.debug(f"PLAN_DELIMITER: {PLAN_DELIMITER}")

PLAN_DATASET: Dict[str, str] = {
    "halfway then back with one second sleeps" : PLAN_DELIMITER.join([
        "move(0, 0, 0)",
        "sleep(1.0)",
        "move(180, 180, 180)",
        "sleep(1.0)",
        "move(0, 0, 0)",
    ]),
    "wait at the end" : PLAN_DELIMITER.join([
        "move(360, 360, 360)",
        "sleep(5.0)",
    ]),
    "wiggle" : PLAN_DELIMITER.join([
        "move(90, 90, 90)",
        "sleep(0.5)",
        "move(45, 45, 45)",
        "sleep(0.5)",
        "move(90, 90, 90)",
        "sleep(0.5)",
        "move(135, 135, 135)",
    ]),
}

def plan_from_description(
    description: str,
) -> str:
    _messages = [
        {
            "role": "system",
            "content": " ".join(
                [
                    "Output a robot motion plan based on a string description.",
                    "You output motion plans for a 3DoF robot arm.",
                    f"Motion plans are sequences of python function calls delimited by {PLAN_DELIMITER}.",
                ]
            ),
        },
    ]
    for example_description, example_plan in PLAN_DATASET.items():
        _messages.append({
            "role": "user",
            "content": example_description,
        })
        _messages.append({
            "role": "assistant",
            "content": example_plan,
        })
    _messages.append({
        "role": "user",
        "content": description,
    })
    return gpt_text(messages=_messages)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    set_openai_key()
    test_plan = plan_from_description("wait at the end for a second then come back to halfway")