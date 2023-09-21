import logging
import gradio as gr
from .camera import Camera

log = logging.getLogger(__name__)

def capture():
    camera = Camera()
    image = camera.get_image()
    return image

# Creating the interface
iface_camera = gr.Interface(
    fn=capture,
    inputs=gr.inputs.Button(label='Capture Image'),
    outputs=gr.outputs.Image(),
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    iface_camera.launch()