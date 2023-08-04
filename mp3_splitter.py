#!/usr/bin/env python3

import io

class ReadMP3:
    def __init__(self, f):
        self.f = f

    def next(self):
        while True:
            self.header = self.f.read(4)
            if len(self.header) < 4:
                return False

            if self.header[:3] == b'TAG':
                self.f.read(124)
            elif self.header[:3] == b'ID3':
                self.f.read(2)
                skip = self.f.read(4)
                skip = (skip[0] << 21) + (skip[1] << 14) + (skip[2] << 7) + skip[3]
                self.f.read(skip)
            elif self.header[0] == 0xff and (self.header[1] >> 4) == 0xf:
                self.mpeg_ver = {0: 2.5, 2: 2, 3: 1}[(self.header[1] >> 3) & 0x3]
                self.layer = {1: 3, 2: 2, 3: 1}[(self.header[1] >> 1) & 0x3]
                self.protection = self.header[1] & 0x1
                bitrate_index = self.header[2] >> 4
                self.bitrate = {
                    (1, 1): [32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
                    (1, 2): [32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
                    (1, 3): [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
                    (2, 1): [32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
                    (2, 2): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
                    (2, 3): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
                }[(self.mpeg_ver, self.layer)][bitrate_index - 1]
                self.sample_rate = {
                    1: [44100, 48000, 32000],
                    2: [22050, 24000, 16000],
                    2.5: [11025, 12000, 8000],
                }[self.mpeg_ver][(self.header[2] >> 2) & 0x3]
                self.padding = (self.header[2] >> 1) & 0x1
                self.channel_mode = (self.header[3] >> 6) & 0x3

                self.padding_size = {1: 4, 2: 1, 3: 1}[self.layer]
                self.samples_per_frame = {(1, 1): 384, (1, 2): 1152, (1, 3): 1152, (2, 1): 192, (2, 2): 1152, (2, 3): 576}[(self.mpeg_ver, self.layer)]
                self.size = self.samples_per_frame // 8 * (self.bitrate * 1000) // self.sample_rate + (self.padding * self.padding_size)
                self.data = self.f.read(self.size - 4)
                return True

def chunk_mp3(fn, duration_in_seconds=None, size_in_bytes=None):
    ret = []
    cur_len = 0
    cur_buffer = io.BytesIO()
    chunk_at = 0
    offset = 0

    with open(fn, "rb") as f:
        mp3 = ReadMP3(f)
        while mp3.next():
            new_chunk = False
            if duration_in_seconds is not None and (cur_len / mp3.sample_rate) >= duration_in_seconds:
                new_chunk = True
            if size_in_bytes is not None and cur_buffer.tell() >= size_in_bytes:
                new_chunk = True
            if new_chunk:
                ret.append({
                    'offset': chunk_at / mp3.sample_rate,
                    'duration': (offset - chunk_at) / mp3.sample_rate,
                    'fn': fn + f"_chunk_{len(ret):04d}.mp3",
                })
                with open(ret[-1]['fn'], "wb") as f_dest:
                    cur_buffer.seek(0, 0)
                    f_dest.write(cur_buffer.read())
                    cur_buffer = io.BytesIO()
                    cur_len = 0
                chunk_at = offset
            cur_len += mp3.samples_per_frame
            cur_buffer.write(mp3.header)
            cur_buffer.write(mp3.data)
            offset += mp3.samples_per_frame

        if cur_len > 0:
            ret.append({
                'offset': chunk_at / mp3.sample_rate,
                'duration': (offset - chunk_at) / mp3.sample_rate,
                'fn': fn + f"_chunk_{len(ret):04d}.mp3",
            })
            with open(ret[-1]['fn'], "wb") as f_dest:
                cur_buffer.seek(0, 0)
                f_dest.write(cur_buffer.read())

    return ret

if __name__ == "__main__":
    print("This module is not meant to be run directly.")
