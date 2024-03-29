#!/usr/bin/env python3

from hashlib import sha256
from mp3_splitter import ReadMP3
import base64
import gzip
import html
import json

class IsParagraph:
    def __init__(self):
        self.last_end = 0
        self.last_sentence = False
        self.gaps = []
        self.was_sentence = False
        self.was_paragraph = False
        self.speakers = {}

    def prep_speakers(self, words):
        self.speakers = {}
        temp = {}
        for word, start, end, speaker in enumerate_words(words):
            if speaker not in temp:
                temp[speaker] = 0
            temp[speaker] += end - start
        temp = [(dur, speaker_id) for speaker_id, dur in temp.items()]
        temp.sort(reverse=True)

        misc_speaker = None
        for dur, speaker_id in temp:
            if misc_speaker is None:
                self.speakers[speaker_id] = chr(ord('A') + (len(self.speakers) % 26))
                if dur <= 60:
                    misc_speaker = self.speakers[speaker_id]
            else:
                self.speakers[speaker_id] = misc_speaker

    def encode_speaker(self, speaker):
        return self.speakers.get(speaker, ' ')

    def check(self, *args):
        if isinstance(args[0], dict):
            word, start, end = args[0]['word'], args[0]['start'], args[0]['end']
        elif isinstance(args[0], (list, tuple)):
            if len(args[0]) == 3:
                word, start, end = args[0]
            else:
                word, start, end, _ = args[0]
        else:
            word, start, end = args

        self.was_sentence = False
        self.was_paragraph = False

        if self.last_sentence:
            self.was_sentence = True

            dur = min(start, end) - self.last_end
            self.gaps.append(dur)
            if len(self.gaps) > 10:
                self.gaps.pop(0)
            best = min((sum(abs(x - y) for x in self.gaps), y) for y in self.gaps)[1]
            best = max(best, 0.05)
            if dur > best and ((dur - best) / best) > 2:
                self.was_paragraph = True

        self.last_end = max(start, end)
        self.last_sentence = (len(word) > 0 and word[-1] in ".?!")

def enumerate_words(data):
    for frame in data:
        if len(frame) == 3:
            word, start, end = frame
            speaker = -1
        else:
            word, start, end, speaker = frame
        yield word, start, end, speaker

def split_phrases(words):
    ret = []
    for word, start, end, speaker in enumerate_words(words):
        if start > end:
            start, end = end, start
        if " " in word:
            dur = end - start
            temp = word.split(" ")
            dur /= len(temp)
            for i, word in enumerate(temp):
                ret.append((word, i * dur + start, (i + 1) * dur + start, speaker))
        else:
            ret.append((word, start, end, speaker))
    return ret

def fill_out(words, mp3_fn):
    with open("template.html", "rt") as f:
        data = f.read()
    
    # Get the duration from the MP3
    with open(mp3_fn, "rb") as f:
        mp3 = ReadMP3(f)
        duration = 0
        while mp3.next():
            duration += mp3.samples_per_frame / mp3.sample_rate

    # For engines that output phrases instead of words, invent where the boundaries are
    if " " in "".join(x[0] for x in words):
        # There's a space in at least on word, so pass it off to our helper to split up
        words = split_phrases(words)

    is_para = IsParagraph()
    is_para.prep_speakers(words)

    last_speaker = ""
    paragraphs = []
    start_time = 0
    paragraph = []
    for i, (word, start, end, speaker) in enumerate(enumerate_words(words)):
        is_para.check((word, start, end))

        para_break = False

        if (start - start_time) > 45 and is_para.was_sentence:
            para_break = True

        if (start - start_time) > 60:
            para_break = True
        
        if i == 0 or (speaker != last_speaker and is_para.was_sentence):
            if i > 0:
                para_break = True
            last_speaker = speaker

        if i == len(words) - 1:
            paragraph.append({
                'word': word, 
                'start': start, 
                'end': end, 
                'speaker_encoded': is_para.encode_speaker(speaker),
            })
            para_break = True

        if para_break:
            paragraphs.append(paragraph)
            paragraph = []
            start_time = start

        if len(word) > 0:
            paragraph.append({
                'word': word, 
                'start': start, 
                'end': end, 
                'speaker_encoded': is_para.encode_speaker(speaker),
            })

    # Create a dump out of final data to send to the webpage, the webpage itself
    # will merge these to try to prevent too much animated noise
    simple = {'off': [], 'word': [], 'speaker': [], 'para': []}
    last_pos, last_value = 0, 0
    transcript = ""
    def track_pos(value):
        nonlocal last_pos, last_value
        last_value = value
        value = int(value * 100)
        ret = value - last_pos
        last_pos = value
        return ret

    for i, paragraph in enumerate(paragraphs):
        merged = []
        for word in paragraph:
            merged.append(word)

        for word_number, word in enumerate(merged):
            simple['off'].append(track_pos(word['start']))
            simple['word'].append(word['word'].replace("|", "/"))
            simple['speaker'].append(word.get('speaker_encoded', ' '))
            simple['para'].append('.' if word_number == 0 else ' ')

    fn = mp3_fn.replace("\\", "/").split("/")[-1]

    data = data.replace("{{TITLE}}", html.escape(fn.replace(".mp3", "")))
    data = data.replace("{{MP3_NAME}}", html.escape(fn))
    data = data.replace("{{WORD_ID}}", sha256(fn.encode("utf-8")).hexdigest()[:10])
    data = data.replace("{WORDS_VAR}", encode_words(simple))
    data = data.replace("{EXPECTED_DUR}", json.dumps(duration))

    data = "".join(x.strip() for x in data.split("\n"))

    return data

def encode_words(value):
    # Compress and encode the simple version of the word data to a compressed
    # format used by the webpage
    
    # Turn the list of words to a single string seperated by a pipe.
    value['word'] = "|".join(value['word'])
    # The list of paragraph starts is just a "." for a paragraph start,
    # and " " otherwise, so turn it into a long string
    value['para'] = "".join(value['para'])
    # Speakers are A-Z, or " " for no speaker, so again, a simlpe string
    value['speaker'] = "".join(value['speaker'])
    # Place the rest in a compressed json dump
    value = json.dumps(value, separators=(",", ":"))
    value = value.encode("utf-8")
    value = gzip.compress(value)
    value = base64.b64encode(value)
    value = value.decode("utf-8")
    # One final pass through json just to ensure the string is javascript safe
    value = json.dumps(value)

    return value

if __name__ == "__main__":
    print("This module is not meant to be run directly.")
