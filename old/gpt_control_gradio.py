import gradio as gr

def move_cat_toy(direction, speed):
    # For demonstration purposes, we will just print the direction and speed.
    # In a real-world application, you'd send these commands to your robot.
    return f"Moving {direction} at speed {speed}"

# Dropdown for directions
directions = gr.inputs.Dropdown(choices=['Forward', 'Backward', 'Left', 'Right'], label='Direction')

# Slider for speed
speed = gr.inputs.Slider(minimum=1, maximum=10, default=5, label='Speed')

# Creating the interface
iface = gr.Interface(
    fn=move_cat_toy,
    inputs=[directions, speed],
    outputs="text"
)

iface.launch()
