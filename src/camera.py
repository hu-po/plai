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
        self.width = width
        self.height = height
        self.fps = fps
        self.fpo = fpo
        self.device = device
        self.cap = start_capture()

    def start_capture(self):
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

    def image(self) -> np.ndarray:
        raw_image = self.cap.stdout.read(self.width * self.height * 3)
        if not raw_image:
            log.error("Failed to capture frame")
            raise RuntimeError("Failed to capture frame")
        image = np.frombuffer(raw_image, np.uint8).reshape([self.height, self.width, 3])
        log.debug(f"Captured image {image.shape}")
        return image

    def video(self) -> np.ndarray:
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
        return observation

    def __del__(self):
        log.info("Deleting video capture")
        self.cap.stdin.close()
        self.cap.wait()