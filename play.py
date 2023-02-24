""" Start play mode. """

from imagenet_labels import classes
import logging
import time
from contextlib import contextmanager

import torch
from torchvision import models, transforms


# from servo import servo_ctx
# from camera import camera_ctx
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Imagenet classes for cats
IMAGENET_CATS = {
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

    def inference(x):
        with torch.no_grad():
            # Create a mini-batch as expected by the model
            x = preprocess(x).unsqueeze(0)
            x = net(x)
            return x
    try:
        yield inference
    finally:
        log.info("Ended AI model")
        pass


def is_cat_imagenet(output, threshold=0.5):
    """ Check if the model thinks it is a cat. """
    is_cat: bool = False
    cat_ids = set(IMAGENET_CATS.keys())
    top = list(enumerate(output[0].softmax(dim=0)))
    # Get confidence score on cat classes
    for cat_id in cat_ids:
        if top[cat_id][1] > threshold:
            is_cat = True
            break
    # Get the top predictions
    top.sort(key=lambda x: x[1], reverse=True)
    top = [(classes[x[0]], f"{x[1]:.2f}") for x in top[:20]]
    return is_cat, top


# if __name__ == '__main__':

#     log.setLevel(logging.DEBUG)

#     # Calculate FPS
#     # TODO: FPS for each component, profile
#     started = time.time()
#     last_logged = time.time()
#     frame_count = 0

#     with camera_ctx() as np_image:
#         with servo_ctx() as servo:
#             with model() as predict:
#                 while True:

#                     # Set servos to starting position
#                     servo[0].move(0)
#                     servo[1].move(0)

#                     # Get image and preprocess
#                     image = np_image()

#                     # Create a mini-batch as expected by the model
#                     output = predict(image)

#                     if is_cat(output):
#                         # The Wiggle
#                         servo[0].move(0.1)
#                         servo[1].move(0.1)
#                         servo[0].move(0.05)
#                         servo[1].move(0.05)
#                         servo[0].move(0.1)
#                         servo[1].move(0.1)
#                         continue

#                     # Calculate FPS
#                     frame_count += 1
#                     now = time.time()
#                     if now - last_logged > 1:
#                         print(f"{frame_count / (now-last_logged)} fps")
#                         last_logged = now
#                         frame_count = 0
