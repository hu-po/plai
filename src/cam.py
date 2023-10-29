import asyncio
from ffmpeg import Progress
from ffmpeg.asyncio import FFmpeg


async def send_video(
    filename: str = "output.mp4",
    remote_ip: str = "192.168.1.2",
    remote_path: str = "/path/to/destination/",
    username: str = "default_username",
) -> str:
    cmd = ["scp", filename, f"{username}@{remote_ip}:{remote_path}"]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        return f"SCP command failed with error: {stderr.decode()}"
    else:
        return f"Successfully sent {filename} to {remote_ip}:{remote_path}"


async def record_video(
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    output_filename: str = "output",
    extension: str = "mp4",
    max_frames: int = 500,
    video_device: str = "/dev/video0",
) -> str:
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(
            video_device, format="v4l2", framerate=fps, video_size=f"{width}x{height}"
        )
        .output(f"{output_filename}.{extension}", vcodec="copy")
    )

    @ffmpeg.on("progress")
    def time_to_terminate(progress: Progress):
        if progress.frame > max_frames:
            ffmpeg.terminate()

    await ffmpeg.execute()
    return f"Recording completed and saved to {output_filename}.{extension}"


if __name__ == "__main__":
    result_recording = asyncio.run(record_video())
    print(result_recording)

    result_sending = asyncio.run(send_video())
    print(result_sending)
