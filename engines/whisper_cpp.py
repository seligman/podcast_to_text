#!/usr/bin/env python3

import json

def get_name():
    return "whisper.cpp"

def get_id():
    return "whisper.cpp"

def get_settings():
    return {
        "limit_seconds": 7200, # Limit MP3 files to about 2 hours to prevent overloading Whisper
    }

def get_opts():
    return [
        ("whisper.cpp", "Filename of whisper.cpp's main executable"),
        ("ffmpeg", "Filename of ffmpeg's executable"),
        ("model", "Filename of model to use"),
        ("threads", "Number of threads to use during computation (leave blank for default)"),
        ("processors", "Number of processors to use during computation (leave blank for default)"),
    ]

def run_engine(settings, source_fn):
    import os
    import subprocess
    import tempfile
    
    temp_srt, temp_wav = None, None

    try:
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

        f, temp_srt = tempfile.mkstemp(".srt")
        os.close(f)
        for cur in [temp_srt, temp_srt + ".srt"]:
            if os.path.isfile(cur):
                os.unlink(cur)
        print("Running whisper.cpp")
        cmd = [
            settings['whisper.cpp'], 
            "--model", settings['model'],
            "--output-srt", 
            "--split-on-word", 
            "--output-file", temp_srt, 
        ]
        if "threads" in settings and len(settings["threads"]) > 0: cmd += ["--threads", settings["threads"]]
        if "processors" in settings and len(settings["processors"]) > 0: cmd += ["--processors", settings["processors"]]
        cmd += [
            "--file", temp_wav,
        ]
        subprocess.check_call(cmd)

        results = None
        for cur in [temp_srt, temp_srt + ".srt"]:
            if os.path.isfile(cur):
                with open(cur, "rb") as f:
                    results = f.read()

        return results
    finally:
        for cur in ([] if temp_wav is None else [temp_wav]) + ([] if temp_srt is None else [temp_srt, temp_srt + ".srt"]):
            if os.path.isfile(cur):
                os.unlink(cur)

def parse_at(val):
    ret = 0
    val = val.split(",")
    ret = int(val[1]) / 1000
    val = val[0].split(":")[::-1]
    for val, mul in zip(val, [1, 60, 3600]):
        ret += int(val) * mul
    return ret

def parse_data(data):
    import io
    bits = io.StringIO(data.decode('utf-8'))
    state = "count"
    ret = []

    for row in bits:
        row = row.strip(" \r\n")
        if state == "count":
            state = "time"
        elif state == "time":
            state = "text"
            start, end = list(map(parse_at, row.split(" --> ")))
            data = []
        elif state == "text":
            if len(row) == 0:
                data = " ".join(data)
                ret.append((data.strip(" "), start, end))
                state = "count"
            else:
                data.append(row)

    return ret

if __name__ == "__main__":
    print("This module is not meant to be run directly")
