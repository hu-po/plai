import asyncio
from ffmpeg.asyncio import FFmpeg
from dataclasses import dataclass

# Global variables for default values
USERNAME_DEFAULT = "oop"
REMOTE_IP_DEFAULT = "192.168.1.44"

# Global variables for data paths
PI_DATA_PATH = "/home/pi/dev/data/"
OOP_DATA_PATH = "/home/oop/dev/data/"

@dataclass
class Camera:
    Device: str
    name: str
    width: int
    height: int
    desc: str

async def send_video(
    directory_path: str = OOP_DATA_PATH,
    output_filename: str = "pi.stereo.mp4",
    username: str = USERNAME_DEFAULT,
    remote_ip: str = REMOTE_IP_DEFAULT,
) -> str:
    local_path = PI_DATA_PATH + output_filename
    remote_path = directory_path + output_filename
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
    duration: int
) -> str:
    output_path = PI_DATA_PATH + f"{camera.name}.mp4"
    ffmpeg = (
        FFmpeg()
        .option("y")
        .option("t", str(duration))
        .input(
            camera.Device, format="v4l2",
            framerate=camera.fps, video_size=f"{camera.width}x{camera.height}"
        )
        .output(output_path, vcodec="h264")
    )

    stdout, stderr = await ffmpeg.execute()

    if stderr:
        return f"Recording failed with error: {stderr.decode()}"
    else:
        return f"Recording completed and saved to {output_path}"

if __name__ == "__main__":
    # Test case for stereo camera
    stereo_camera = Camera(Device="/dev/video0", name="pi.stereo", width=960, height=1080, desc="Stereo Camera")
    result_recording_stereo = asyncio.run(record_video(
        camera=stereo_camera,
        duration=2
    ))
    print(result_recording_stereo)
    result_sending_stereo = asyncio.run(send_video())
    print(result_sending_stereo)

    # Test case for mono camera
    mono_camera = Camera(Device="/dev/video2", name="pi.mono", width=640, height=480, desc="Mono Camera")
    result_recording_mono = asyncio.run(record_video(
        camera=mono_camera,
        duration=2
    ))
    print(result_recording_mono)
    result_sending_mono = asyncio.run(send_video(directory_path=OOP_DATA_PATH))
    print(result_sending_mono)
