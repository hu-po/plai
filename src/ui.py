import gradio as gr

def move_cat_toy(servo1, servo2, servo3):
    # For demonstration purposes, we will just return the angles of the servos.
    # In a real-world application, you'd send these values to your robot to adjust the servos.
    return f"Servo 1 set to {servo1}°, Servo 2 set to {servo2}°, Servo 3 set to {servo3}°"

# Sliders for each servo
servo1_slider = gr.inputs.Slider(minimum=0, maximum=360, default=180, label='Servo 1')
servo2_slider = gr.inputs.Slider(minimum=0, maximum=360, default=180, label='Servo 2')
servo3_slider = gr.inputs.Slider(minimum=0, maximum=360, default=180, label='Servo 3')

# Creating the interface
iface = gr.Interface(
    fn=move_cat_toy,
    inputs=[servo1_slider, servo2_slider, servo3_slider],
    outputs="text",
    live=True,
)

iface.launch()