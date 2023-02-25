"""

If the Gradio app is running on port 7860 on a computer with IP address 192.168.1.100, and you want to access it from a computer with IP address 192.168.1.200 using port 7861, you could use the following command:

ssh -L 7861:localhost:7860 user@192.168.1.100

On the local computer go to the URL

http://localhost:7861

"""

import time
import gradio as gr
from servo import Servo
from typing import List


from play import model, is_cat_imagenet

def run(image):
    servos: List[Servo] = [
        Servo(
            id=1,
            min_pos=869,
            max_pos=1420,
        ),
        Servo(
            id=2,
            min_pos=3700,
            max_pos=4000,
        ),
    ]
    # Copy the port handler and packet handler to the other servos
    for servo in servos[1:]:
        servo.portHandler = servos[0].portHandler
        servo.packetHandler = servos[0].packetHandler

    # Enable cat detection model
    with model() as predict:
        output = predict(image)
        cat_bool, raw = is_cat_imagenet(output)
        msg = f"is cat: {cat_bool}\n"
        for name, score in raw:
            msg += f"{name} {score}\n"
    if cat_bool:
        # Wiggle the servos
        for keyframe in [0.0, 1.0, 0.0]:
            servos[0].move(keyframe)
            servos[1].move(keyframe)
            pos_1 = servos[0].get_position()
            pos_2 = servos[1].get_position()
            time.sleep(0.2)
            msg += f"Servo 1: {pos_1}\nServo 2: {pos_2}"
        
    return image, f"Servo 1: {pos_1}\nServo 2: {pos_2}"


# Create interface
interface = gr.Interface(
    run,
    [
        gr.Image(source="webcam", label="Camera Image")
    ],
    [
        gr.Image(type="numpy", label="Processed Image"),
        gr.Textbox(lines=2, label="Output")
    ],
    title="Plai",
    description="Control the servos",
)

if __name__ == "__main__":
    interface.launch()
