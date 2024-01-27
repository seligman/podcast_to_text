#!/usr/bin/env python3

# Extend http.server to include support for range requests for demo purposes

import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
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
            start = size-end
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

        l = end-start+1
        if 'Range' in self.headers:
            self.send_response(206)
        else:
            self.send_response(200)
        self.send_header('Content-type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range',
                         'bytes %s-%s/%s' % (start, end, size))
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
        bufsize = 64*1024
        while True:
            buf = infile.read(bufsize)
            if not buf:
                break
            outfile.write(buf)

if __name__ == '__main__':
    server = HTTPServer(("127.0.0.1", 8000), RangeHTTPRequestHandler)
    print("Running server on http://127.0.0.1:8000/")
    server.serve_forever()
