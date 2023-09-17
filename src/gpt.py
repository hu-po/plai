import logging
import os
from typing import Dict, List, Tuple

import openai

# ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = '/home/oop/dev/plai'
KEYS_DIR = os.path.join(ROOT_DIR, ".keys")
DEFAULT_LLM: str = "gpt-3.5-turbo"
assert DEFAULT_LLM in [
    "gpt-3.5-turbo",
    "gpt-4",
    # TODO: llama through hf?
]
DEFAULT_TEMPERATURE: float = 0
DEFAULT_MAX_TOKENS: int = 64

log = logging.getLogger('plai')


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
    log.debug("OpenAI API key set.")
    return key


def gpt_text(
    messages: List[Dict[str, str]] = None,
    model="gpt-3.5-turbo",
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    stop: List[str] = ["\n"],
) -> str:
    log.debug("Starting gpt_text function with parameters: messages=%s, model=%s, temperature=%s, max_tokens=%s, stop=%s", messages, model, temperature, max_tokens, stop)
    response: Dict = openai.ChatCompletion.create(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
    )
    log.debug("Received response from OpenAI: %s", response)
    return response["choices"][0]["message"]["content"]

def gpt_trajectory(
    trajectory_description: str,
    num_keyframes: int = 4,
    model="gpt-3.5-turbo",
    num_servos: int = 2,
    keyframe_delimiter: str = ",",
    servo_delimiter: str = " ",
    min_value: int = 0,
    max_value: int = 255,
) -> List[Tuple[int, int]]:
    _messages = [
            {
                "role": "system",
                "content": " ".join(
                    [
                        "Given a description of a trajectory, output the trajectory.",
                        f"You output trajectories for a {num_servos}DoF robot arm.",
                        f"The trajectory is list of integers between {min_value} and {max_value}.",
                        f"The delimiter used for the trajectory is {keyframe_delimiter}",
                        f"The delimiter used for the servo values is {servo_delimiter}",
                    ]
                ),
            },
            {
                "role": "user",
                "content": "Give me a min, max, min trajectory with 3 keyframes.",
            },
            {
                "role": "assistant",
                "content": f"{servo_delimiter.join(['0'] * num_servos)}{keyframe_delimiter}{servo_delimiter.join(['255'] * num_servos)}{keyframe_delimiter}{servo_delimiter.join(['0'] * num_servos)}",
            },
            {
                "role": "user",
                "content": "Give me a blip trajectory with 2 keyframes.",
            },
            {
                "role": "assistant",
                "content": f"{servo_delimiter.join(['0'] * num_servos)}{keyframe_delimiter}{servo_delimiter.join(['10'] * num_servos)}",
            },
            {
                "role": "user",
                "content": f"Give me a {trajectory_description} trajectory with {num_keyframes} keyframes.",
            },
        ]
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
