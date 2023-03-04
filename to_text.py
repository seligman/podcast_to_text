#!/usr/bin/env python3

from command_opts import opt, main_entry
import engines.transcribe
import gzip
import os

ENGINES = {
    "aws-transcribe": engines.transcribe,
}

@opt("Show all available transcription engines")
def show_engines():
    for key, value in ENGINES.items():
        print(f"{key}: '{value.get_name()}'")
        for setting, desc in value.get_opts():
            print(f'  "{setting}": "{desc}",')

@opt("Run through the engines and generate transcription data")
def run_all_engines():
    engine = ENGINES["aws-transcribe"]
    settings = {
        "region_name": "us-west-2",
        "s3_bucket": "example-bucket",
        "s3_prefix": "example/",
    }
    data = engine.run_engine(settings, "International_Space_Station.mp3")
    with gzip.open(os.path.join("examples", "aws-transcribe.example.json.gz"), "wb") as f:
        f.write(data)

if __name__ == "__main__":
    main_entry('func')
