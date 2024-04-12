#!/usr/bin/env python3

import io, sys

class ReadMP3:
    def __init__(self, f):
        self.f = f

    def next(self):
        while True:
            self.loc = self.f.tell()
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
                valid = True
                if valid:
                    self.mpeg_ver = {0: 2.5, 2: 2, 3: 1}.get((self.header[1] >> 3) & 0x3)
                    if self.mpeg_ver is None:
                        valid = False
                if valid:
                    self.layer = {1: 3, 2: 2, 3: 1}.get((self.header[1] >> 1) & 0x3)
                    if self.layer is None:
                        valid = False
                if valid:
                    self.protection = self.header[1] & 0x1
                    bitrate_index = self.header[2] >> 4
                    bitrate = {
                        (1, 1): [32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
                        (1, 2): [32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
                        (1, 3): [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
                        (2, 1): [32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
                        (2, 2): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
                        (2, 3): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
                    }.get((self.mpeg_ver, self.layer))
                    if bitrate is None:
                        valid = False
                if valid:
                    if bitrate_index - 1 < len(bitrate):
                        self.bitrate = bitrate[bitrate_index - 1]
                    else:
                        valid = False
                if valid:
                    sample_rate = {
                        1: [44100, 48000, 32000],
                        2: [22050, 24000, 16000],
                        2.5: [11025, 12000, 8000],
                    }.get(self.mpeg_ver)
                    if sample_rate is None:
                        valid = False
                    else:
                        i = (self.header[2] >> 2) & 0x3
                        if 0 <= i < len(sample_rate):
                            self.sample_rate = sample_rate[i]
                        else:
                            valid = False
                if valid:
                    self.padding = (self.header[2] >> 1) & 0x1
                    self.channel_mode = (self.header[3] >> 6) & 0x3
                    self.padding_size = {1: 4, 2: 1, 3: 1}[self.layer]
                    self.samples_per_frame = {(1, 1): 384, (1, 2): 1152, (1, 3): 1152, (2, 1): 192, (2, 2): 1152, (2, 3): 576}[(self.mpeg_ver, self.layer)]
                    self.size = self.samples_per_frame // 8 * (self.bitrate * 1000) // self.sample_rate + (self.padding * self.padding_size)
                    self.data = self.f.read(self.size - 4)
                    return True

def split_array(a, n):
    k, m = divmod(len(a), n)
    return [a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]

def chunk_mp3(fn, duration_in_seconds=None, size_in_bytes=None, fn_extra=""):
    ret = []

    offsets = []
    total_len = 0
    batch_size = 30
    with open(fn, "rb") as f:
        mp3 = ReadMP3(f)
        offsets.append([0, 0])
        while mp3.next():
            total_len += mp3.samples_per_frame
            if total_len / mp3.sample_rate > len(offsets) * batch_size:
                offsets.append([mp3.loc, 0])
            offsets[-1][1] += mp3.samples_per_frame

        base_offsets = offsets
        offsets = [offsets]
        count = 1
        while True:
            need_more = False
            if size_in_bytes is not None:
                if max((x[-1][1] - x[0][0]) for x in offsets) > size_in_bytes:
                    need_more = True
            if duration_in_seconds is not None:
                if max(len(x) for x in offsets) * batch_size > duration_in_seconds:
                    need_more = True
            if need_more:
                count += 1
                offsets = split_array(base_offsets, count)
            else:
                break

        offset = 0
        for i, chunk in enumerate(offsets):
            duration = sum(x[1] for x in chunk)
            new_entry = {
                'offset': offset / mp3.sample_rate,
                'duration': duration / mp3.sample_rate,
                'fn': f"{fn}{fn_extra}_chunk_{len(ret):04d}.mp3",
            }
            offset += duration
            if i == len(offsets) - 1:
                left = -1
            else:
                left = offsets[i+1][0][0] - chunk[0][0]
            wrote = 0
            f.seek(chunk[0][0], os.SEEK_SET)
            with open(new_entry['fn'], "wb") as f_dest:
                while True:
                    temp = f.read(1048576 if left == -1 else min(1048576, left))
                    if len(temp) == 0:
                        break
                    wrote += len(temp)
                    f_dest.write(temp)
                    if left > 0:
                        left -= len(temp)
                        if left == 0:
                            break
            new_entry['size'] = wrote
            ret.append(new_entry)

    return ret

def main():
    if len(sys.argv) != 2:
        print(f"Use '{sys.argv[0]} <fn>' to test running this on a single MP3")
        exit(1)

    fn = sys.argv[1]

    print("Creating 5 minute chunks:")
    chunks = chunk_mp3(fn, duration_in_seconds=300, fn_extra="_by_time")
    for chunk in chunks:
        print(f"Chunk: {chunk['fn']}, Offset: {chunk['offset']:.2f}, Duration: {chunk['duration']:.2f}, Size: {chunk['size']:,}")

    print("Creating 5 minute chunks (allow larger last segment):")
    chunks = chunk_mp3(fn, duration_in_seconds=300, fn_extra="_by_time_pad", allow_large_final_segment=True)
    for chunk in chunks:
        print(f"Chunk: {chunk['fn']}, Offset: {chunk['offset']:.2f}, Duration: {chunk['duration']:.2f}, Size: {chunk['size']:,}")

    print("Creating 10 megabyte chunks:")
    chunks = chunk_mp3(fn, size_in_bytes=10485760, fn_extra="_by_size")
    for chunk in chunks:
        print(f"Chunk: {chunk['fn']}, Offset: {chunk['offset']:.2f}, Duration: {chunk['duration']:.2f}, Size: {chunk['size']:,}")

if __name__ == "__main__":
    main()
