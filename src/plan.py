import logging
from typing import Callable, Dict, List, Union

from .gpt import gpt_text, set_openai_key

log = logging.getLogger(__name__)

PLAN_DELIMITER: str = ";"
log.debug(f"PLAN_DELIMITER: {PLAN_DELIMITER}")





if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    set_openai_key()
    