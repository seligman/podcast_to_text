#!/usr/bin/env python3

# Extend http.server to include support for range requests for demo purposes

from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
import argparse, json, html, io, os, sys, urllib.parse
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

ROOT_TEMPLATE = '''<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width"/>
<meta name="viewport" content="initial-scale=1.0"/>
<meta name="theme-color" media="(prefers-color-scheme: dark)"  content="light-dark(#ccc, #333)">
<title>Pages</title>
<style>
:root{
    color-scheme: light dark;
}
html,
body {
    background-color: light-dark(#ccc, #333);
    color: light-dark(#333, #ccc);
    font-family: "Roboto", sans-serif;
    font-size: 12pt;
}
a {
    color: light-dark(#003, #ccf);
    text-decoration: none;
    padding: 0.1em;
}
ul {
    list-style-type: none;
}
li {
    margin-bottom: 0.5em;
}
a:hover {
    color: light-dark(#003, #ccf);
    text-decoration: underline;
}
</style>
</head>
<body>
<!-- HTML -->
</body>
</html>
'''

def get_root_page():
    ret = "<ul>"

    if os.path.isfile("cache.json"):
        with open("cache.json", "r") as f:
            cache = json.load(f)
    else:
        cache = {}
    
    titles = {}
    for cur in cache.values():
        titles[f"{cur['filename']}.html"] = f"{cur['pub_date'][:10]}: {cur['title']}"

    if os.path.isfile("search.html"):
        ret += f'<li><a href="search.html">Main Search Page</a>'

    for cur in sorted(os.listdir(".")):
        if cur != "search.html":
            if os.path.isfile(cur) and cur.endswith(".html"):
                ret += f'<li><a href="{urllib.parse.quote_plus(cur)}">{html.escape(titles.get(cur, cur))}</a>'

    ret = ROOT_TEMPLATE.replace('<!-- HTML -->', ret)

    return ret.encode("utf-8")

class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_request(self, *args, **kw):
        print(f"{datetime.now(UTC).strftime('%d %H:%M:%S')}: {self.command} '{self.path}' [{self.headers.get('Range', '-')}]")

    def send_head(self):
        path = self.translate_path(self.path)
        ctype = self.guess_type(path)

        # Custom page with links to any built examples
        if self.path == "/":
            data = get_root_page()
            f = io.BytesIO(data)
            fs = None
            size = len(data)
            ctype = "text/html"
        else:
            if os.path.isdir(path):
                return SimpleHTTPRequestHandler.send_head(self)
            if not os.path.exists(path):
                return self.send_error(404, self.responses.get(404)[0])
            f = open(path, 'rb')
            fs = os.fstat(f.fileno())
            size = fs.st_size

        start, end = 0, size-1
        if 'Range' in self.headers:
            start, end = self.headers.get('Range').strip().strip('bytes=').split('-')
        if start == "":
            try:
                end = int(end)
            except ValueError as e:
                self.send_error(400, 'invalid range')
            start = size - end
        else:
            try:
                start = int(start)
            except ValueError as e:
                self.send_error(400, 'invalid range')
            if start >= size:
                self.send_error(416, self.responses.get(416)[0])
            if end == "":
                end = size-1
            else:
                try:
                    end = int(end)
                except ValueError as e:
                    self.send_error(400, 'invalid range')

        start = max(start, 0)
        end = min(end, size-1)
        self.range = (start, end)

        l = end - start + 1
        if 'Range' in self.headers:
            self.send_response(206)
        else:
            self.send_response(200)
        self.send_header('Content-type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(l))
        if fs is not None:
            self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.end_headers()

        return f

    def copyfile(self, infile, outfile):
        if not 'Range' in self.headers:
            SimpleHTTPRequestHandler.copyfile(self, infile, outfile)
            return

        start, end = self.range
        infile.seek(start)
        bufsize = 64 * 1024
        left = (end - start) + 1
        while left > 0:
            buf = infile.read(min(left, bufsize))
            if not buf:
                break
            left -= len(buf)
            outfile.write(buf)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="Port to run on", default=8000)
    parser.add_argument("--bind", type=str, help="Local IP address to bind to", default="127.0.0.1")
    parser.add_argument("--source", type=str, help="Folder to serve up", default=".")
    args = parser.parse_args()
    os.chdir(args.source)
    server = HTTPServer((args.bind, args.port), RangeHTTPRequestHandler)
    print(f"Running server on http://{args.bind}:{args.port}/")
    server.serve_forever()
