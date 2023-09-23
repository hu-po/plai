import numpy as np
import logging
import ffmpeg

log = logging.getLogger(__name__)


class Camera:
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 24,
        fpo: int = 8,
        device: str = "/dev/video0",
    ):
        """
        Initializes the video capture.

        Parameters:
        width (int): The width of the video frames in pixels.
        height (int): The height of the video frames in pixels.
        fps (int): The frames per second of the video capture.
        fpo (int): The frames per observation or capture.
        device (str): The device identifier from which to capture video.
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.fpo = fpo
        self.device = device

    def start_capture(self):
        """
        Starts the video capture process.

        Returns:
        subprocess.Popen: The process that is capturing the video.
        """
        log.info(f"Starting video capture at {self.width}x{self.height} {self.fps}fps")
        return (
            ffmpeg.input(
                self.device,
                format="video4linux2",
                video_size=f"{self.width}x{self.height}",
                framerate=self.fps,
            )
            .output("pipe:", format="rawvideo", pix_fmt="rgb24")
            .run_async(pipe_stdout=True)
        )

    def get_image(self) -> np.ndarray:
        """
        Captures a single frame and returns it as a numpy array.

        Returns:
        np.ndarray: The captured frame as a 3D numpy array (height, width, RGB).

        Raises:
        RuntimeError: If the frame capture fails.
        """
        cap = self.start_capture()
        raw_image = self.cap.stdout.read(self.width * self.height * 3)
        if not raw_image:
            log.error("Failed to capture frame")
            raise RuntimeError("Failed to capture frame")
        image = np.frombuffer(raw_image, np.uint8).reshape([self.height, self.width, 3])
        log.debug(f"Captured image {image.shape}")
        cap.terminate()
        log.debug("Ended video capture")
        return image

    def observe(self) -> np.ndarray:
        """
        Captures a sequence of frames and returns them as a 4D numpy array.

        Returns:
        np.ndarray: The captured video as a 4D numpy array (frames, height, width, RGB).

        Raises:
        RuntimeError: If a frame capture fails.
        """
        cap = self.start_capture()
        observation = np.zeros((self.fpo, self.height, self.width, 3), np.uint8)
        for i in range(self.fpo):
            raw_image = self.cap.stdout.read(self.width * self.height * 3)
            if not raw_image:
                log.error("Failed to capture frame")
                raise RuntimeError("Failed to capture frame")
            image = np.frombuffer(raw_image, np.uint8).reshape(
                [self.height, self.width, 3]
            )
            observation[i] = image
        log.debug(f"Captured {observation.shape}")
        cap.terminate()
        log.debug("Ended video capture")
        return observation


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    camera = Camera()
    image = camera.get_image()
    # Displaying the image requires a different approach as we're not using OpenCV anymore
    # You can use matplotlib for example
    import matplotlib.pyplot as plt

    plt.imshow(image)
    plt.show()