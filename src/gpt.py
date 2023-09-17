import logging
import os
from typing import Dict, List, Tuple
import pytest

import openai

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_DIR = os.path.join(ROOT_DIR, ".keys")
DEFAULT_LLM: str = "gpt-3.5-turbo"
assert DEFAULT_LLM in [
    "gpt-3.5-turbo",
    "gpt-4",
    # TODO: llama through hf?
]
DEFAULT_TEMPERATURE: float = 0
DEFAULT_MAX_TOKENS: int = 64

log = logging.getLogger(__name__)


def set_openai_key(key=None) -> str:
    if key is None:
        try:
            with open(os.path.join(KEYS_DIR, "openai.txt"), "r") as f:
                key = f.read()
        except FileNotFoundError:
            log.warning("OpenAI API key not found.")
            return
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
    response: Dict = openai.ChatCompletion.create(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
    )
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

def multi_run(arg_sets):
    def decorator(func):
        def wrapper(*args, **kwargs):
            results = []
            bad_configs = []
            for arg_set in arg_sets:
                log.info(f"Running with args: {arg_set}")
                try:
                    result = func(*args, **{**kwargs, **arg_set})
                    results.append(result)
                except AssertionError as e:
                    log.error(e)
                    bad_configs.append(arg_set)
            log.warning(f"Bad configs: {bad_configs}")
            return results
        return wrapper
    return decorator

@multi_run([
    {"model": "gpt-3.5-turbo", "num_servos": 2, "num_keyframes": 4},
    {"model": "gpt-3.5-turbo", "num_servos": 3, "num_keyframes": 5},
    # {"model": "gpt-4", "num_servos": 2, "num_keyframes": 6},
    # {"model": "gpt-4", "num_servos": 3, "num_keyframes": 5},
])
@multi_run([
    {"servo_delimiter": " ", "keyframe_delimiter": ","},
    # {"servo_delimiter": " ", "keyframe_delimiter": "|"},
    # {"servo_delimiter": "\t", "keyframe_delimiter": ";"},
    # {"servo_delimiter": ",", "keyframe_delimiter": "\n"},
    # {"servo_delimiter": ";", "keyframe_delimiter": " "},
])
def gpt_test(
    model: str = DEFAULT_LLM,
    system_prompt: List[str] = None,
    keyframe_delimiter: str = "\n",
    servo_delimiter: str = " ",
    num_servos: int = 2,
    min_value = 0,
    max_value = 255,
    num_keyframes: int = 4,
):
    _messages = [
            {
                "role": "system",
                "content": " ".join(
                    [
                        # "You are a robot control module.",
                        "Given a description of a trajectory, output the trajectory.",
                        f"You output trajectories for a {num_servos}DoF robot arm.",
                        f"The trajectory is list of integers between {min_value} and {max_value}.",
                        f"The delimiter used for the trajectory is {keyframe_delimiter}",
                        f"The delimiter used for the servo values is {servo_delimiter}",
                        # f"Do not add an extra {keyframe_delimiter} at the end of the trajectory.",
                    ]
                ),
            },
            # Mini in-context supervised learning dataset
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
                "content": f"Give me a triangle function trajectory with {num_keyframes} keyframes.",
            },
        ]
    log.info(f"Messages: {_messages}")
    _output: str = gpt_text(
        messages=_messages,
        model=model,
    )
    log.info(f"Raw output: {_output}")
    trajectory: List[Tuple[int, int]] = []
    for keyframe in _output.split(keyframe_delimiter):
        values = [_ for _ in keyframe.split(" ")]
        assert len(values) == num_servos
        assert all([min_value <= int(_val) for _val in values])
        assert all([int(_val) <= max_value for _val in values])
        trajectory.append((int(values[0]), int(values[1])))
    assert len(trajectory) == num_keyframes
    log.info(f"Trajectory: {trajectory}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    set_openai_key()
    # gpt_test()
    print(gpt_trajectory("squiggle", num_keyframes=5))
    print(gpt_trajectory("swoosh", num_keyframes=3))
    print(gpt_trajectory("cosine", num_keyframes=40))
    print(gpt_trajectory("zigzag", num_keyframes=7))
    print(gpt_trajectory("spiral", num_keyframes=10))
    print(gpt_trajectory("ellipse", num_keyframes=25))
    print(gpt_trajectory("sinusoidal", num_keyframes=50))