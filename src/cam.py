import asyncio
from ffmpeg import Progress
from ffmpeg.asyncio import FFmpeg


async def send_video(
    local_path: str = "/home/pi/dev/data/pi.stereo.mp4",
    remote_path: str = "/home/oop/dev/data/pi.stereo.mp4",
    username: str = "oop",
    remote_ip: str = "192.168.1.44",
) -> str:
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
    output_path: str = "/home/pi/dev/data/pi.stereo.mp4",
    width: int = 960,
    height: int = 1080,
    fps: int = 1,
    max_frames: int = 3,
    video_device: str = "/dev/video0",
) -> str:
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(
            video_device, format="v4l2", framerate=fps, video_size=f"{width}x{height}"
        )
        .output(output_path, vcodec="copy")
    )

    @ffmpeg.on("progress")
    def time_to_terminate(progress: Progress):
        if progress.frame > max_frames:
            ffmpeg.terminate()

    await ffmpeg.execute()
    return f"Recording completed and saved to {output_path}"


if __name__ == "__main__":
    result_recording = asyncio.run(record_video())
    print(result_recording)

    result_sending = asyncio.run(send_video())
    print(result_sending)
