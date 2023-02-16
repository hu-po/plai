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


if __name__ == '__main__':

    log.setLevel(logging.DEBUG)

    # Calculate FPS
    # TODO: FPS for each component, profile
    started = time.time()
    last_logged = time.time()
    frame_count = 0

    # Servo FPS


    with camera() as get_frame, servos() as servo, model() as (net, preprocess):
        while True:

            # Set servos to starting position
            import pdb; pdb.set_trace()
            servo[0].move(0)
            servo[1].move(0)

            # Get image and preprocess
            image = get_frame()

            # Create a mini-batch as expected by the model
            input_tensor = preprocess(image).unsqueeze(0)
            with torch.no_grad():
                output = net(input_tensor)

            # print results
            top = list(enumerate(output[0].softmax(dim=0)))
            top.sort(key=lambda x: x[1], reverse=True)
            for idx, val in top[:3]:
                print(f"{val.item()*100:.2f}% {classes[idx]}")

            # TODO: Confidence as LED?

            # Goal position is confidence for class
            servo[0].move(top[0][1])
            # Goal position is index of class
            servo[1].move(top[0][0] / len(classes))

            # Calculate FPS
            frame_count += 1
            now = time.time()
            if now - last_logged > 1:
                print(f"{frame_count / (now-last_logged)} fps")
                last_logged = now
                frame_count = 0
