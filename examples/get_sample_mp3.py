#!/usr/bin/env python3

from urllib.request import urlretrieve
import os

url = "https://www.nasa.gov/wp-content/uploads/2023/07/podcast_the_international_space_station.mp3"
fn = "International_Space_Station.mp3"

if os.path.isfile(fn):
    print(f"{fn} already exists")
    exit(0)

msg = ""
def show_progress(block_count, block_size, file_size):
    global msg
    msg = f"Downloading, done with {block_size * block_count / file_size * 100:.2f}%..."
    print("\r" + msg, end="", flush=True)

urlretrieve(url, fn, show_progress)
print(" " * len(msg) + "\r", end="", flush=True)
print(f"Downloaded {fn}")

print("Use a command like the following to create a down-sampled version:")
cmd = f"ffmpeg -i {fn} -acodec libmp3lame -ab 48k -ar 48000 -ac 1 {fn}-small.mp3"
print(cmd)
