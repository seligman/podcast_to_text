#!/usr/bin/env python3

import json

def get_name():
    return "Whisper Timestamped"

def get_id():
    return "whisper_timestamped"

def get_settings():
    return {
        "limit_seconds": 7200, # Limit MP3 files to about 2 hours to prevent overloading Whisper
    }

def get_opts():
    return [
        ("model", "Whisper model to use (tiny/small/medium/large)"),
    ]

def run_engine(settings, source_fn):
    import whisper_timestamped

    print("Loading model...")
    model = whisper_timestamped.load_model(settings["model"])
    print("Loading audio file...")
    audio = whisper_timestamped.load_audio(source_fn)
    print("Transcribing...")
    args = {
        'best_of': 5,
        'beam_size': 5,
        'temperature': (0.0, 0.2, 0.4, (0.6 + 1e-16), 0.8, 1.0),
        'language': 'en', 
        'verbose': None,
    }
    results = whisper_timestamped.transcribe(model, audio, **args)

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
