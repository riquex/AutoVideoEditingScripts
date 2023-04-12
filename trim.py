import subprocess
import os
import re
import sys

# Initiating
if len(sys.argv) != 2:
    raise IndexError('You must pass two arguments!')

# Getting file path
file = sys.argv[1]

if not os.path.isfile(file):
    raise FileNotFoundError(f'file not found {file}')

VIDEO_CODEC = 'h264_amf'
THREASHOLD = '-32dB'
SILENCE_MINIMAL_DURATION = '0.5'
EASE = 0.2

while float(SILENCE_MINIMAL_DURATION) - (2 * EASE) <= 0: EASE -= .01

TOTAL_TIME = float(
        subprocess.check_output(
            f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file}',
            shell=True
        ).decode()
    )

noise_reduction_model_git = 'https://github.com/GregorR/rnnoise-models.git'
noise_reduction_filter = "arnndn=m='rnnoise-models/somnolent-hogwash-2018-09-01/sh.rnnn'"

if not os.path.isdir('GregorR'):
    git_process=subprocess.run(f'git clone {noise_reduction_model_git}', shell=True, capture_output=True)

noise_reduction_process=subprocess.run(f'ffmpeg -hide_banner -vn -i {file} -af {noise_reduction_filter} -y {"NR"+file}', shell=True)

silence_detect_filter = f"silencedetect=n={THREASHOLD}:d={SILENCE_MINIMAL_DURATION}"

silence_times=subprocess.run(f'ffmpeg -hide_banner -vn -i {"NR"+file} -af {silence_detect_filter} -f null -', shell=True, capture_output=True)

os.remove(f'{"NR"+file}')

silence_start = list(re.finditer(r'((?<=silence_start: )\d+\.?\d*)', silence_times.stderr.decode()))
silence_duration = list(re.finditer(r'((?<=silence_duration: )\d+\.?\d*)', silence_times.stderr.decode()))

start_stamps = [0.0,] + [float(start.group())+(float(duration.group()) - EASE) for start, duration in zip(silence_start, silence_duration)]
end_stamps = [(float(start.group()) + EASE)for start in silence_start] + [TOTAL_TIME,]

with open('temp.txt', 'w') as temp:
    for start, end in zip(start_stamps, end_stamps):
        temp.write(f"file '{file}'\n")
        temp.write(f'inpoint {round(start, 3)}\n')
        temp.write(f'outpoint {round(end, 3)}\n')


if os.path.isfile('temp.txt'):
    subprocess.run(f'ffmpeg -hide_banner -f concat -i temp.txt -vf select=concatdec_select -af aselect=concatdec_select,aresample=async=1 -acodec aac -vcodec {VIDEO_CODEC} -y {"trim"+file}', shell=True)
    os.remove('temp.txt')
