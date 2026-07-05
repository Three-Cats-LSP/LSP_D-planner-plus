"""Regression tests for dev/test_http.py port lifecycle and app-root verification."""
from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_DEV = ROOT / "dev"
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from test_http import (  # noqa: E402
    DEFAULT_HOST,
    DEFAULT_PORT,
    PortInUseError,
    find_available_port,
    serve_root,
    verify_app_root,
)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def _free_port(host: str = DEFAULT_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


class TestHttpLifecycleTests(unittest.TestCase):
    def test_strict_port_in_use_raises_clearly(self):
        host = DEFAULT_HOST
        port = _free_port(host)
        blocker = ThreadingHTTPServer((host, port), _QuietHandler)
        thread = threading.Thread(target=blocker.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(PortInUseError):
                find_available_port(host, port, allow_fallback=False)
        finally:
            blocker.shutdown()
            thread.join(timeout=2)

    def test_fallback_selects_different_port_when_default_occupied(self):
        host = DEFAULT_HOST
        port = _free_port(host)
        blocker = ThreadingHTTPServer((host, port), _QuietHandler)
        thread = threading.Thread(target=blocker.serve_forever, daemon=True)
        thread.start()
        try:
            chosen = find_available_port(host, port, allow_fallback=True)
            self.assertNotEqual(chosen, port)
        finally:
            blocker.shutdown()
            thread.join(timeout=2)

    def test_wrong_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<html><body>not the planner</body></html>", encoding="utf-8")
            with serve_root(root, port=_free_port(), verify_app=False) as base_url:
                with self.assertRaises(RuntimeError) as ctx:
                    verify_app_root(base_url)
                self.assertIn("bnavPlanner", str(ctx.exception))

    def test_selected_port_propagates_through_serve_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<html><body><button id="bnavPlanner"></button></body></html>',
                encoding="utf-8",
            )
            preferred = _free_port()
            with serve_root(root, port=preferred, verify_app=True) as base_url:
                self.assertIn(f":{preferred}/", base_url)

    def test_cleanup_after_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<html><body><button id="bnavPlanner"></button></body></html>',
                encoding="utf-8",
            )
            port = _free_port()
            try:
                with serve_root(root, port=port, verify_app=True):
                    raise RuntimeError("probe failure")
            except RuntimeError:
                pass
            chosen = find_available_port(DEFAULT_HOST, port, allow_fallback=False)
            self.assertEqual(chosen, port)

    def test_repeated_invocations_get_clean_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<html><body><button id="bnavPlanner"></button></body></html>',
                encoding="utf-8",
            )
            ports = []
            for _ in range(3):
                with serve_root(root, port=0, verify_app=True) as base_url:
                    ports.append(int(base_url.split(":")[2].split("/")[0]))
            self.assertEqual(len(set(ports)), 3)

    def test_concurrent_invocations_use_distinct_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<html><body><button id="bnavPlanner"></button></body></html>',
                encoding="utf-8",
            )
            ports: list[int] = []
            lock = threading.Lock()
            barrier = threading.Barrier(2)

            def worker() -> None:
                barrier.wait()
                with serve_root(root, port=0, verify_app=True) as base_url:
                    port = int(base_url.split(":")[2].split("/")[0])
                    with lock:
                        ports.append(port)
                    threading.Event().wait(0.3)

            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertEqual(len(ports), 2)
            self.assertNotEqual(ports[0], ports[1])

    def test_occupied_default_port_does_not_serve_foreign_root(self):
        """When DEFAULT_PORT is taken by a foreign listener, serve_www must not silently reuse it."""
        host = DEFAULT_HOST
        with tempfile.TemporaryDirectory() as wrong:
            wrong_root = Path(wrong)
            (wrong_root / "index.html").write_text("<html><body>foreign</body></html>", encoding="utf-8")
            blocker = ThreadingHTTPServer((host, DEFAULT_PORT), _QuietHandler)
            thread = threading.Thread(target=blocker.serve_forever, daemon=True)
            thread.start()
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import sys; sys.path.insert(0, 'dev'); "
                            "from pathlib import Path; "
                            "from test_http import serve_root; "
                            "root = Path('.'); "
                            "with serve_root(root / 'www' if (root / 'www/index.html').is_file() else root, "
                            f"host={host!r}, port={DEFAULT_PORT}, allow_fallback=True, verify_app=True): "
                            "pass"
                        ),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            finally:
                blocker.shutdown()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
