# Podcast To Text

This is a utility to turn a MP3 file into a HTML page with a machine generated transcription that looks like this:

![Preview](examples/preview.png)

Currently this is the early days, WIP as I migrate an internal tool that does a few other things into a single purpose tool.

Supported engines:

* [AWS Transcribe](https://aws.amazon.com/transcribe/) -- [Sample output](https://seligman.github.io/podcast_to_text/Example-Results-AWS-Transcribe.html)
* [OpenAI Speech to Text](https://platform.openai.com/docs/guides/speech-to-text) -- [Sample output](https://seligman.github.io/podcast_to_text/Example-Results-OpenAI.html)
* [Whisper](https://github.com/openai/whisper) -- Sample output: [Tiny](https://seligman.github.io/podcast_to_text/Example-Results-Whisper-Tiny.html), [Large](https://seligman.github.io/podcast_to_text/Example-Results-Whisper-Large.html) models
* [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) -- Sample output: [Tiny](https://seligman.github.io/podcast_to_text/Example-Results-Whisper_CPP-Tiny.html), [Large](https://seligman.github.io/podcast_to_text/Example-Results-Whisper_CPP-Large.html) models
* [Whisper-Timestamped](https://github.com/linto-ai/whisper-timestamped) -- Sample output: [Medium](https://seligman.github.io/podcast_to_text/Example-Results-WhisperTimestamped-Medium.html) model.
* [WhisperX](https://github.com/m-bain/whisperX) -- Sample output: [Medium](https://seligman.github.io/podcast_to_text/Example-Results-WhisperX-Medium.html) model.
