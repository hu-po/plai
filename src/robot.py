import logging
import time
import re
from typing import Callable, Dict, List, Union

from servo import Servos
from plan import PLAN_DELIMITER, PLAN_DATASET

log = logging.getLogger(__name__)


class Robot:

    def __init__(self):
        self.actions: Dict[str, Callable] = {}
        self.servos = Servos()
        self.actions["move"] = self.servos.move
        self.actions["sleep"] = time.sleep

    def run_plan(self,
        raw_plan: str,
        plan_delimiter: str = PLAN_DELIMITER,
    ):
        # Use regex to extract the action name and its arguments
        action_pattern = re.compile(r'(\w+)\(([^)]*)\)')

        for raw_action in raw_plan.split(plan_delimiter):
            raw_action = raw_action.strip()  # remove extra spaces
            match = action_pattern.match(raw_action)

            if not match:
                log.warning(f"Invalid action format: {raw_action}")
                continue

            action_name, action_args_str = match.groups()

            # Convert arguments to their respective types (int, float, or str)
            action_args = self._parse_args(action_args_str)

            if action_name not in self.actions:
                log.warning(f"Unknown action: {action_name}")
                continue

            # Call the action with the parsed arguments
            self.actions[action_name](*action_args)

    def _parse_args(self, args_str: str) -> List[Union[str, float, int]]:
        """
        Parse the arguments string and return a list of converted arguments.
        """
        raw_args = args_str.split(',')
        parsed_args = []
        for arg in raw_args:
            arg = arg.strip()
            if arg.replace('.', '', 1).isdigit():
                if '.' in arg:
                    parsed_args.append(float(arg))
                else:
                    parsed_args.append(int(arg))
            else:
                parsed_args.append(arg)
        return parsed_args

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    bot = Robot()
    for plan_description, plan in PLAN_DATASET.items():
        log.debug(f"Running plan: {plan_description}")
        bot.run_plan(plan)
