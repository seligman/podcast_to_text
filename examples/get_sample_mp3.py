#!/usr/bin/env python3

from urllib.request import urlretrieve
import os

url = "http://www.nasa.gov/sites/default/files/atoms/audio/podcast_the_international_space_station.mp3"
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
