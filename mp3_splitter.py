#!/usr/bin/env python3

import sys, os

class ReadMP3:
    # The version of this helper class
    READMP3_VERSION = 8

    # Some lookup tables for parsing the MP3 format
    MP3_VERS = {0: 25, 2: 2, 3: 1}
    LAYERS = {1: 3, 2: 2, 3: 1}
    BITRATES = {
        (1, 1): [32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
        (1, 2): [32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
        (1, 3): [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
        (2, 1): [32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
        (2, 2): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
        (2, 3): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
        (25, 1): [32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
        (25, 2): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
        (25, 3): [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    }
    SAMPLE_RATES = {
        1: [44100, 48000, 32000],
        2: [22050, 24000, 16000],
        25: [11025, 12000, 8000],
    }
    PADDING_SIZES = {1: 4, 2: 1, 3: 1}
    SAMPLES_PER_FRAMES = {
        (1, 1): 384, (1, 2): 1152, (1, 3): 1152, 
        (2, 1): 192, (2, 2): 1152, (2, 3): 576,
        (25, 1): 192, (25, 2): 1152, (25, 3): 576,
    }

    # The number of "beats" per second
    BEAT_RATE = 14112000

    def __init__(self, f):
        self.f = f
        self.loc = 0 # The offset in the file of where the last read started
        self.tell = 0 # The offset in the file
        # The idea with beats is to have an integer value for the offset to prevent
        # float drift issues.  It's converted to a float in terms of seconds for the 
        # offset property.  The beat_rate is the number of beats per second, which 
        # is the LCM of all the possible sample rates
        self.total_beats = 0

    # Offset in seconds of the current position
    @property
    def offset(self):
        # Since this uses beats, it's immune from float math errors
        return self.total_beats / ReadMP3.BEAT_RATE

    # Read a number of bytes from the file and track the offset
    def _read(self, bytes):
        ret = self.f.read(bytes)
        self.tell += len(ret)
        return ret

    # Run through the entire MP3 till hitting the end
    def read_till_end(self):
        while self.next():
            pass

    # Find and read the next frame
    def next(self):
        while True:
            # Store the position where this frame was
            self.loc = self.tell
            self.header = self._read(4)
            if len(self.header) < 4:
                # All done
                return False

            if self.header[:3] == b'TAG':
                # Skip over ID3v1 Tags
                self._read(124)
            elif self.header[:3] == b'ID3':
                # Get the size and skip over ID3v2 headers
                self._read(2)
                skip = self._read(4)
                skip = (skip[0] << 21) + (skip[1] << 14) + (skip[2] << 7) + skip[3]
                self._read(skip)
            elif self.header[0] == 0xff and (self.header[1] >> 5) == 0x7:
                # We found the sync bytes, cautiously read the rest of the data
                # Anything that's invalid causes a short circuit to ignore the frame

                self.mpeg_ver = ReadMP3.MP3_VERS.get((self.header[1] >> 3) & 0x3)
                if self.mpeg_ver is None: continue

                self.layer = ReadMP3.LAYERS.get((self.header[1] >> 1) & 0x3)
                if self.layer is None: continue

                self.protection = self.header[1] & 0x1
                bitrate_index = self.header[2] >> 4
                bitrate = ReadMP3.BITRATES.get((self.mpeg_ver, self.layer))
                if bitrate is None: continue

                if bitrate_index - 1 < len(bitrate):
                    self.bitrate = bitrate[bitrate_index - 1]
                else:
                    continue

                sample_rate = ReadMP3.SAMPLE_RATES.get(self.mpeg_ver)
                if sample_rate is None:
                    continue
                else:
                    i = (self.header[2] >> 2) & 0x3
                    if 0 <= i < len(sample_rate):
                        self.sample_rate = sample_rate[i]
                    else:
                        continue

                # All the data appears valid, decode and update our data
                self.padding = (self.header[2] >> 1) & 0x1
                self.channel_mode = (self.header[3] >> 6) & 0x3
                self.padding_size = ReadMP3.PADDING_SIZES[self.layer]
                self.samples_per_frame = ReadMP3.SAMPLES_PER_FRAMES[(self.mpeg_ver, self.layer)]
                self.size = self.samples_per_frame // 8 * (self.bitrate * 1000) // self.sample_rate + (self.padding * self.padding_size)
                # This read will pull in the data, except for the self.header, and skip to the next frame
                self.data = self._read(self.size - 4)
                self.beats = self.samples_per_frame * (ReadMP3.BEAT_RATE // self.sample_rate)
                self.total_beats += self.beats
                return True
            #else:
            #    If we get here, then we'll continue reading two bytes 
            #    till we get a sync byte, or hit the end of the file

    # Helper method to run through the MP3 and get the total duration of the MP3
    @staticmethod
    def get_duration(f, use_buffer=False, include_size=False):
        if use_buffer:
            # If use_buffer is enabled, then read in large chunks
            # this can prevent network round trip delays if the file handle
            # is in fact a network stream
            class BufferReader:
                def __init__(self):
                    self.chunk = b''
                    self.off = 0
                def read(self, to_read):
                    ret = None
                    if to_read > len(self.chunk) - self.off:
                        if len(self.chunk) - self.off > 0:
                            ret = self.chunk[self.off:]
                            to_read -= len(ret)
                        self.chunk = f.read(33554432)
                        self.off = 0
                    if to_read > 0:
                        if ret is None:
                            ret = self.chunk[self.off:self.off+to_read]
                        else:
                            ret += self.chunk[self.off:self.off+to_read]
                    self.off += to_read
                    return b'' if ret is None else ret
            buffer = BufferReader()
            mp3 = ReadMP3(buffer)
        else:
            mp3 = ReadMP3(f)
        mp3.read_till_end()
        if include_size:
            from os import SEEK_END
            f.seek(0, SEEK_END)
            return mp3.offset, f.tell()
        else:
            return mp3.offset

# Helper to split an array into n mostly equally length arrays
def split_array(a, n):
    k, m = divmod(len(a), n)
    return [a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]

# Take one MP3 and chunk it into multiple MP3s if it's too big by size or length
def chunk_mp3(fn, duration_in_seconds=None, size_in_bytes=None, fn_extra=""):
    ret = []

    offsets = []
    total_len = 0
    batch_size = 30
    with open(fn, "rb") as f:
        mp3 = ReadMP3(f)
        offsets.append([0, 0])
        while mp3.next():
            total_len += mp3.beats
            if total_len / ReadMP3.BEAT_RATE > len(offsets) * batch_size:
                offsets.append([mp3.loc, 0])
            offsets[-1][1] += mp3.beats

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
                'offset': offset / ReadMP3.BEAT_RATE,
                'duration': duration / ReadMP3.BEAT_RATE,
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

    print("Creating 10 megabyte chunks:")
    chunks = chunk_mp3(fn, size_in_bytes=10485760, fn_extra="_by_size")
    for chunk in chunks:
        print(f"Chunk: {chunk['fn']}, Offset: {chunk['offset']:.2f}, Duration: {chunk['duration']:.2f}, Size: {chunk['size']:,}")

if __name__ == "__main__":
    main()
