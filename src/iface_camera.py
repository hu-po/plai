import logging
import gradio as gr
from .camera import Camera

log = logging.getLogger(__name__)

def capture_video(self, *args, **kwargs):
    camera = Camera()
    video = camera.video()  # This method returns a 4D numpy array
    del camera
    # Convert the 4d numpy array to a video file
    
    return video

# Creating the interface
iface_camera = gr.Interface(
    fn=capture_video,
    inputs=gr.Button(label='Capture Video'),
    outputs=gr.Video(shape=(8, 480, 640, 3)),  # camera.fpo is the number of frames in the video
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    iface_camera.launch()