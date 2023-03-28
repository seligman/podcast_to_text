#!/usr/bin/env python3

from hashlib import sha256
import html
import json

class IsParagraph:
    def __init__(self):
        self.last_end = 0
        self.last_sentence = False
        self.gaps = []
        self.was_sentence = False
        self.was_paragraph = False
        self.last_pos = 0

    def get_pos(self, at):
        at = int(at * 100)
        ret = at - self.last_pos
        self.last_pos = at
        return ret

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
            best = max(best, 0.05)
            if dur > best and ((dur - best) / best) > 2:
                self.was_paragraph = True
        
        self.last_end = max(start, end)
        self.last_sentence = (len(word) > 0 and word[-1] in ".?!")

def fill_out(words, mp3_fn):
    with open("template.html", "rt") as f:
        data = f.read()
    
    # First off, combine clusters together so the read along indicator has a hope of keeping up
    merged = []
    for word, start, end in words:
        if start > end:
            start, end = end, start
        if len(word) > 0:
            new_group = False
            if len(merged) == 0:
                new_group = True
            elif merged[-1]['word'][-1] in ".?!":
                new_group = True
            elif merged[-1]['end'] - merged[-1]['start'] >= 0.5:
                new_group = True
            
            if new_group:
                merged.append({
                    "first": len(merged) == 0,
                    "word": word,
                    "start": start,
                    "end": end,
                })
            else:
                merged[-1]["word"] += " " + word
                merged[-1]["end"] = end

    # And now simplify the list of words and find "paragraph" breaks
    final = []
    is_para = IsParagraph()
    last_start = 0
    for cur in merged:
        is_para.check(cur)
        if cur["first"] or is_para.was_paragraph or (is_para.was_sentence and (cur["end"] - last_start) > 45):
            final += [is_para.get_pos(cur["start"]), -1]
            last_start = cur["start"]
        final += [is_para.get_pos(cur["start"]), cur["word"]]

    fn = mp3_fn.replace("\\", "/").split("/")[-1]

    data = data.replace("{{TITLE}}", html.escape(fn.replace(".mp3", "")))
    data = data.replace("{{MP3_NAME}}", html.escape(fn))
    data = data.replace("{{WORD_ID}}", sha256(fn.encode("utf-8")).hexdigest()[:10])
    data = data.replace("{WORDS_VAR}", json.dumps(final, separators=(",", ":")))

    data = "".join(x.strip() for x in data.split("\n"))

    return data

if __name__ == "__main__":
    print("This module is not meant to be run directly.")
