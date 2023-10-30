import asyncio
from ffmpeg.asyncio import FFmpeg
from dataclasses import dataclass
import os

ROBOT_DATA_DIR = "/home/pi/dev/data/"
REMOTE_DATA_DIR = "/home/oop/dev/data/"
REMOTE_USERNAME = "oop"
REMOTE_IP = "192.168.1.44"

VIDEO_DURATION = 3
VIDEO_FPS = 10

@dataclass
class Camera:
    device: str
    name: str
    width: int
    height: int
    desc: str

CAMERAS = [
    Camera(device="/dev/video0", name="stereo", width=960, height=1080, desc="stereo camera on the face facing forward"),
    Camera(device="/dev/video2", name="mono", width=640, height=480, desc="monocular camera on the chest facing forward"),
]

async def send_file(
    filename: str,
    robot_dir_path: str = ROBOT_DATA_DIR,
    remote_dir_path: str = REMOTE_DATA_DIR,
    username: str = REMOTE_USERNAME,
    remote_ip: str = REMOTE_IP,
) -> str:
    msg: str = ""
    local_path = os.path.join(robot_dir_path, filename)
    remote_path = os.path.join(remote_dir_path, filename)
    cmd = ["scp", local_path, f"{username}@{remote_ip}:{remote_path}"]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        msg += f"ERROR on sending {stderr.decode()}"
    return msg

async def record_video(
    camera: Camera,
    duration: int = VIDEO_DURATION,
    fps: int = VIDEO_FPS,
) -> str:
    msg: str = ""
    output_filename = f"{camera.name}.mp4"
    output_path = os.path.join(ROBOT_DATA_DIR, output_filename)
    ffmpeg = (
        FFmpeg()
        .option("y")
        .option("t", str(duration))
        .option("r", str(fps))
        .option("f", "v4l2")
        .option("video_size", f"{camera.width}x{camera.height}")
        .option("c:v", "h264")
        .input(camera.device)
        .output(output_path)
    )
    stdout, stderr = await ffmpeg.execute()
    msg += f"Recorded {output_filename} of duration {duration} seconds\n"
    if stderr:
        msg += f"ERROR when recording {stderr.decode()}"
        return msg
    msg += await send_file(output_filename)
    return msg

async def test_cameras():
    tasks = [record_video(camera) for camera in CAMERAS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(test_cameras())