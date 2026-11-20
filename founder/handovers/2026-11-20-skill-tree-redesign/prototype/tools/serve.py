import http.server, sys, os
class H(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        if '/_blob/' in path and os.path.isfile(path):
            b = open(path, 'rb').read(64)
            s = b.lstrip()
            if s.startswith(b'<svg') or s.startswith(b'<?xml'): return 'image/svg+xml'
            if b[:4] == b'RIFF' and b[8:12] == b'WEBP': return 'image/webp'
            if b[:8] == b'\x89PNG\r\n\x1a\n': return 'image/png'
            if b[:4] == b'wOF2': return 'font/woff2'
            if s[:1] in (b'{', b'['): return 'application/json'
        return super().guess_type(path)
    def log_message(self, *a): pass
os.chdir(sys.argv[1])
http.server.ThreadingHTTPServer(('', int(sys.argv[2])), H).serve_forever()
