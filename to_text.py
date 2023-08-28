#!/usr/bin/env python3

from command_opts import opt, main_entry
from list_picker import list_picker
import gzip
import json
import mp3_splitter
import os
import pickle
import templater

ENGINES = {}
import engines.openai
import engines.transcribe
import engines.whisper
import engines.whisper_cpp
import engines.whisper_timestamped
import engines.whisperx
def setup_engines():
    # Validate the engines implemenet the expected functions
    to_setup = [
        engines.openai,
        engines.transcribe,
        engines.whisper,
        engines.whisper_cpp,
        engines.whisper_timestamped,
        engines.whisperx,
    ]
    expected = [
        ('get_id', 'Get an unique ID for this engine'),
        ('get_name', 'Describe the engine'),
        ('get_opts', 'Get all available options for the engine'),
        ('get_settings', 'Get model specific settings'),
        ('run_engine', 'Run the engine and transcribe audio'),
        ('parse_data', 'Parse the output of run_engine to a normalized format'),
    ]
    for module in to_setup:
        if module.get_id() in ENGINES:
            raise Exception(f"The engine ID '{module.get_id()}' was use more than once!")
        ENGINES[module.get_id()] = module

    for name, module in ENGINES.items():
        for func, desc in expected:
            if not hasattr(module, func):
                raise Exception(f"Helper '{name}' does contain function {func}() for '{desc}!")
setup_engines()

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

def enumerate_words(data):
    for frame in data:
        if len(frame) == 3:
            word, start, end = frame
            speaker = -1
        else:
            word, start, end, speaker = frame
        yield word, start, end, speaker

@opt("Transcribe an MP3 file and create a webpage")
def create_webpage(settings_file):
    with open(settings_file, "rt", encoding="utf-8") as f:
        settings = json.load(f)

    engine = ENGINES[settings["engine"]]
    engine_settings = engine.get_settings()
    data_fn = settings_file + ".gz"

    if os.path.isfile(data_fn):
        with gzip.open(data_fn, "rb") as f:
            data = f.read()
    else:
        if 'limit_seconds' in engine_settings or 'limit_bytes' in engine_settings:
            temp = []
            print("Creating seperate chunks...")
            chunks = mp3_splitter.chunk_mp3(
                settings["source_mp3"], 
                duration_in_seconds=engine_settings.get('limit_seconds'),
                size_in_bytes=engine_settings.get('limit_bytes'),
            )
            for chunk in chunks:
                temp.append({
                    "offset": chunk["offset"],
                    "duration": chunk["duration"],
                    "data": engine.run_engine(settings["engine_details"], chunk['fn']),
                })
                os.unlink(chunk['fn'])
            data = b'CHUNKED' + pickle.dumps(temp)
        else:
            data = engine.run_engine(settings["engine_details"], settings["source_mp3"])

        with gzip.open(data_fn, "wb") as f:
            f.write(data)

    if data.startswith(b'CHUNKED'):
        # For chunked data, parse each chunk in turn and offset the resulting data
        temp = pickle.loads(data[7:])
        data = []
        for cur in temp:
            chunk = engine.parse_data(cur['data'])
            for word, start, end, speaker in enumerate_words(chunk):
                data.append((word, start + cur['offset'], end + cur['offset'], speaker))
    else:
        # Non-chunked data, just read and parse it as is
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
