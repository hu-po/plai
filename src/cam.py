import asyncio
from ffmpeg.asyncio import FFmpeg


async def send_video(
    local_path: str,
    remote_path: str,
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
    output_path: str,
    width: int,
    height: int,
    fps: int,
    video_device: str,
    duration: int
) -> str:
    ffmpeg = (
        FFmpeg()
        .option("y")
        .option("t", str(duration))
        .input(
            video_device, format="v4l2", framerate=fps, video_size=f"{width}x{height}"
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
    result_recording_stereo = asyncio.run(record_video(
        output_path="/home/pi/dev/data/pi.stereo.mp4",
        width=960,
        height=1080,
        fps=5,
        video_device="/dev/video0",
        duration=2
    ))
    print(result_recording_stereo)
    result_sending_stereo = asyncio.run(send_video(
        local_path="/home/pi/dev/data/pi.stereo.mp4",
        remote_path="/home/oop/dev/data/pi.stereo.mp4"
    ))
    print(result_sending_stereo)

    # Test case for mono camera
    result_recording_mono = asyncio.run(record_video(
        output_path="/home/pi/dev/data/pi.mono.mp4",
        width=640,
        height=480,
        fps=5,
        video_device="/dev/video2",
        duration=2
    ))
    print(result_recording_mono)
    result_sending_mono = asyncio.run(send_video(
        local_path="/home/pi/dev/data/pi.mono.mp4",
        remote_path="/home/oop/dev/data/pi.mono.mp4"
    ))
    print(result_sending_mono)
