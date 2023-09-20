import gradio as gr
import logging

def move(servo1, servo2, servo3):
    # Initialize robot
    robot = Robot()
    # Move the servos to the specified positions
    robot.move(servo1, servo2, servo3)
    # Get the current positions of the servos
    positions = robot.get_position()
    # Convert the positions to degrees
    degrees = [robot.position_to_degrees(position) for position in positions]
    # Return the current positions of the servos in degrees
    return f"Servo 1: {degrees[0]}°\nServo 2: {degrees[1]}°\nServo 3: {degrees[2]}°"

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