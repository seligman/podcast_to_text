## Setup

For the transcription itself to run here, you will need to setup an environment variable HF_TOKEN with your [Hugging Face token](https://huggingface.co/docs/hub/en/security-tokens).

You'll also need to ensure [WhisperX](https://github.com/m-bain/whisperX) is installed in your Python Packages.

## Downloading and transcribing a feed

You can then run 

```bash
transcribe_feed.py <url> <path>
```

Where `<url>` is a URL of an RSS feed to a podcast, and `<path>` is the local path to store MP3 files, along with the transcription data when it's created.  

This will download each item, transcribe the MP3, and create a `.json.gz` for each file, then create a `.html` player for each item with the transcription data.

The command is safe to run again, it will only download MP3 files that have not been previously processed.

Optionally, you can create a .json file with the same format as the `DEFAULT_SETTINGS` variable in `transcribe_feed.py` and pick a different transcription engine and/or model to process the audio files.

## Creating a search database

You can run the following to create a search database:

```bash
python3 make_search_page.py <path>
```

Where `<path>` is the local path that was used in the previous step.

## Running the example server

While the pages that are output can be served up with almost any server, they will not work from a file system, since most modern browsers block Javascript from loading local files, and they also won't work with Python's built in http.server since that does not support byte-range requests..  This project includes a simple example server that will work:

```bash
cd <path>
ptyhon "<path to this repo>/examples/example_server.py"
```

Where `<path>` is again the local path that was used to store data, and `<path to this repo>` is the path to this repo on your local machine.  When run, visit `http://127.0.0.1:8000/search.html` in your local browser to view the search page:

![The search page](search/web_server.png)

Once the data is loaded, all searching will occur in your brower itself.
