import gradio as gr
import logging
from .servo import Robot

log = logging.getLogger(__name__)

def move(servo1, servo2, servo3):
    robot = Robot()
    robot.move(*robot.degrees_to_position([servo1, servo2, servo3]))
    degrees = [robot.position_to_degrees(position) for position in robot.get_position()]
    return f"Servo 1: {degrees[0]} degrees, Servo 2: {degrees[1]} degrees, Servo 3: {degrees[2]} degrees"

# Sliders for each servo
servo1_slider = gr.inputs.Slider(minimum=0, maximum=360, default=180, label='Servo 1')
servo2_slider = gr.inputs.Slider(minimum=0, maximum=360, default=180, label='Servo 2')
servo3_slider = gr.inputs.Slider(minimum=0, maximum=360, default=180, label='Servo 3')

# Creating the interface
iface_servo = gr.Interface(
    fn=move,
    inputs=[servo1_slider, servo2_slider, servo3_slider],
    outputs="text",
    live=True,
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    iface.launch()