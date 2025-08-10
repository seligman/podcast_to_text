#!/usr/bin/env python3

from decimal import Decimal
from hashlib import sha256
from mp3_splitter import ReadMP3
import base64
import gzip
import html
import json
import re

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
        for word in enumerate_words(words):
            if 'start' in word:
                if word.get('speaker', -1) not in temp:
                    temp[word.get('speaker', -1)] = 0
                temp[word.get('speaker', -1)] += max(word['end'], word['start']) - min(word['end'], word['start'])
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
            word, start, end = args[0]
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
            best = max(best, Decimal('0.05'))
            if dur > best and ((dur - best) / best) > 2:
                self.was_paragraph = True

        self.last_end = max(start, end)
        self.last_sentence = (len(word) > 0 and word[-1] in "\\),:;.?!'\"")

def safe_json_dumps(obj, separators=(",", ":"), **kwargs):
    json_str = json.dumps(obj, separators=separators, **kwargs)
    return json_str.replace('<', '\\x3C')

def enumerate_words(data):
    for frame in data:
        if isinstance(frame, dict):
            yield frame # In case enumerate_words was already called
        else:
            if len(frame) == 3:
                word, start, end = frame
                speaker = -1
            else:
                word, start, end, speaker = frame
            yield {
                "word": word,
                "start": Decimal(str(start)),
                "end": Decimal(str(end)),
                "speaker": speaker,
            }

def split_phrases(words):
    for word in enumerate_words(words):
        if word['start'] > word['end']:
            word['start'], word['end'] = word['end'], word['start']
        if " " in word['word']:
            temp = word['word'].split(" ")
            dur = (word['end'] - word['start']) / Decimal(len(temp))
            for i, sub_word in enumerate(temp):
                yield {
                    'word': sub_word,
                    'start': Decimal(i) * dur + word['start'],
                    'end': Decimal(i + 1) * dur + word['start'],
                    'speaker': word['speaker']
                }
        else:
            yield word

def fill_out(words, mp3_fn):
    with open("template.html", "rt") as f:
        data = f.read()
    
    # Get the duration from the MP3
    with open(mp3_fn, "rb") as f:
        duration = ReadMP3.get_duration(f)

    # For engines that output phrases instead of words, invent where the boundaries are
    if " " in "".join(x[0] for x in words):
        # There's a space in at least on word, so pass it off to our helper to split up
        words = list(split_phrases(words))

    is_para = IsParagraph()
    is_para.prep_speakers(words)

    last_speaker = ""
    paragraphs = []
    start_time = Decimal(0)
    paragraph = []
    for i, word in enumerate(enumerate_words(words)):
        is_para.check(word)

        para_break = False

        if (word['start'] - start_time) > Decimal(45) and is_para.was_sentence:
            para_break = True

        if (word['start'] - start_time) > Decimal(60):
            para_break = True
        
        if i == 0 or (word['speaker'] != last_speaker and is_para.was_sentence):
            if i > 0:
                para_break = True
            last_speaker = word['speaker']

        if i == len(words) - 1:
            paragraph.append({
                'word': word['word'], 
                'start': word['start'], 
                'end': word['end'], 
                'speaker_encoded': is_para.encode_speaker(word['speaker']),
            })
            para_break = True

        if para_break:
            paragraphs.append(paragraph)
            paragraph = []
            start_time = word['start']

        if len(word) > 0:
            paragraph.append({
                'word': word['word'], 
                'start': word['start'], 
                'end': word['end'], 
                'speaker_encoded': is_para.encode_speaker(word['speaker']),
            })

    # Create a dump out of final data to send to the webpage, the webpage itself
    # will merge these to try to prevent too much animated noise
    simple = {'off': [], 'word': [], 'speaker': [], 'para': []}
    last_pos, last_value = 0, 0
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

    details = {
        'link_title': fn.replace(".mp3", "").replace("_", " "),
        'feed_title': '',
        # 'duration': '<not used>',
        # 'published': '<not used>',
    }

    to_replace = {
        # The HTML title
        "[[TITLE]]": html.escape(fn.replace(".mp3", "").replace("_", " ")),
        # The encoded and compressed metadata, include words, timings, and speaker information
        '"[[WORDS_VAR]]"': encode_words(simple),
        # The title, used for creating Media Metadata (for use on mobile devices)
        "[[TITLE_META]]": base64.b64encode(safe_json_dumps(details).encode("utf-8")).decode("utf-8"),
        # An ID used to store local information about the playback position
        "[[WORD_ID]]": sha256(fn.encode("utf-8")).hexdigest()[:10],
        # The total length of the MP3 file, used to render the progress bar
        '"[[EXPECTED_DUR]]"': safe_json_dumps(duration),
        # The name of the MP3 file being shown, currently unused
        "[[META_MP3_NAME]]": html.escape(fn),
        # The name of the MP3 file for the player to load
        "[[MP3_NAME]]": html.escape(fn),
        # A chance for the template to include extra HTML, currently unused
        "<!-- EXTRA_WIDGETS -->": "",
        # The render of the page supports showing segments.  This could be generated from MP3 chapters and/or by use of 
        # a LLM to find the segments, but as of now, this is unused here.
        '"[[SEGMENTS_DATA]]"': '" "',
    }

    all_tags = "(?P<tag>" + "|".join(re.escape(k) for k in to_replace) + ")"
    data = re.sub(all_tags, lambda m: to_replace[m.group('tag')], data)

    data = "".join(x.strip() for x in data.split("\n"))

    return data

def encode_words(value):
    # Compress and encode the simple version of the word data to a compressed
    # format used by the webpage
    
    # Turn the list of words to a single string separated by a pipe.
    value['word'] = "|".join(value['word'])
    # The list of paragraph starts is just a "." for a paragraph start,
    # and " " otherwise, so turn it into a long string
    value['para'] = "".join(value['para'])
    # Speakers are A-Z, or " " for no speaker, so again, a simple string
    value['speaker'] = "".join(value['speaker'])
    # Place the rest in a compressed json dump
    value = safe_json_dumps(value)
    value = value.encode("utf-8")
    value = gzip.compress(value)
    value = base64.b64encode(value)
    value = value.decode("utf-8")
    # One final pass through json just to ensure the string is javascript safe
    value = safe_json_dumps(value)

    return value

if __name__ == "__main__":
    print("This module is not meant to be run directly.")
