""" Camera code. 

Check your camera is working with:

v4l2-ctl --list-devices
ffplay -f v4l2 -framerate 30 -video_size 224x224 -i /dev/video0

"""

import logging
import time
from contextlib import contextmanager

import cv2
import numpy as np

log = logging.getLogger(__name__)

@contextmanager
def camera_ctx(
    width: int = 224,
    height: int = 224,
    fps: int = 30,
):
    """Context manager for video capture.

    Parameters:
    width (int): The width of the video frames.
    height (int): The height of the video frames.
    fps (int): The frames per second of the video.

    Yields:
    function: A function that captures a frame and returns it as a numpy array.
    """
    log.info(f"Starting video capture at {width}x{height} {fps}fps")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    def np_image() -> np.ndarray:
        """Capture a frame and return it as a numpy array.

        Returns:
        np.ndarray: The captured frame.

        Raises:
        RuntimeError: If a frame capture fails.
        """
        ret, image = cap.read()
        if not ret:
            log.error("Failed to capture frame")
            raise RuntimeError("Failed to capture frame")
        # convert opencv output from BGR to RGB
        image = image[:, :, [2, 1, 0]]
        log.debug(f"Captured image {image.shape}")
        return image

    try:
        yield np_image
    finally:
        log.info("Ended video capture")
        cap.release()

if __name__ == "__main__":
    with camera_ctx() as snapshot:
        image = snapshot()
    cv2.imshow("image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()