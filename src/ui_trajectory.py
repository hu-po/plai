import gradio as gr
from src.gpt import gpt_trajectory

def gradio_gpt_trajectory(trajectory_description: str):
    trajectory = gpt_trajectory(trajectory_description)
    return str(trajectory)

# Textbox for trajectory description
trajectory_description = gr.inputs.Textbox(lines=2, label='Trajectory Description')

# Creating the interface
iface = gr.Interface(
    fn=gradio_gpt_trajectory,
    inputs=trajectory_description,
    outputs="text",
)

if __name__ == "__main__":
    iface.launch()