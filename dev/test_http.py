"""Shared quiet HTTP server for Playwright / browser test harnesses."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Copied beside synced www/ so Playwright hits the same app shell as Capacitor/APK.
STAGE_DIRS = ("tests", "lib")
STAGE_GLOB = "tests-*.html"


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


def stage_regression_harness(www: Path, root: Path = ROOT) -> None:
    """Stage browser regression pages next to post-sync www/ app assets."""
    for name in STAGE_DIRS:
        src = root / name
        if not src.is_dir():
            continue
        dest = www / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    for src in sorted(root.glob(STAGE_GLOB)):
        if src.is_file():
            shutil.copy2(src, www / src.name)
    fixtures_src = root / "dev" / "fixtures"
    if fixtures_src.is_dir():
        fixtures_dest = www / "dev" / "fixtures"
        fixtures_dest.parent.mkdir(parents=True, exist_ok=True)
        if fixtures_dest.exists():
            shutil.rmtree(fixtures_dest)
        shutil.copytree(fixtures_src, fixtures_dest)


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


@contextmanager
def serve_www(
    root: Path = ROOT,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    sync: bool = True,
):
    """Run sync_www.py, stage regression harness files, serve from www/."""
    sync_script = root / "tools" / "sync_www.py"
    if sync:
        if not sync_script.is_file():
            raise FileNotFoundError(f"sync_www.py missing: {sync_script}")
        subprocess.run([sys.executable, str(sync_script)], cwd=str(root), check=True)
    www = root / "www"
    if not (www / "index.html").is_file():
        raise FileNotFoundError(f"www/index.html missing after sync — run tools/sync_www.py")
    with tempfile.TemporaryDirectory(prefix="lsp-www-") as tmp:
        serve_dir = Path(tmp) / "www"
        shutil.copytree(www, serve_dir)
        stage_regression_harness(serve_dir, root)
        with serve_root(serve_dir, host, port) as base_url:
            yield base_url
