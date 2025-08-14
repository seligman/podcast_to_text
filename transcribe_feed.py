#!/usr/bin/env python3

from urllib.request import Request, HTTPRedirectHandler, build_opener
import email.utils, io, json, os, re, subprocess, sys, time
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

    # Download with a simple progress
    next_at = time.time() + 1.0
    last_msg = ""
    ret = b''
    total = int(resp.headers.get("content-length", '0'))
    while True:
        temp = resp.read(1048576)
        if len(temp) == 0:
            break
        ret += temp
        if time.time() >= next_at:
            if total > len(ret):
                msg = f"Downloaded {len(ret) // 1048576}mb, {len(ret) / total * 100:.2f}%..."
            else:
                msg = f"Downloaded {len(ret) // 1048576}mb..."
            print("\r" + " " * len(last_msg) + "\r" + msg, end="", flush=True)
            last_msg = msg
            next_at += 1.0
    if len(last_msg):
        print("\r" + " " * len(last_msg) + "\r", end="", flush=True)

    return ret

def process_feed(target_dir, settings):
    global DEFAULT_SETTINGS
    if settings['engine'] is not None:
        with open(settings['engine'], "r") as f:
            DEFAULT_SETTINGS = json.load(f)

    cache = load_cache(target_dir)

    print("Loading feed...")
    feed = pod_open(settings['podcast'])

    if not os.path.isdir(os.path.join(target_dir, "media")):
        os.mkdir(os.path.join(target_dir, "media"))

    stats = {
        "downloaded": 0,
        "transcribed": 0,
        "already_done": 0,
    }

    todo = list(parse_rss(feed))
    for i, cur in enumerate(todo):
        if os.path.isfile('abort.txt'):
            print("Abort file detected!")
            break

        if cur['id'] not in cache:
            cur['filename'] = clean(cur['pub_date'][:10] + "-" + cur['title']) + ".mp3"
            cache[cur['id']] = cur
            save_cache(target_dir, cache)

        cur = cache[cur['id']]
        if not os.path.isfile(os.path.join(target_dir, "media", cur['filename'])):
            print(f"Downloading {i+1:,} of {len(todo):,}")
            mp3 = pod_open(cur['enclosure'])
            with open(os.path.join(target_dir, "media", cur['filename']), "wb") as f:
                f.write(mp3)
            stats['downloaded'] += 1

    if stats['downloaded'] == 0:
        print("Nothing new to download")

    todo = []
    for cur in cache.values():
        web_page = os.path.join(target_dir, "media", cur['filename'] + ".html")
        meta_file = os.path.join(target_dir, "media", cur['filename'] + ".json.gz")
        if not os.path.isfile(meta_file) or not os.path.isfile(web_page):
            todo.append(cur)
        else:
            stats['already_done'] += 1
    
    for i, cur in enumerate(todo):
        if os.path.isfile('abort.txt'):
            print("Abort file detected!")
            break

        web_page = os.path.join(target_dir, "media", cur['filename'] + ".html")
        meta_file = os.path.join(target_dir, "media", cur['filename'] + ".json.gz")

        temp_fn = "_temp_settings.json"
        for fn in [temp_fn, temp_fn + ".gz"]:
            if os.path.isfile(fn):
                os.unlink(fn)

        with open(temp_fn, "wt") as f:
            temp = DEFAULT_SETTINGS.copy()
            temp['source_mp3'] = os.path.join(target_dir, "media", cur['filename'])
            json.dump(temp, f)

        print("")
        print(f"Working on {i+1:,} of {len(todo):,}: '{cur['title']}'...")
        subprocess.check_call(['python3', 'to_text.py', 'create_webpage_and_data', temp_fn])
        stats['transcribed'] += 1

        for fn in [temp_fn, temp_fn + ".gz"]:
            if os.path.isfile(fn):
                os.unlink(fn)

    print("")
    print(f"Done. Downloaded {stats['downloaded']:,}, transcribed {stats['transcribed']:,}, and {stats['already_done']:,} already done.")

def get_settings(target_dir):
    fn = os.path.join(target_dir, "settings.json")
    if os.path.isfile(fn):
        with open(fn) as f:
            return json.load(f)

    url = input("Enter podcast RSS feed URL: ")
    engine_override = input("Enter filename of settings file for Engine override (blank for none): ")

    print("URL: " + url)
    if len(engine_override) == 0:
        engine_override = None
        print("Engine: (Use default)")
    else:
        print("Engine: " + engine_override)
    
    yn = input("Does this look ok? [y/(n)] ")
    if yn != "y":
        exit(1)
    
    settings = {
        "engine": engine_override,
        "podcast": url,
    }

    with open(fn, "wt", newline="", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

    print("Settings saved!")

    return settings

def main():
    # Wrapper to parse command line args and call the helper
    if len(sys.argv) == 2:
        settings = get_settings(sys.argv[1])
        process_feed(sys.argv[1], settings)
    else:
        print("Usage:")
        print(f"  {__file__} <Target Dir>")
        exit(1)

if __name__ == "__main__":
    main()
