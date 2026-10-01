"""Serve only the prototype directory on the loopback interface."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8765)
args = parser.parse_args()
handler = partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parent))
print(f'Open http://127.0.0.1:{args.port} — Ctrl+C to stop', flush=True)
ThreadingHTTPServer(('127.0.0.1', args.port), handler).serve_forever()
