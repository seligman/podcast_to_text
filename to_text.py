#!/usr/bin/env python3

from command_opts import opt, main_entry
from list_picker import list_picker
import engines.transcribe
import gzip
import os
import json
import templater

ENGINES = {
    "aws-transcribe": engines.transcribe,
}

@opt("Show all available transcription engines")
def show_engines():
    for key, value in ENGINES.items():
        print(f"{key}: '{value.get_name()}'")
        for setting, desc in value.get_opts():
            print(f'  "{setting}": "{desc}",')

@opt("Interactivately reate a settings file example")
def create_settings():
    fn = input("Please enter the filename to write the settings to: ")
    settings = {}
    settings["source_mp3"] = input("Please enter the filename of the source MP3 file: ")
    settings["target_fn"] = input("Please enter the target output HTML name (blank to name after the MP3): ")
    if len(settings["target_fn"]) == 0:
        del settings["target_fn"]
    settings["engine"] = list_picker([("Select engine:",)] + [(value.get_name(), key) for key, value in ENGINES.items()])
    settings["engine_details"] = {}
    for setting, desc in ENGINES[settings["engine"]].get_opts():
        settings["engine_details"][setting] = input(desc + ": ")
    
    print("Target settings:")
    print(json.dumps(settings, indent=4))
    with open(fn, "wt", newline="", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

@opt("Transcribe an MP3 file and create a webpage")
def create_webpage(settings_file):
    with open(settings_file, "rt", encoding="utf-8") as f:
        settings = json.load(f)

    engine = ENGINES[settings["engine"]]
    data_fn = settings_file + ".gz"

    if os.path.isfile(data_fn):
        with gzip.open(data_fn, "rb") as f:
            data = f.read()
    else:
        data = engine.run_engine(settings["engine_details"], settings["source_mp3"])
        with gzip.open(data_fn, "wb") as f:
            f.write(data)

    data = engine.parse_data(data)
    data = templater.fill_out(data, settings['source_mp3'])
    if "target_fn" in settings:
        dest = settings["target_fn"]
    else:
        dest = settings['source_mp3'] + ".html"
    with open(dest, "wt", newline="") as f:
        f.write(data)
    print(f"{dest} created!")

if __name__ == "__main__":
    main_entry('func')
