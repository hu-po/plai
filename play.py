""" Start play mode. """

import logging
import time
from contextlib import contextmanager

import cv2
import numpy as np
import torch
from torchvision import models, transforms

from imagenet_labels import classes
from servo import servos

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@contextmanager
def camera(
    width: int = 224,
    height: int = 224,
    fps: int = 36,
):
    log.info("Starting video capture")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    def get_frame() -> np.ndarray:
        ret, image = cap.read()
        if not ret:
            log.error("Failed to capture frame")
            return None
        # convert opencv output from BGR to RGB
        image = image[:, :, [2, 1, 0]]
        return image

    try:
        yield get_frame
    finally:
        log.info("Ended video capture")
        del cap


@contextmanager
def model(*args, **kwds):
    log.info("Starting AI model")
    torch.backends.quantized.engine = 'qnnpack'
    preprocess = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]),
    ])
    net = models.quantization.mobilenet_v2(pretrained=True, quantize=True)
    # jit model to take it from ~20fps to ~30fps
    net = torch.jit.script(net)
    try:
        yield net, preprocess
    finally:
        log.info("Ended AI model")
        pass


def is_cat(output):
    """ Check if the model thinks it is a cat. """
    top = list(enumerate(output[0].softmax(dim=0)))
    top.sort(key=lambda x: x[1], reverse=True)
    CATS = {
        281: 'tabby, tabby cat',
        282: 'tiger cat',
        283: 'Persian cat',
        284: 'Siamese cat, Siamese',
        285: 'Egyptian cat',
        286: 'cougar, puma, catamount, mountain lion, painter, panther, Felis concolor',
        287: 'lynx, catamount',
        288: 'leopard, Panthera pardus',
        289: 'snow leopard, ounce, Panthera uncia',
        290: 'jaguar, panther, Panthera onca, Felis onca',
        291: 'lion, king of beasts, Panthera leo',
        292: 'tiger, Panthera tigris',
        293: 'cheetah, chetah, Acinonyx jubatus',
    }
    cat_ids = set(CATS.keys())
    if top[0][0] in cat_ids:
        log.info(
            f"\n\n {top[0][1]*100.0:.2f} cat detected {CATS[top[0][0]]} \n\n")
        return True
    else:
        log.info(f"Not a cat: {top[0][1]} {classes[top[0][0]]}")
        return False


if __name__ == '__main__':

    log.setLevel(logging.DEBUG)

    # Calculate FPS
    # TODO: FPS for each component, profile
    started = time.time()
    last_logged = time.time()
    frame_count = 0

    with camera() as get_frame, servos() as servo, model() as (net, preprocess):
        while True:

            # Set servos to starting position
            servo[0].move(0)
            servo[1].move(0)

            # Get image and preprocess
            image = get_frame()

            # Create a mini-batch as expected by the model
            input_tensor = preprocess(image).unsqueeze(0)
            with torch.no_grad():
                output = net(input_tensor)

            if is_cat(output):
                servo[0].move(1)
                servo[1].move(1)
                servo[0].move(0.2)
                servo[1].move(0.2)
                servo[0].move(1)
                servo[1].move(1)
                continue

            # Calculate FPS
            frame_count += 1
            now = time.time()
            if now - last_logged > 1:
                print(f"{frame_count / (now-last_logged)} fps")
                last_logged = now
                frame_count = 0
