import logging
import time
import re
import rerun
from typing import Callable, Dict, List, Union

from .servo import Servos
from .camera import Camera
from .plan import PLAN_DELIMITER, PLAN_DATASET

log = logging.getLogger(__name__)


class Robot:

    def __init__(self):
        self.actions: Dict[str, Callable] = {}
        self.servos = Servos()
        self.camera = Camera()
        self.actions["move"] = self.servos.move
        self.actions["move_to"] = self.servos.move_to
        self.actions["get_image"] = self.camera.get_image
        self.actions["sleep"] = time.sleep

    def observe():
        rerun.log_image

    def action():
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    bot = Robot()
    for plan_description, plan in PLAN_DATASET.items():
        log.debug(f"Running plan: {plan_description}")
        bot.run_plan(plan)
