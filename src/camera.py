import numpy as np
import logging
import ffmpeg

log = logging.getLogger(__name__)

class Camera:
    def __init__(self, width: int = 640, height: int = 480, fps: int = 30, device: str = '/dev/video0'):
        """Initializes the video capture.

        Parameters:
        width (int): The width of the video frames.
        height (int): The height of the video frames.
        fps (int): The frames per second of the video.
        device (str): The device to capture video from.
        """
        self.width = width
        self.height = height
        log.info(f"Starting video capture at {self.width}x{self.height} {fps}fps")
        self.process = (
            ffmpeg
            .input(device, format='video4linux2', video_size=f'{self.width}x{self.height}', framerate=fps)
            .output('pipe:', format='rawvideo', pix_fmt='rgb24')
            .run_async(pipe_stdout=True)
        )

    def get_image(self) -> np.ndarray:
        """Capture a frame and return it as a numpy array.

        Returns:
        np.ndarray: The captured frame.

        Raises:
        RuntimeError: If a frame capture fails.
        """
        raw_image = self.process.stdout.read(self.width*self.height*3)
        if not raw_image:
            log.error("Failed to capture frame")
            raise RuntimeError("Failed to capture frame")
        image = np.frombuffer(raw_image, np.uint8).reshape([self.height, self.width, 3])
        log.debug(f"Captured image {image.shape}")
        return image

    def __del__(self):
        """Releases the video capture when the object is deleted."""
        log.info("Ended video capture")
        self.process.terminate()

if __name__ == "__main__":
    camera = Camera()
    image = camera.get_image()
    # Displaying the image requires a different approach as we're not using OpenCV anymore
    # You can use matplotlib for example
    import matplotlib.pyplot as plt
    plt.imshow(image)
    plt.show()