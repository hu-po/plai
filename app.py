import gradio as gr
from gpt import gpt_trajectory
import os
import subprocess
import logging

from src.iface_trajectory import iface_trajectory
from src.iface_servo import iface_servo

log = logging.getLogger(__name__)

def remote_chromium_gradio_ui(display_number: str = "0.0", localhost_port: str = "7860"):
    os.environ["DISPLAY"] = f":{display_number}"
    _cmd = ["chromium-browser", "--kiosk", f"http://localhost:{localhost_port}"]
    log.info(f"Starting remote chromium browser with command: {_cmd}")
    return subprocess.Popen(_cmd, stdin=subprocess.PIPE)

# Combine the interfaces into a single interface with separate tabs
iface_combined = gr.TabbedInterface([iface_servo, iface_trajectory], ["servo", "trajectory"])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        process = remote_chromium_gradio_ui()
        iface_combined.launch()
    except KeyboardInterrupt:
        log.info("Remote chromium browser terminated.")
        sys.exit(0)
    except subprocess.CalledProcessError:
        log.error("Error: chromium process failed.")