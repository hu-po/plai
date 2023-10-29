import asyncio
from ffmpeg.asyncio import FFmpeg
from dataclasses import dataclass
import os

USERNAME_DEFAULT = "oop"
REMOTE_IP_DEFAULT = "192.168.1.44"
DEFAULT_DURATION = 3

ROBOT_DATA_DIR = "/home/pi/dev/data/"
REMOTE_DATA_DIR = "/home/oop/dev/data/"

@dataclass
class Camera:
    device: str
    name: str
    width: int
    height: int
    desc: str

CAMERAS = [
    Camera(device="/dev/video0", name="pi.stereo", width=960, height=1080, desc="Stereo Camera"),
    Camera(device="/dev/video2", name="pi.mono", width=640, height=480, desc="Mono Camera"),
]

async def send_video(
    robot_dir_path: str = ROBOT_DATA_DIR,
    remote_dir_path: str = REMOTE_DATA_DIR,
    output_filename: str = "pi.stereo.mp4",
    username: str = USERNAME_DEFAULT,
    remote_ip: str = REMOTE_IP_DEFAULT,
) -> str:
    local_path = os.path.join(robot_dir_path, output_filename)
    remote_path = os.path.join(remote_dir_path, output_filename)
    cmd = ["scp", local_path, f"{username}@{remote_ip}:{remote_path}"]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return f"SCP command failed with error: {stderr.decode()}"
    else:
        return f"Successfully sent {local_path} to {remote_ip}:{remote_path}"

async def record_video(
    camera: Camera,
    duration: int = DEFAULT_DURATION
) -> str:
    output_path = os.path.join(ROBOT_DATA_DIR, f"{camera.name}.mp4")
    ffmpeg = (
        FFmpeg()
        .option("y")
        .option("t", str(duration))
        .input(
            camera.device, format="v4l2",
            framerate=camera.fps, video_size=f"{camera.width}x{camera.height}"
        )
        .output(output_path, vcodec="h264")
    )
    stdout, stderr = await ffmpeg.execute()
    if stderr:
        return f"Recording failed with error: {stderr.decode()}"
    else:
        return f"Recording completed and saved to {output_path}"

async def handle_camera(camera):
    record_result = await record_video(camera=camera, duration=2)
    
    if "error" in record_result.lower():
        print(f"Error occurred while recording for {camera.name}: {record_result}")
        return

    send_result = await send_video(output_filename=f"{camera.name}.mp4")
    if "error" in send_result.lower():
        print(f"Error occurred while sending video for {camera.name}: {send_result}")

async def run_camera_tasks():
    tasks = [handle_camera(camera) for camera in CAMERAS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_camera_tasks())