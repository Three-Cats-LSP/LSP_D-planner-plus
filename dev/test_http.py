"""Shared quiet HTTP server for Playwright / browser test harnesses."""
from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
APP_PLANNER_MARKERS = (b"mainNavBar", b'id="mainNavBar"', b'id="navBtnBuh"')

# Copied beside synced www/ so Playwright hits the same app shell as Capacitor/APK.
STAGE_DIRS = ("tests", "lib")
STAGE_GLOB = "tests-*.html"


class PortInUseError(RuntimeError):
    """Raised when a fixed test port is occupied and fallback is disabled."""


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


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _port_can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
        return True


def find_available_port(
    host: str = DEFAULT_HOST,
    preferred: int = DEFAULT_PORT,
    *,
    allow_fallback: bool = True,
) -> int:
    """Return preferred when free, otherwise an ephemeral port or raise clearly."""
    if preferred == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])
    if not _port_is_open(host, preferred) and _port_can_bind(host, preferred):
        return preferred
    if not allow_fallback:
        raise PortInUseError(
            f"Port {preferred} on {host} is already in use; refusing to bind silently."
        )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def verify_app_root(base_url: str, *, timeout: float = 10.0, max_bytes: int = 2_097_152) -> None:
    """Ensure the served index.html is the LSP planner shell, not a foreign listener."""
    index_url = f"{base_url.rstrip('/')}/index.html"
    try:
        with urllib.request.urlopen(index_url, timeout=timeout) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Unexpected HTTP {resp.status} from {index_url}")
            chunks: list[bytes] = []
            remaining = max_bytes
            while remaining > 0:
                part = resp.read(min(remaining, 65536))
                if not part:
                    break
                chunks.append(part)
                if any(marker in part for marker in APP_PLANNER_MARKERS):
                    return
                remaining -= len(part)
            body = b"".join(chunks)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot verify app root at {index_url}: {exc}") from exc
    if not any(marker in body for marker in APP_PLANNER_MARKERS):
        raise RuntimeError(
            f"Served root at {base_url} is not the LSP planner app (missing #mainNavBar). "
            "Another process may already be bound to the requested port."
        )


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
def serve_root(
    root: Path,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    allow_fallback: bool = True,
    verify_app: bool = True,
):
    chosen_port = find_available_port(host, port, allow_fallback=allow_fallback)
    server = ThreadingHTTPServer((host, chosen_port), make_handler(root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{host}:{server.server_port}/"
    try:
        if verify_app:
            verify_app_root(base_url)
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def serve_www(
    root: Path = ROOT,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    sync: bool = True,
    allow_fallback: bool = True,
    verify_app: bool = True,
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
        with serve_root(
            serve_dir,
            host,
            port,
            allow_fallback=allow_fallback,
            verify_app=verify_app,
        ) as base_url:
            yield base_url
