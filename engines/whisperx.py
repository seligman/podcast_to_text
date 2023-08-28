#!/usr/bin/env python3

import json, gc, os

def get_name():
    return "WhisperX"

def get_id():
    return "whisperx"

def get_settings():
    return {
        "limit_seconds": 7200, # Limit MP3 files to about 2 hours to prevent overloading Whisper
    }

def get_opts():
    return [
        ("model", "Whisper model to use (tiny/small/medium/large)"),
        ("batch_size", "Batch size (reduce if low on GPU memory, defaults to '16')"),
        ("compute_type", "Compute size (defaults to 'float16', change to int8 if low on GPU mem (may reduce accuracy)) "),
        ("device", "Target device (defaults to 'cuda')"),
        ("hf_token", "Hugging Face user access token (leave blank to use HF_TOKEN env) "),
    ]

def run_engine(settings, source_fn):
    device = settings.get("device", "")
    if len(device) == 0:
        device = "cuda"
    batch_size = str(settings.get("batch_size", ""))
    if len(batch_size) == 0:
        batch_size = "16"
    batch_size = int(batch_size)
    compute_type = settings.get("compute_type", "")
    if len(compute_type) == 0:
        compute_type = "float16"
    target_model = settings["model"]

    hf_token = settings.get("hf_token", "")
    if len(hf_token) == 0:
        hf_token = os.environ["HF_TOKEN"]

    import whisperx, torch # type: ignore

    args = {
        'initial_prompt': "Hello, welcome to my lecture.",
        'best_of': 5,
        'beam_size': 5,
        'temperatures': (0.0, 0.2, 0.4, (0.6 + 1e-16), 0.8, 1.0),
    }
    print("Loading model...")
    model = whisperx.load_model(target_model, device, compute_type=compute_type, language="en", asr_options=args)
    audio = whisperx.load_audio(source_fn)
    print("Transcribing...")

    result = model.transcribe(audio, batch_size=batch_size)

    del model; gc.collect(); torch.cuda.empty_cache()

    print("Aliging results...")
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    del model_a; gc.collect(); torch.cuda.empty_cache()

    print("Performing speaker diarization...")
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)

    diarize_segments = diarize_model(audio)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    if "word_segments" in result:
        del result["word_segments"]

    # Clean up the "Speaker" labels to just by the speaker number
    def clean_speaker(obj):
        if isinstance(obj, dict):
            if "speaker" in obj:
                if isinstance(obj["speaker"], str) and obj["speaker"].startswith("SPEAKER_"):
                    obj["speaker"] = int(obj["speaker"][8:])
            for key, val in obj.items():
                clean_speaker(val)
        elif isinstance(obj, list):
            for val in obj:
                clean_speaker(val)
    clean_speaker(result)

    # This model likes to create the prompt when it gets slightly confused, remove it when seen
    for phrase in ["Hello, welcome to my lecture.", "Welcome to my lecture."]:
        phrase = tuple(phrase.split(" "))
        for item in result['segments']:
            for i in range(len(item['words']) - len(phrase), -1, -1):
                if tuple(x['word'] for x in item['words'][i:i+len(phrase)]) == phrase:
                    for i in range(i, i + len(phrase)):
                        item['words'][i]['word'] = None
            item['words'] = [x for x in item['words'] if x['word'] is not None]

    result = json.dumps(result, separators=(",", ":")).encode("utf-8")

    return result

def parse_data(data):
    ret = []
    
    data = json.loads(data)

    # For the case where only one item is transcribed, treat it
    # as a group of one item
    if isinstance(data, dict):
        data = [data]
    
    extra = None
    for cur in data:
        for item in cur['segments']:
            for word in item['words']:
                cur_word = word['word']
                if extra is not None:
                    cur_word = extra + " " + word
                if 'start' in word:
                    ret.append([cur_word, word['start'], word['end'], word.get('speaker', -1)])
                else:
                    if len(ret) > 0:
                        ret[-1][0] += " " + cur_word
                    else:
                        extra = cur_word

    return ret

if __name__ == "__main__":
    print("This module is not meant to be run directly")
