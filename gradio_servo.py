"""

If the Gradio app is running on port 7860 on a computer with IP address 192.168.1.100, and you want to access it from a computer with IP address 192.168.1.200 using port 7861, you could use the following command:

ssh -L 7861:localhost:7860 user@192.168.1.100

On the local computer go to the URL

http://localhost:7861

"""

import gradio as gr
from servo import Servo
from typing import List


def run(servo_1, servo_2):
    servos: List[Servo] = [
        Servo(
            id=1,
            min_pos=853,
            max_pos=1469,
        ),
        Servo(
            id=2,
            min_pos=3660,
            max_pos=4462,
        ),
    ]
    # Copy the port handler and packet handler to the other servos
    for servo in servos[1:]:
        servo.portHandler = servos[0].portHandler
        servo.packetHandler = servos[0].packetHandler
    # Move the servos to a position
    servos[0].move(servo_1)
    servos[1].move(servo_2)
    # Read the current position
    pos_1 = servos[0].get_position()
    pos_2 = servos[1].get_position()
    return f"Servo 1: {pos_1}\nServo 2: {pos_2}"


# Create interface
interface = gr.Interface(
    run,
    [
        gr.Slider(minimum=0.0, maximum=1.0, value=0.5, label="Servo 1"),
        gr.Slider(minimum=0.0, maximum=1.0, value=0.5, label="Servo 2"),
    ],
    [
        gr.Textbox(lines=2, label="Output")
    ],
    title="Plai",
    description="Control the servos",
)

if __name__ == "__main__":
    interface.launch()
