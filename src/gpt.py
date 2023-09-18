import logging
import os
from typing import Dict, List, Tuple

import openai

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS_DIR = os.path.join(ROOT_DIR, ".keys")
DEFAULT_LLM: str = "gpt-4"

log = logging.getLogger(__name__)


def set_openai_key(key=None) -> str:
    """
    This function sets the OpenAI API key.

    Parameters:
    key (str): The OpenAI API key. If not provided, the function will try to read it from a file.

    Returns:
    str: The OpenAI API key.

    Raises:
    FileNotFoundError: If the key file is not found and no key is provided.
    """
    if key is None:
        try:
            # Try to read the key from a file
            with open(os.path.join(KEYS_DIR, "openai.txt"), "r") as f:
                key = f.read()
        except FileNotFoundError:
            log.warning("OpenAI API key not found.")
            return
    # Set the OpenAI API key
    openai.api_key = key
    log.info("OpenAI API key set.")
    return key


def gpt_text(
    messages: List[Dict[str, str]] = None,
    model="gpt-3.5-turbo",
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    stop: List[str] = ["\n"],
) -> str:
    log.debug(f"Sending messages to OpenAI: {messages}")
    response: Dict = openai.ChatCompletion.create(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
    )
    reply: str = response["choices"][0]["message"]["content"]
    log.debug(f"Received reply from OpenAI: {reply}")
    return reply

class Trajectory:
    def __init__(self, keyframes: int = 4, description: str = '', num_servos: int = 3, keyframe_delimiter: str = ',', servo_delimiter: str = ' '):
        self.keyframes = keyframes
        self.description = description
        self.num_servos = num_servos
        self.keyframe_delimiter = keyframe_delimiter
        self.servo_delimiter = servo_delimiter



def gpt_trajectory(
    trajectory_description: str,
    num_keyframes: int = 4,
    num_servos: int = 3,
    keyframe_delimiter: str = ",",
    servo_delimiter: str = " ",
    min_value: int = 0,
    max_value: int = 360,
) -> List[Tuple[int, int]]:
    _messages = [
            {
                "role": "system",
                "content": " ".join(
                    [
                        "Output a trajectory based on a string description of a trajectory and a number of keyframes.",
                        f"You output trajectories for a {num_servos}DoF robot arm.",
                        f"A trajectory is a sequence of keyframes.",
                        f"Each keyframe represents {num_servos} integer degree values for each servo between {min_value} and {max_value}.",
                        f"The delimiter used for the trajectory is {keyframe_delimiter}",
                        f"The delimiter used for the servo values is {servo_delimiter}",
                    ]
                ),
            },
            {
                "role": "user",
                "content": "keyframes: 3, description: min, max, min",
            },
            {
                "role": "assistant",
                "content": f"{servo_delimiter.join([str(min_value)] * num_servos)}{keyframe_delimiter}{servo_delimiter.join([str(max_value)] * num_servos)}{keyframe_delimiter}{servo_delimiter.join([str(min_value)] * num_servos)}",
            },
            {
                "role": "user",
                "content": "keyframes: 2, description: zero to halfway",
            },
            {
                "role": "assistant",
                "content": f"{servo_delimiter.join([str(min_value)] * num_servos)}{keyframe_delimiter}{servo_delimiter.join([str(max_value//2)] * num_servos)}",
            },
            {
                "role": "user",
                "content": f"keyframes: {num_keyframes}, description: {trajectory_description}",
            },
        ]
    reply = gpt_text(messages=_messages)
    trajectory: List[Tuple[int, int]] = []
    for keyframe in gpt_text(
        messages=_messages,
        model=model,
    ).split(keyframe_delimiter):
        if not keyframe:
            continue
        values = [_ for _ in keyframe.split(" ")]
        trajectory.append((int(values[0]), int(values[1])))
    return trajectory

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    set_openai_key()
    print(gpt_trajectory("min, max, min", num_keyframes=3))
