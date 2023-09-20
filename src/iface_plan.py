import logging

import gradio as gr

from .plan import plan_from_description
from .robot import Robot

log = logging.getLogger(__name__)

def gradio_plan(description: str):
    bot = Robot()
    raw_plan: str = plan_from_description(description)
    log.info(f"Running plan: {raw_plan}")
    bot.run_plan(plan)
    return raw_plan

description = gr.inputs.Textbox(lines=2, label='Description')

# Creating the interface
iface_plan = gr.Interface(
    fn=gradio_plan,
    inputs=description,
    outputs="text",
)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    iface.launch()