#!/usr/bin/env python3

import json

def get_name():
    return "whisper.cpp"

def get_id():
    return "whisper.cpp"

def get_opts():
    return [
        ("whisper.cpp", "Filename of whisper.cpp's main executable"),
        ("ffmpeg", "Filename of ffmpeg's executable"),
        ("model", "Filename of model to use"),
    ]

def run_engine(settings, source_fn):
    import os
    import subprocess
    import tempfile

    f, temp_wav = tempfile.mkstemp(".wav")
    os.close(f)
    if os.path.isfile(temp_wav):
        os.unlink(temp_wav)
    cmd = [
        settings['ffmpeg'], 
        "-i", source_fn, 
        "-f", "wav", 
        "-ac", "1", 
        "-acodec", "pcm_s16le", 
        "-ar", "16000", 
        temp_wav,
    ]
    print("Converting file to a wav...")
    subprocess.check_call(cmd)

    f, temp_csv = tempfile.mkstemp(".csv")
    os.close(f)
    for cur in [temp_csv, temp_csv + ".csv"]:
        if os.path.isfile(cur):
            os.unlink(cur)
    print("Running whisper.cpp")
    cmd = [
        settings['whisper.cpp'], 
        "--model", settings['model'],
        "--output-csv", 
        "--split-on-word", 
        "--output-file", temp_csv, 
        "--file", 
        temp_wav,
    ]
    subprocess.check_call(cmd)

    results = None
    for cur in [temp_csv, temp_csv + ".csv"]:
        if os.path.isfile(cur):
            with open(cur, "rb") as f:
                results = f.read()

    for cur in [temp_wav, temp_csv, temp_csv + ".csv"]:
        if os.path.isfile(cur):
            os.unlink(cur)

    return results

def parse_data(data):
    import csv
    import io

    bits = io.StringIO(data.decode('utf-8'))
    cr = csv.reader(bits)
    ret = []
    for row in cr:
        if len(row) == 3:
            start, end, phrase = row
            phrase = phrase.strip('" ')
            ret.append((phrase, int(start) / 1000, int(end) / 1000))

    return ret

if __name__ == "__main__":
    print("This module is not meant to be run directly")
