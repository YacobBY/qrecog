"""Tiny static server so the A/B demo HTML files can fetch the audio.

Run:
    python serve.py
Then open http://127.0.0.1:8765/demo/surah_1.html in a browser.
"""
import http.server
import socketserver
import os
from pathlib import Path

os.chdir(Path(__file__).parent)
PORT = 8765
print(f"Serving {Path('.').resolve()} at http://127.0.0.1:{PORT}/")
print("Open one of:")
for p in sorted(Path("demo").glob("surah_*.html")):
    print(f"   http://127.0.0.1:{PORT}/{p.as_posix()}")
print("Ctrl-C to stop.")
with socketserver.TCPServer(("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    httpd.serve_forever()
