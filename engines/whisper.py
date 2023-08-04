#!/usr/bin/env python3

import json

def get_name():
    return "OpenAI Whisper"

def get_id():
    return "whisper"

def get_settings():
    return {
        "limit_seconds": 7200, # Limit MP3 files to about 2 hours to prevent overloading Whisper
    }

def get_opts():
    return [
        ("model", "Whisper model to use (tiny/small/medium/large)"),
    ]

def run_engine(settings, source_fn):
    import whisper

    print("Loading model...")
    model = whisper.load_model(settings["model"])
    print("Transcribing...")
    results = model.transcribe(source_fn)

    results = json.dumps(results, separators=(",", ":")).encode("utf-8")

    return results

def parse_data(data):
    ret = []
    
    data = json.loads(data)

    # For the case where only one item is transcribed, treat it
    # as a group of one item
    if isinstance(data, dict):
        data = [data]
    
    for cur in data:
        for item in cur['segments']:
            ret.append((item['text'], item['start'], item['end']))

    return ret

if __name__ == "__main__":
    print("This module is not meant to be run directly")
