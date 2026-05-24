#!/usr/bin/env python3
"""Zero-cache HTTP server for local Gaia development.

Serves docs/ with Cache-Control: no-store on every response so the
browser never returns a 304 from a stale local cache.
"""
import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
DIRECTORY = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.abspath("docs")


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with http.server.HTTPServer(("", PORT), NoCacheHandler) as httpd:
        print(f"Serving {DIRECTORY}/ at http://localhost:{PORT}/  (no-cache mode)")
        httpd.serve_forever()
