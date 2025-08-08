#!/usr/bin/env python3

from urllib.request import Request, HTTPRedirectHandler, build_opener
import email.utils, io, json, os, re, subprocess, sys
import xml.etree.ElementTree as ET

# Use WhisperX's Medium model for this example
# This requires the enviornment variable HF_TOKEN be set
DEFAULT_SETTINGS = {
    "source_mp3": "<populated by code>",
    "engine": "whisperx",
    "engine_details": {
        "model": "medium",
    }
}

def parse_rss(data):
    # Utility to parse an RSS feed, yields a dictionary
    # of info for each entry with an audio enclosure
    it = ET.iterparse(io.BytesIO(data))
    for _, el in it:
        _, _, el.tag = el.tag.rpartition('}') # strip ns
    root = it.root

    def safe_text(elem):
        if elem is not None:
            return elem.text
        return None

    # Set this to a value to bail of <x> number of items, -1 to parse them all
    bail = -1

    for x in root.findall("./channel/item"):
        title = x.find("./title").text
        pub_date = x.find("./pubDate").text
        guid = safe_text(x.find("./guid"))
        link = safe_text(x.find("./link"))
        desc = safe_text(x.find("./description"))
        enclosure = None
        for enc in x.findall("./enclosure"):
            if enc.attrib["type"] == "audio/mpeg":
                enclosure = enc.attrib["url"]
                break
        yield {
            "id": guid if guid is not None else link,
            "link": link,
            "guid": guid,
            "title": title,
            "pub_date": email.utils.parsedate_to_datetime(pub_date).strftime("%Y-%m-%d %H:%M:%S"),
            "enclosure": enclosure,
            "desc": desc,
        }
        bail -= 1
        if bail == 0:
            break

def clean(value, allow_special=True, max_len=80):
    # Return a string that's safe to use for a filename
    ret = ""
    if allow_special:
        allowed = {'-', "'", "_", "(", ")", ".", ","}
    else:
        allowed = {'-', "_"}
    for x in value:
        if x == ' ':
            ret += "_"
        elif ('a' <= x <= 'z') or ('A' <= x <= 'Z') or ('0' <= x <= '9'):
            ret += x
        elif x in allowed:
            ret += x
        else:
            ret += "_"
    ret = ret.strip("_")
    ret = re.sub("_+", "_", ret)
    if max_len is not None:
        if len(ret) > max_len:
            ret = ret[:max_len]
    return ret

def load_cache(target_dir):
    # Simple JSON backed history of what's been downloaded
    if os.path.isfile(os.path.join(target_dir, "cache.json")):
        with open(os.path.join(target_dir, "cache.json"), "rt", encoding="utf-8") as f:
            cache = json.load(f)
    else:
        cache = {}
    
    return cache

def save_cache(target_dir, cache):
    with open(os.path.join(target_dir, "cache.json"), "wt", newline="", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)
        f.write("\n")

def pod_open(url, show_progress=False):
    # Wrap all requests with a common user agent, and handle 302 redirects
    opener = build_opener(HTTPRedirectHandler)
    req = Request(url, headers={"User-Agent": "Podcast Grabber"})
    resp = opener.open(req)
    return resp.read()

def process_feed(rss_url, target_dir, settings_file=None):
    global DEFAULT_SETTINGS
    if settings_file is not None:
        with open(settings_file, "r") as f:
            DEFAULT_SETTINGS = json.load(f)

    if not os.path.isdir(target_dir):
        raise Exception(f"Unable to find directory {target_dir}")

    cache = load_cache(target_dir)

    print("Loading feed...")
    feed = pod_open(rss_url)

    for cur in parse_rss(feed):
        if os.path.isfile('abort.txt'):
            print("Abort file detected!")
            exit(0)

        if cur['id'] not in cache:
            cur['filename'] = clean(cur['pub_date'][:10] + "-" + cur['title']) + ".mp3"
            cache[cur['id']] = cur
            save_cache(target_dir, cache)

        cur = cache[cur['id']]
        if not os.path.isfile(os.path.join(target_dir, cur['filename'])):
            print(f"Downloading '{cur['title']}' to '{cur['filename']}'...")
            mp3 = pod_open(cur['enclosure'])
            with open(os.path.join(target_dir, cur['filename']), "wb") as f:
                f.write(mp3)

        if not os.path.isfile(os.path.join(target_dir, cur['filename']) + ".html"):
            print(f"Transcribing '{cur['title']}'...")
            temp_fn = "_temp_settings.json"

            for fn in [temp_fn, temp_fn + ".gz"]:
                if os.path.isfile(fn):
                    os.unlink(fn)

            with open(temp_fn, "wt") as f:
                temp = DEFAULT_SETTINGS.copy()
                temp['source_mp3'] = os.path.join(target_dir, cur['filename'])
                json.dump(temp, f)

            subprocess.check_call(['python3', 'to_text.py', 'create_webpage_and_data', temp_fn])

            for fn in [temp_fn, temp_fn + ".gz"]:
                if os.path.isfile(fn):
                    os.unlink(fn)

def main():
    # Wrapper to parse command line args and call the helper
    if len(sys.argv) in {3, 4}:
        process_feed(*sys.argv[1:])
    else:
        print("Usage:")
        print(f"  {__file__} <RSS URL> <Target Dir> (<settings file>)")
        exit(1)

if __name__ == "__main__":
    main()
