# Usage

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

To pull down all episodes of a podcast, use the `transcribe_feed.py` helper:

```
$ ./transcribe_feed.py https://www.nasa.gov/feeds/podcasts/houston-we-have-a-podcast nasa_podcast
Loading feed...
Downloading 'Mars Audio Log #9' to '2024-04-26-Mars_Audio_Log_9.mp3'...
Transcribing 'Mars Audio Log #9'...
[...]
```

This will download the episodes from the podcast feed, and create the transcription web pages in the target folder.
