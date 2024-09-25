# Usage

## Basic Usage

For basic usage, you can use `create_settings` to interactively create a settings file.  For instance, assuming the file `podcast_the_international_space_station.mp3` already exists, and the environment variable `HF_TOKEN` is set to a valid Hugging Face token:

```
$ ./to_text.py create_settings
Please enter the filename to write the settings to: example_settings.json
Please enter the filename of the source MP3 file: podcast_the_international_space_station.mp3
Please enter the target output HTML name (blank to name after the MP3):
 WhisperX

Whisper model to use (tiny/small/medium/large): medium
Batch size (reduce if low on GPU memory, defaults to '16'):
Compute size (defaults to 'float16', change to int8 if low on GPU mem (may reduce accuracy)) :
Target device (defaults to 'cuda'):
Hugging Face user access token (leave blank to use HF_TOKEN env) :
Target settings:
{
    "source_mp3": "podcast_the_international_space_station.mp3",
    "engine": "whisperx",
    "engine_details": {
        "model": "medium",
        "batch_size": "",
        "compute_type": "",
        "device": "",
        "hf_token": ""
    }
}
```

That will create `example_settings.json` showing how the settings should be set.  From here, to run the settings file and create an output file:

```
$ ./to_text.py create_webpage example_settings.json
Creating seperate chunks...
torchvision is not available - cannot save figures
Loading model...
[...]
podcast_the_international_space_station.mp3.html created!
```

This creates a webpage with the transcription and JavaScript to show playback position on the transcription.

## Transcribe RSS Feed and Create Search Page

You will need a Hugging Face access token (read) that you can generate from [here](https://huggingface.co/settings/tokens), after accepting the user agreement for the following models: [Segmentation](https://huggingface.co/pyannote/segmentation-3.0) and [Speaker-Diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1).

To pull down all episodes of a podcast and create a searchable index, use the `transcribe_feed.py` helper:

```
# Setup pre-conditions:

# Specify Hugging Face token:
$ export HF_TOKEN=EXAMPLE_TOKEN_SPECIFY_TOKEN

# Install cuDNN from https://developer.nvidia.com/cudnn

# Install Python modules
$ pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall --no-cache
$ pip install git+https://github.com/m-bain/whisperx.git

# Add necessary libraries
# Add libraries to path: https://github.com/Purfview/whisper-standalone-win/releases/tag/libs

# Run transcription
# The first argument is the URL of the RSS feed to parse, the second argument is the directory to store
# the results in:
$ python3 transcribe_feed.py https://www.nasa.gov/feeds/podcasts/houston-we-have-a-podcast nasa_podcast
Loading feed...
Downloading 'Mars Audio Log #9' to '2024-04-26-Mars_Audio_Log_9.mp3'...
Transcribing 'Mars Audio Log #9'...
[...]
```

This will download the episodes from the podcast feed, and create the transcription web pages in the target folder.

To create a searchable index, run the following:

```
# The first argument is the directory with data from transcribe_feed:
$ python3 make_search_page.py nasa_podcast

# Since the page can not be served from a file:// URL, go ahead and run a simple
# Python server to show the page:
python3 examples\example_server.py --source nasa_podcast

# Visit http://127.0.0.1:8000/search.html to view the search page
```
