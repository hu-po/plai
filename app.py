import os
import subprocess
import sys

import gradio as gr

def remote_chromium_gradio_ui(
    display_number: str = "0.0",
    localhost_port: str = "7860",
):
    # Start chromium browser in kiosk mode on remote display (raspberry pi)
    os.environ["DISPLAY"] = f":{display_number}"
    _cmd = ["chromium-browser", "--kiosk", f"http://localhost:{localhost_port}"]
    return subprocess.Popen(_cmd, stdin=subprocess.PIPE)

def update_interface(servo1, servo2, servo3):
    return image

# Sliders for each servo
servo1_slider = gr.Slider(minimum=0, maximum=360, value=180, label='Servo 1')
servo2_slider = gr.Slider(minimum=0, maximum=360, value=180, label='Servo 2')
servo3_slider = gr.Slider(minimum=0, maximum=360, value=180, label='Servo 3')
image = gr.Image(shape=(480, 640), image_mode='L', invert_colors=True, label='Camera')

# Creating the interface
iface = gr.Interface(
    fn=update_interface,
    inputs=[servo1_slider, servo2_slider, servo3_slider],
    outputs=[image],
    live=True,
)

if __name__ == "__main__":
    try:
        process = remote_chromium_gradio_ui()
        iface.launch()
    except KeyboardInterrupt:
        print("Remote chromium browser terminated.")
        sys.exit(0)
    except subprocess.CalledProcessError:
        print("Error: chromium process failed.")