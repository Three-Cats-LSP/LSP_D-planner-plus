"""Shared quiet HTTP server for Playwright / browser test harnesses."""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Suppress routine logs and broken-pipe noise during fast Playwright teardown."""

    def log_message(self, fmt, *args):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


def make_handler(root: Path):
    class Handler(QuietHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

    return Handler


@contextmanager
def serve_root(root: Path, host: str = "127.0.0.1", port: int = 8765):
    prev = os.getcwd()
    os.chdir(root)
    server = ThreadingHTTPServer((host, port), make_handler(root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}/"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        os.chdir(prev)
