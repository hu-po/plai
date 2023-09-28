import logging
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Union


@dataclass
class Action:
    name: str  # name of action
    func: Callable  # function that will be called
    desc: str  # description of action for llm use
    args: List[Union[str, float, int]] = None  # arguments for the function

DEFAULT_ACTIONS: Dict[str, Action] = {
    "move": Action(
        "move",
        lambda *args: print(f"move({args})"),
        "move the robot arm to a position",
    ),
    "sleep": Action(
        "sleep",
        lambda *args: print(f"sleep({args})"),
        "wait for a period of time",
    ),
    "take_image": Action(
        "take_image",
        lambda *args: print(f"take_image({args})"),
        "take an image",
    ), 
}

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

class Plan:
    def __init__(
        self,
        raw_str: str,
        actions: Dict[str, Action] = DEFAULT_ACTIONS,
        action_pattern: re.Pattern = re.compile(r"(\w+)\(([^)]*)\)"),
        plan_delimiter: str = ";",
        args_delimiter: str = ",",
    ):
        self.actions = actions
        self.action_pattern = action_pattern
        self.plan_delimiter = plan_delimiter
        self.args_delimiter = args_delimiter
        for raw_action in raw_str.split(self.plan_delimiter):
            raw_action = raw_action.strip()  # remove extra spaces
            match = self.action_pattern.match(raw_action)

            if not match:
                logging.warning(f"Invalid action format: {raw_action}")
                continue

            action_name, action_args_str = match.groups()

            # Convert arguments to their respective types (int, float, or str)
            action_args = self._parse_args(action_args_str)

            if action_name not in self.actions:
                logging.warning(f"Unknown action: {action_name}")
                continue

            # Store the action with the parsed arguments
            self.actions[action_name] = Action(
                action_name,
                self.actions[action_name].func,
                self.actions[action_name].desc,
                action_args,
            )

    def run(self):
        for action in self.actions.values():
            action.func(*action.args)

    def _parse_args(self, args_str: str) -> List[Union[str, float, int]]:
        raw_args = args_str.split(self.args_delimiter)
        parsed_args = []
        for arg in raw_args:
            arg = arg.strip()
            if arg:
                if arg.replace(".", "", 1).isdigit():
                    if "." in arg:
                        parsed_args.append(float(arg))
                    else:
                        parsed_args.append(int(arg))
                else:
                    parsed_args.append(arg)
        return parsed_args

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from gpt import gpt_text, set_openai_key
    set_openai_key()

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