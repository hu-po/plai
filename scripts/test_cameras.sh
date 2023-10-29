v4l2-ctl --list-devices
echo "stereo camera"
# ffplay -f v4l2 -framerate 30 -video_size 960x1080 -i /dev/video0
ffmpeg -y -f v4l2 -r 5 -t 2 -video_size 960x1080 -i /dev/video0 -c:v h264 out.mp4
scp out.mp4 oop@192.168.1.44:/home/oop/dev/data/pi.stereo.mp4

echo "mono camera"
# ffplay -f v4l2 -framerate 30 -video_size 640x480 -i /dev/video1
ffmpeg -y -f v4l2 -r 5 -t 2 -video_size 640x480 -i /dev/video2 -c:v h264 out.mp4
scp out.mp4 oop@192.168.1.44:/home/oop/dev/data/pi.mono.mp4