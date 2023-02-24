"""

If the Gradio app is running on port 7860 on a computer with IP address 192.168.1.100, and you want to access it from a computer with IP address 192.168.1.200 using port 7861, you could use the following command:

ssh -L 7861:localhost:7860 user@192.168.1.100

On the local computer go to the URL

http://localhost:7861

"""

import gradio as gr
from servo import servo_ctx
from camera import camera_ctx
from play import model, is_cat_imagenet


def run(servo_1, servo_2):
    with servo_ctx() as servo:
        with camera_ctx() as image:
            with model() as predict:
                output = predict(image)
                cat_bool, raw = is_cat_imagenet(output)
                msg = f"is cat: {cat_bool}\n"
                for name, score in raw:
                    msg += f"{name} {score}\n"
                servo[0].move(servo_1)
                servo[1].move(servo_2)
    return image, msg


# Create interface
interface = gr.Interface(
    run,
    [
        gr.Slider(minimum=0.0, maximum=1.0, value=0.5, label="Servo 1"),
        gr.Slider(minimum=0.0, maximum=1.0, value=0.5, label="Servo 2"),
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
