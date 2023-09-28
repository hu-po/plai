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


class Plan:
    def __init__(
        self,
        raw_str: str,
        actions: Dict[str, Action],
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