#!/usr/bin/env python3

import json

def get_name():
    return "OpenAI Online API"

def get_id():
    return "openai"

def get_settings():
    return {
        "limit_bytes": 24500000, # Limit MP3 files to just shy of 25MB to always fall below OpenAI limits
    }

def get_opts():
    return [
        ("openai_api_key", "OpenAI API Key (leave blank to load OPENAI_API_KEY from environment)"),
    ]

def run_engine(settings, source_fn):
    from urllib.request import urlopen, Request
    import string
    import random
    import os

    openai_api_key = settings["openai_api_key"]
    if len(openai_api_key) == 0:
        openai_api_key = os.getenv("OPENAI_API_KEY")

    base_url = "https://api.openai.com/v1/audio/transcriptions"
    boundary = "-" * 20 + "".join(random.choice(string.ascii_letters) for _ in range(20))

    headers = {
        "Authorization": "Bearer " + openai_api_key,
        "Content-Type": "multipart/form-data; boundary=" + boundary,
    }
    file = source_fn.replace("\\", "/").split("/")[-1]

    body = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file}"'.encode("utf-8")
    body += f'\r\nContent-Type: application/octet-stream\r\n\r\n'.encode("utf-8")

    with open(source_fn, "rb") as f:
        body += f.read()

    for key, value in (("model", "whisper-1"), ("response_format", "verbose_json")):
        body += f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}'.encode("utf-8")

    body += f'\r\n--{boundary}--\r\n'.encode("utf-8")
    print("Requesting transcription...")

    req = Request(base_url, body, headers=headers)
    resp = urlopen(req)

    return resp.read()

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
