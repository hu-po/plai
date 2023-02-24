import gradio as gr


demo = gr.Interface(
    fn=lambda x: x,
    inputs='text',
    outputs='text',
)

demo.launch()