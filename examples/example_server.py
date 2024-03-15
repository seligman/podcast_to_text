#!/usr/bin/env python3

# Extend http.server to include support for range requests for demo purposes

from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
import argparse
import os
import sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_request(self, *args, **kw):
        print(f"{datetime.now(UTC).strftime('%d %H:%M:%S')}: {self.command} '{self.path}' [{self.headers.get('Range', '-')}]")

    def send_head(self):
        path = self.translate_path(self.path)
        ctype = self.guess_type(path)

        if os.path.isdir(path):
            return SimpleHTTPRequestHandler.send_head(self)

        if not os.path.exists(path):
            return self.send_error(404, self.responses.get(404)[0])

        f = open(path, 'rb')
        fs = os.fstat(f.fileno())
        size = fs[6]

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
    args = parser.parse_args()
    server = HTTPServer((args.bind, args.port), RangeHTTPRequestHandler)
    print(f"Running server on http://{args.bind}:{args.port}/")
    server.serve_forever()
