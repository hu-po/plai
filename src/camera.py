import numpy as np
import logging

log = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    log.error("OpenCV is not installed. Please install it to use the Camera class.")
    cv2 = None

class Camera:
    def __init__(self, width: int = 224, height: int = 224, fps: int = 30):
        """Initializes the video capture.

        Parameters:
        width (int): The width of the video frames.
        height (int): The height of the video frames.
        fps (int): The frames per second of the video.
        """
        if cv2 is None:
            raise RuntimeError("OpenCV is not installed. Please install it to use the Camera class.")
        log.info(f"Starting video capture at {width}x{height} {fps}fps")
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

    def get_image(self) -> np.ndarray:
        """Capture a frame and return it as a numpy array.

        Returns:
        np.ndarray: The captured frame.

        Raises:
        RuntimeError: If a frame capture fails.
        """
        ret, image = self.cap.read()
        if not ret:
            log.error("Failed to capture frame")
            raise RuntimeError("Failed to capture frame")
        # convert opencv output from BGR to RGB
        image = image[:, :, [2, 1, 0]]
        log.debug(f"Captured image {image.shape}")
        return image

    def __del__(self):
        """Releases the video capture when the object is deleted."""
        log.info("Ended video capture")
        self.cap.release()

if __name__ == "__main__":
    camera = Camera()
    image = camera.get_image()
    cv2.imshow("image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()