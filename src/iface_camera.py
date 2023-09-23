import logging
import gradio as gr
from .camera import Camera

log = logging.getLogger(__name__)

class CameraCapture:
    def __init__(self):
        self.camera = Camera()

    def capture(self, *args, **kwargs):
        image = self.camera.get_image()
        return image

camera_capture = CameraCapture()

# Creating the interface
iface_camera = gr.Interface(
    fn=camera_capture.capture,
    inputs=gr.Button(label='Capture Image'),
    outputs=gr.Image(),
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    iface_camera.launch()