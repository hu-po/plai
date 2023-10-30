import asyncio
import os
from dataclasses import dataclass

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
    msg += f"Sent {local_path} to {remote_path}\n"
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
    cmd = [
        "ffmpeg", "-y",
        "-t", str(duration),
        "-r", str(fps),
        "-f", "v4l2",
        "-video_size", f"{camera.width}x{camera.height}",
        "-c:v", "h264",
        "-i", camera.device,
        output_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if stderr:
        msg += f"FFmpeg Error: {stderr.decode()}\n"
    msg += f"Recorded {output_filename} of duration {duration} seconds\n"
    if process.returncode != 0:
        return msg
    msg += await send_file(output_filename)
    return msg

async def test_cameras():
    tasks = [record_video(camera) for camera in CAMERAS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            print(f"Error: {res}")
        else:
            print(res)

if __name__ == "__main__":
    asyncio.run(test_cameras())
