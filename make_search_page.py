#!/usr/bin/env python3

from datetime import datetime
import gzip, io, json, os, sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

class DumpData:
    def __init__(self, target_size):
        self.i = -1
        self.off = 0
        self.f = None
        self.existing = False
        self.total_files = 0
        self.total_bytes = 0
        self.target_size = target_size
        self.data = {}
        self.skipped = set()
    
    def move_to(self, file_number):
        self.close()
        self.i = file_number - 1
        self.existing = True

    def skip(self):
        if self.f is not None:
            self.f = None
        self.i += 1
        self.skipped.add(self.i)
        if self.i >= 100:
            raise Exception("Too many part files")
        if not self.existing:
            self.data[self.i] = io.BytesIO()
            self.total_files += 1
        self.f = self.data[self.i]
        if self.existing:
            self.f.seek(0, os.SEEK_SET)
        self.off = 0

    def write(self, value, compress=True, next_segment=False):
        if not isinstance(value, bytes):
            value = json.dumps(value, separators=(',', ':'))
            value = value.encode("utf-8")
        if compress:
            value = gzip.compress(value, mtime=0)
            value = value[:9] + b'\xff' + value[10:]
        if self.target_size is not None:
            if self.off + len(value) >= self.target_size:
                next_segment = True
        if self.f is None:
            next_segment = True
        if next_segment:
            if self.f is not None:
                self.f = None
            self.i += 1
            if self.i >= 100:
                raise Exception("Too many part files")
            if not self.existing:
                self.data[self.i] = io.BytesIO()
                self.total_files += 1
            self.f = self.data[self.i]
            if self.existing:
                self.f.seek(0, os.SEEK_SET)
            self.off = 0
        ret = [self.i, self.off, len(value)]
        self.f.write(value)
        self.off += len(value)
        self.total_bytes += len(value)
        return ret
    
    def close(self):
        if self.f is not None:
            self.f = None

def main():
    target = sys.argv[1]

    # Load the cache data, this will tell us where to find all of the
    # transcript data
    with open(os.path.join(target, "cache.json")) as f:
        cache = json.load(f)
    
    batches = []

    # Make sure to present everything in order of publication
    items = list(cache.values())
    items.sort(key=lambda x: x['pub_date'])

    for value in items:
        source_fn = os.path.join(target, value['filename'] + ".json.gz")
        if not os.path.isfile(source_fn):
            continue

        with gzip.open(source_fn) as f:
            data = json.load(f)

        # This is the data for this item that we pass off to the search page
        ret = {
            "published": value['pub_date'],
            "title": value['title'],
            'link': value['link'],
            'words': " ".join(x[0].replace(" ", "_") for x in data),
            'start': [],
            'speaker': "".join(chr(ord('A') + x[3]) for x in data),
        }
        # Start times are delta from each other, so calculate that
        last_start = 0
        for word, start, end, speaker in data:
            start = int(start)
            ret['start'].append(start - last_start)
            last_start = start
        if len(batches) == 0 or batches[-1]['size'] >= 10485760:
            batches.append({
                "size": 0,
                "items": [],
            })
        
        # The size is a "best effort" number to let us know when to split output files
        batches[-1]['size'] += len(json.dumps(ret))
        batches[-1]['items'].append(ret)

    # Create and initialize a helper to store data
    output = DumpData(None)
    header_len = 100
    output.write(b' ' * header_len, compress=False)

    for batch in batches:
        # Compress each batch in turn
        value = json.dumps(batch['items'], separators=(',', ':'))
        value = value.encode("utf-8")
        value = gzip.compress(value, mtime=0)
        # We toss the data information
        value = value[:9] + b'\xff' + value[10:]
        # Write the batch to a new file, noting the metadata of where to 
        # read this data
        batch['info'] = output.write(value, False, True)

    # Now that we've written everything, go ahead and store index to look
    # up each batch data chunk
    output.move_to(0)
    output.write(b' ' * header_len, compress=False)
    # This is the index that lets the search page know where to load data
    final = output.write([x['info'] for x in batches], compress=True)
    # And this is a small header, with enough data to find the index itself,
    # and some minor other data to configure the the UI
    final = {
        'data': final, 
        'created': datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"), 
        'items': len(cache),
        'before': 15, 
        'after': 100,
    }
    final = json.dumps(final, separators=(',', ':'))
    final = final.encode("utf-8")
    if len(final) > header_len:
        # This shouldn't happen, but if it does, it means the "final" dict is too big
        raise Exception(f"Header block is too big! {len(final)} > {header_len}")
    # Write out the final dict, note that it's padded by spaces because we wrote
    # padding spaces before we get here
    output.move_to(0)
    output.write(final, compress=False)
    output.close()

    # Finaly dump out all of the data files
    for i in sorted(output.data):
        data = output.data[i].getvalue()
        fn = os.path.join(target, f"search_data_{i:02d}.dat")
        with open(fn, "wb") as f:
            f.write(data)

    # And write out the page itself that does the work
    for fn in ["search.html", "spyglass.png"]:
        with open(os.path.join("search", fn), "rb") as f_src:
            with open(os.path.join(target, fn), "wb") as f_dest:
                f_dest.write(f_src.read())

    print("All done!")

if __name__ == "__main__":
    main()
