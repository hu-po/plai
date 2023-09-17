"""
    Run.
"""

import time
from typing import List
import random

from camera import camera_ctx
from model import is_cat_imagenet, model
from servo import Servo


def run():
    msg = ""
    servos: List[Servo] = [
        Servo(
            id=1,
            min_pos=869,
            max_pos=1420,
        ),
        Servo(
            id=2,
            min_pos=3700,
            max_pos=4000,
        ),
    ]
    # Copy the port handler and packet handler to the other servos
    for servo in servos[1:]:
        servo.portHandler = servos[0].portHandler
        servo.packetHandler = servos[0].packetHandler
    # Capture an image
    with camera_ctx() as snapshot:
        image = snapshot()
    # Enable cat detection model
    with model() as predict:
        output = predict(image)
        cat_bool, raw = is_cat_imagenet(output)
        msg += f"is cat: {cat_bool}\n"
        for name, score in raw:
            msg += f"{name} {score}\n"
    if cat_bool:
        # Wiggle the servos
        for keyframe in [0.0, 1.0, 0.0]:
            servos[0].move(keyframe)
            servos[1].move(keyframe)
            pos_1 = (servos[0].get_position() - servos[0].min_pos) / \
                (servos[0].max_pos - servos[0].min_pos)
            pos_2 = (servos[1].get_position() - servos[1].min_pos) / \
                (servos[1].max_pos - servos[1].min_pos)
            time.sleep(random.choice([0.1, 1, 2, 4]))
            msg += f"\n Servo 1: {pos_1:.2f}\n Servo 2: {pos_2:.2f}"

    return image, msg

if __name__ == "__main__":

    # Run the script
    while True:
        try:
            image, msg = run()
        except Exception as e:
            print(e)
            del image, msg
            break