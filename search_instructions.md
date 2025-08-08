# Search a Podcast Feed

These instructions allow you to automate downloading all of the episodes from a podcast feed using the RSS feed, transcribing the feed, and create the data files for a webpage to search the transcripts.

## Setup

For the transcription itself to run here, you will need to setup an environment variable `HF_TOKEN` with your [Hugging Face token](https://huggingface.co/docs/hub/en/security-tokens):

```text
@rem For Windows:
set HF_TOKEN=[the token from Hugging Face]

# For Linux and macOS:
export HF_TOKEN=[the token from Hugging Face]
```

You'll also need to ensure [WhisperX](https://github.com/m-bain/whisperX) is installed in your Python Packages.  Note that this may require a specific version of Python, I've tested these instructions with Python 3.10.  You can use [Anaconda](https://www.anaconda.com/docs/getting-started/anaconda/install#linux-installer) to install a specific Python version side-by-side with other installations.

It's also possible to run these directions in Docker, though care must be taken to pass through the GPU to the container, and note that especially on Windows, Docker will not pass the GPU to the container during a build, which might impact how the models are downloaded and configured during the initial build.

## Downloading and transcribing a feed

Once setup, you can run 

```bash
python transcribe_feed.py [url] [path]
```

Where `[url]` is a URL of an RSS feed to a podcast, and `[path]` is the local path to store MP3 files, along with the transcription data when it's created.  

This will download each item, transcribe the MP3, and create a `.json.gz` for each file, then create a `.html` player for each item with the transcription data, and also create a `cache.json` file with some metadata about the feed and items downloaded.

The command is safe to run again, it will only download MP3 files and update the metadata file for items that have not been previously processed.

Optionally, you can create a .json file with the same format described as the `DEFAULT_SETTINGS` variable in `transcribe_feed.py` and pick a different transcription engine and/or model to process the audio files.  If you do, pass it as a third parameter to `transcribe_feed.py`

Note that this process will take some time to run, generally a couple of minutes per episode, more if running on a CPU.  You can create a file called `abort.txt` to have the process cleanly stop during a run.  Also note that the WhisperX process will generate several warnings about version compatibility issues.  This is expected.

## Creating a search database

You can run the following to create a search database:

```bash
python make_search_page.py [path]
```

Where `[path]` is the local path that was used in the previous step.

## Running the example server

While the pages that are output can be served up with almost any server, they will not work from a file system, since most modern browsers block Javascript from loading local files, and they also won't work with Python's built in "http.server" since that does not support byte-range requests.  This project includes a simple example server that will work:

```bash
cd [path]
python "[path to this repo]/examples/example_server.py"
```

Where `[path]` is again the local path that was used to store data, and `[path to this repo]` is the path to this repo on your local machine.  When run, visit `http://127.0.0.1:8000/search.html` in your local browser to view the search page:

![The search page](search/web_server.png)

Once the data is loaded, all searching will occur in your browser itself.
