import os
import subprocess
import sys

import gradio as gr
from src.servo import Robot
from src.camera import Camera
from src.plan import Plan, plan_from_description

def remote_chromium_gradio_ui(
    display_number: str = "0.0",
    localhost_port: str = "7860",
):
    # Start chromium browser in kiosk mode on remote display (raspberry pi)
    os.environ["DISPLAY"] = f":{display_number}"
    _cmd = ["chromium-browser", "--kiosk", f"http://localhost:{localhost_port}"]
    return subprocess.Popen(_cmd, stdin=subprocess.PIPE)

# ----- Servos

def move(servo1, servo2, servo3):
    robot = Robot()
    servos.move(*servos.degrees_to_units([servo1, servo2, servo3]))
    degrees = [servos.units_to_degrees(position) for position in servos._read_pos()]
    return f"Servo 1: {degrees[0]} degrees, Servo 2: {degrees[1]} degrees, Servo 3: {degrees[2]} degrees"

# Sliders for each servo
servo1_slider = gr.Slider(minimum=0, maximum=360, value=180, label='Servo 1')
servo2_slider = gr.Slider(minimum=0, maximum=360, value=180, label='Servo 2')
servo3_slider = gr.Slider(minimum=0, maximum=360, value=180, label='Servo 3')

# Creating the interface
iface_servo = gr.Interface(
    fn=move,
    inputs=[servo1_slider, servo2_slider, servo3_slider],
    outputs="text",
    live=True,
)

# ----- Camera

def capture_video():
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

# ----- Plan

def gradio_plan(description: str):
    _plan: str = plan_from_description(description)
    return _plan

description = gr.inputs.Textbox(lines=2, label='Description')

# Creating the interface
iface_plan = gr.Interface(
    fn=gradio_plan,
    inputs=description,
    outputs="text",
)

# Combine the interfaces into a single interface with separate tabs
iface_combined = gr.TabbedInterface(
    [iface_servo, iface_camera, iface_plan],["servo", "camera", "plan"]
)

if __name__ == "__main__":
    try:
        process = remote_chromium_gradio_ui()
        iface_combined.launch()
    except KeyboardInterrupt:
        print("Remote chromium browser terminated.")
        sys.exit(0)
    except subprocess.CalledProcessError:
        print("Error: chromium process failed.")